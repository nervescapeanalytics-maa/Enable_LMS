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
    Privacy-safe deterministic placeholder. Swap the body for a real
    LLM call (OpenAI, on-prem) when ready — the rest of the system
    only consumes this string.
    """
    n = len(percents)
    avg = mean(percents)
    last = percents[-1]
    direction = (
        'improving' if predicted > last + 1
        else 'slipping' if predicted < last - 1
        else 'steady'
    )
    return (
        f'Across {n} attempts the student averaged {avg:.1f}% and most '
        f'recently scored {last:.1f}%. The trend is {direction}; the '
        f'rule-based projection for the next attempt is {predicted:.1f}%.'
    )
