"""
AI insights for the Exams module.

Two layers:

* **Rule-based** (always available, behind ``exam.ai_prediction_rule``)
    - Predicts the next-attempt percentage from a least-squares trend on
      the student's recent percentages.
    - Computes risk band (RED/AMBER/GREEN) using the configurable
      ``exam.alert_red_zone_percent`` / ``exam.alert_amber_zone_percent``
      thresholds.
    - Estimates a competitive-exam rank band from the student's average
      percentage.

* **LLM (narrative)** (behind ``exam.ai_prediction_llm``)
    - When the flag is OFF: returns ``None`` for the narrative.
    - When ON: returns a deterministic, privacy-safe template string. The
      hook ``llm_narrative()`` is the only place that needs to swap in a
      real LLM call.
"""
from __future__ import annotations

from decimal import Decimal
from statistics import mean
from typing import Iterable, Optional

from .permissions import is_feature_enabled, get_exam_setting_int


# ---------------------------------------------------------------------------
# Numeric core
# ---------------------------------------------------------------------------
def _to_float_list(percents: Iterable) -> list[float]:
    out: list[float] = []
    for p in percents:
        if p is None:
            continue
        try:
            out.append(float(p))
        except (TypeError, ValueError):
            continue
    return out


def linear_trend(percents: list[float]) -> float:
    """Slope of the best-fit line over the index 0..n-1. 0.0 if < 2 points."""
    n = len(percents)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(percents) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, percents))
    den = sum((x - mx) ** 2 for x in xs) or 1.0
    return num / den


def predict_next_score(percents: list[float]) -> float:
    """Predict next attempt's percentage. Clamped to [0, 100]."""
    if not percents:
        return 0.0
    if len(percents) == 1:
        return float(percents[0])
    slope = linear_trend(percents)
    nxt = percents[-1] + slope
    if nxt < 0:
        return 0.0
    if nxt > 100:
        return 100.0
    return round(nxt, 2)


def risk_band(score: float, *, red: int, amber: int) -> str:
    if score < red:
        return 'RED'
    if score < amber:
        return 'AMBER'
    return 'GREEN'


# Empirical rank-band table. Conservative — used for "predicted competitive
# rank band" only. Tuned to be approximately representative.
_RANK_TABLE = [
    (95, 'AIR 1 – 1,000'),
    (90, 'AIR 1,000 – 5,000'),
    (85, 'AIR 5,000 – 15,000'),
    (75, 'AIR 15,000 – 50,000'),
    (60, 'AIR 50,000 – 1,00,000'),
    (40, 'AIR 1,00,000 – 3,00,000'),
    (0,  'AIR > 3,00,000'),
]


def predicted_rank_band(avg_pct: float) -> str:
    for threshold, label in _RANK_TABLE:
        if avg_pct >= threshold:
            return label
    return 'AIR > 3,00,000'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def insights_for_attempts(attempt_percents, *, tenant=None) -> dict:
    """
    Build the insight dict from a list of recent percentages
    (oldest → newest).

    Returns
    -------
    dict with keys::

        ok, samples, last, avg, slope_per_attempt, predicted_next_pct,
        risk_band, predicted_rank_band, narrative (None if LLM flag off),
        rule_enabled, llm_enabled
    """
    rule_on = is_feature_enabled(
        'exam.ai_prediction_rule', tenant=tenant, user_type='ADMIN',
    )
    llm_on = is_feature_enabled(
        'exam.ai_prediction_llm', tenant=tenant, user_type='ADMIN',
    )
    pcts = _to_float_list(attempt_percents)
    out = {
        'ok': bool(pcts) and rule_on,
        'samples': len(pcts),
        'rule_enabled': rule_on,
        'llm_enabled': llm_on,
    }
    if not rule_on or not pcts:
        return out

    red = get_exam_setting_int('exam.alert_red_zone_percent', tenant=tenant, default=35)
    amber = get_exam_setting_int('exam.alert_amber_zone_percent', tenant=tenant, default=50)
    nxt = predict_next_score(pcts)

    out.update({
        'last': round(pcts[-1], 2),
        'avg': round(mean(pcts), 2),
        'slope_per_attempt': round(linear_trend(pcts), 3),
        'predicted_next_pct': nxt,
        'risk_band': risk_band(nxt, red=red, amber=amber),
        'predicted_rank_band': predicted_rank_band(mean(pcts)),
        'narrative': llm_narrative(pcts, nxt) if llm_on else None,
    })
    return out


def llm_narrative(percents: list[float], predicted: float) -> str:
    """
    Generate a narrative for the student's performance trajectory.

    Resolution order:
      1. If an ``AIFeatureConfig`` row exists with ``feature_key='exam.ai_prediction_llm'``,
         is enabled, has a non-empty ``provider`` and an ``api_key_reference`` that
         resolves (via ``SystemSetting``) to a real key, call that provider.
         Currently supports ``provider='openai'`` (chat.completions). Any failure
         falls back to the deterministic template below — never raises.
      2. Otherwise (no config, no key, or any error) return a deterministic,
         privacy-safe template string.
    """
    n = len(percents)
    avg = mean(percents)
    last = percents[-1]
    direction = (
        'improving' if predicted > last + 1
        else 'slipping' if predicted < last - 1
        else 'steady'
    )
    fallback = (
        f'Across {n} attempts the student averaged {avg:.1f}% and most '
        f'recently scored {last:.1f}%. The trend is {direction}; the '
        f'rule-based projection for the next attempt is {predicted:.1f}%.'
    )

    # Try real LLM via AIFeatureConfig
    try:
        from system_config.models import AIFeatureConfig, SystemSetting
        cfg = (AIFeatureConfig.objects
               .filter(feature_key='exam.ai_prediction_llm', is_enabled=True)
               .order_by('tenant_id').first())
        if not cfg or not cfg.provider:
            return fallback

        api_key = ''
        if cfg.api_key_reference:
            row = SystemSetting.objects.filter(
                setting_key=cfg.api_key_reference
            ).order_by('tenant_id').first()
            if row:
                api_key = (row.setting_value or '').strip()
        if not api_key:
            return fallback

        provider = (cfg.provider or '').strip().lower()
        prompt = (
            f"Give a 2-3 sentence empathetic, study-coach narrative to a student. "
            f"They have {n} attempts averaging {avg:.1f}%, most recent {last:.1f}%, "
            f"trend {direction}, projected next score {predicted:.1f}%. "
            f"Be encouraging and concrete. Do not mention you are an AI."
        )

        if provider == 'openai':
            import json
            import urllib.request
            endpoint = (cfg.api_endpoint or 'https://api.openai.com/v1/chat/completions')
            model = (cfg.config_json or {}).get('model', 'gpt-4o-mini')
            payload = json.dumps({
                'model': model,
                'messages': [
                    {'role': 'system', 'content': 'You are a supportive study coach.'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.4,
                'max_tokens': 160,
            }).encode('utf-8')
            req = urllib.request.Request(
                endpoint, data=payload,
                headers={'Authorization': f'Bearer {api_key}',
                         'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode('utf-8'))
            text = body.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            return text or fallback

        # Unknown provider — return fallback
        return fallback
    except Exception:
        import logging
        logging.getLogger(__name__).exception('llm_narrative provider call failed; using fallback')
        return fallback
