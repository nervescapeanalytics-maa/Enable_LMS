"""
Phase 4 — AI insights unit tests.

Covers:
  - linear_trend: flat / rising / falling series
  - predict_next_score: correct extrapolation
  - risk_band: RED / AMBER / GREEN boundaries
  - predicted_rank_band: cutoff table
  - insights_for_attempts: empty list, single value, gated by feature flag
  - llm_narrative: returns non-empty string
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from unittest.mock import patch

from assessments.insights import (
    _to_float_list, linear_trend, predict_next_score,
    risk_band, predicted_rank_band, insights_for_attempts, llm_narrative,
)
from assessments.permissions import ensure_exam_feature_flags
from system_config.models import FeatureFlag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enable(key, is_enabled=True):
    FeatureFlag.objects.filter(flag_key=key, tenant__isnull=True).update(is_enabled=is_enabled)


# ---------------------------------------------------------------------------
# _to_float_list
# ---------------------------------------------------------------------------

def test_to_float_list_filters_none():
    assert _to_float_list([None, '50', 75, None]) == [50.0, 75.0]


def test_to_float_list_empty():
    assert _to_float_list([]) == []


# ---------------------------------------------------------------------------
# linear_trend
# ---------------------------------------------------------------------------

def test_linear_trend_flat():
    # constant series → slope ≈ 0
    slope = linear_trend([50.0, 50.0, 50.0, 50.0])
    assert abs(slope) < 0.01


def test_linear_trend_rising():
    slope = linear_trend([40.0, 50.0, 60.0, 70.0])
    assert slope > 0


def test_linear_trend_falling():
    slope = linear_trend([70.0, 60.0, 50.0, 40.0])
    assert slope < 0


def test_linear_trend_single_element():
    # single element → 0
    assert linear_trend([55.0]) == 0.0


# ---------------------------------------------------------------------------
# predict_next_score
# ---------------------------------------------------------------------------

def test_predict_next_score_rising():
    pct = [40.0, 50.0, 60.0, 70.0]
    pred = predict_next_score(pct)
    assert pred > 70.0  # next step should be above current last


def test_predict_next_score_capped():
    # even a strong upward trend should not exceed 100
    pred = predict_next_score([90.0, 95.0, 98.0])
    assert pred <= 100.0


def test_predict_next_score_floor():
    # downward trend should not go below 0
    pred = predict_next_score([20.0, 10.0, 5.0])
    assert pred >= 0.0


def test_predict_next_score_empty_returns_zero():
    assert predict_next_score([]) == 0.0


# ---------------------------------------------------------------------------
# risk_band
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('score,expected', [
    (20.0, 'RED'),
    (34.9, 'RED'),     # strictly below 35 → RED
    (35.0, 'AMBER'),   # exactly at red threshold (not < red) → AMBER
    (36.0, 'AMBER'),
    (49.9, 'AMBER'),
    (50.1, 'GREEN'),   # strictly above 50 → GREEN
    (100.0, 'GREEN'),
])
def test_risk_band(score, expected):
    assert risk_band(score, red=35, amber=50) == expected


# ---------------------------------------------------------------------------
# predicted_rank_band
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('avg,expected_fragment', [
    (99, 'AIR'),          # very high → some top-band string
    (92, 'AIR 1,000'),   # 85-94
    (85, 'AIR 5,000'),   # 80-84 bucket
    (75, 'AIR 15,000'),  # 70-79 bucket
    (60, 'AIR'),          # mid range
    (45, 'AIR'),          # low range
    (20, 'AIR > 3,00,000'),
])
def test_predicted_rank_band(avg, expected_fragment):
    assert expected_fragment in predicted_rank_band(avg)


# ---------------------------------------------------------------------------
# insights_for_attempts
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_insights_empty_returns_not_ok():
    ensure_exam_feature_flags()
    result = insights_for_attempts([])
    assert result.get('ok') is False


@pytest.mark.django_db
def test_insights_single_value_ok():
    ensure_exam_feature_flags()
    _enable('exam.ai_prediction_rule', True)
    result = insights_for_attempts([60.0])
    assert result.get('ok') is True
    assert result['risk_band'] in ('RED', 'AMBER', 'GREEN')


@pytest.mark.django_db
def test_insights_flag_off_returns_not_ok():
    ensure_exam_feature_flags()
    _enable('exam.ai_prediction_rule', False)
    result = insights_for_attempts([40, 50, 60])
    assert result.get('ok') is False
    # restore
    _enable('exam.ai_prediction_rule', True)


@pytest.mark.django_db
def test_insights_full_series():
    ensure_exam_feature_flags()
    _enable('exam.ai_prediction_rule', True)
    result = insights_for_attempts([45, 52, 60, 58, 65])
    assert result['ok'] is True
    assert result['samples'] == 5
    assert result['last'] == 65.0
    assert isinstance(result['avg'], float)
    assert result['risk_band'] == 'GREEN'
    assert result['predicted_next_pct'] > 0


@pytest.mark.django_db
def test_insights_narrative_absent_when_llm_off():
    ensure_exam_feature_flags()
    _enable('exam.ai_prediction_rule', True)
    _enable('exam.ai_prediction_llm', False)
    result = insights_for_attempts([40, 38, 35, 30])
    assert result['narrative'] is None


@pytest.mark.django_db
def test_insights_narrative_present_when_llm_on():
    ensure_exam_feature_flags()
    _enable('exam.ai_prediction_rule', True)
    _enable('exam.ai_prediction_llm', True)
    result = insights_for_attempts([40, 38, 35, 30])
    assert isinstance(result['narrative'], str)
    assert len(result['narrative']) > 10


# ---------------------------------------------------------------------------
# llm_narrative (standalone)
# ---------------------------------------------------------------------------

def test_llm_narrative_returns_string():
    txt = llm_narrative([40.0, 45.0, 50.0], 55.0)
    assert isinstance(txt, str)
    assert len(txt) > 10


def test_llm_narrative_rising_mentions_improvement():
    txt = llm_narrative([40.0, 50.0, 60.0], 68.0)
    assert any(word in txt.lower() for word in ('improv', 'upward', 'trend', 'well', 'good'))
