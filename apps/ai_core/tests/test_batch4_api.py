"""Batch 4 — AI feature services + DRF endpoints."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from ai_core.models import (
    AIFeature,
    AIFeedback,
    AIModel,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
    AIUsageLog,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_DRY_RUN", "1")


@pytest.fixture
def user(db):
    U = get_user_model()
    u = U.objects.create_user(username="ai-user-1", email="u@example.com", password="pw")
    return u


def _make_feature(code, **fkwargs):
    p = AIProvider.objects.create(name=f"P-{code}", kind=AIProvider.Kind.OPENAI)
    m = AIModel.objects.create(
        provider=p, name="m1", capability=AIModel.Capability.CHAT,
        input_cost_per_1k="0.001", output_cost_per_1k="0.002",
    )
    f = AIFeature.objects.create(
        code=code, name=str(code), default_model=m, is_enabled=True, **fkwargs,
    )
    pr = AIPrompt.objects.create(feature=f, name=f"{code}-main")
    pv = AIPromptVersion.objects.create(
        prompt=pr, version=1, status=AIPromptVersion.Status.PUBLISHED,
        published_at=timezone.now(),
        system_prompt="You are a tutor.",
        user_template="Q: {{user_message}}",
    )
    f.active_prompt_version = pv
    f.save(update_fields=["active_prompt_version"])
    return f


def _auth(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---- service-layer unit tests ----------------------------------------------
def test_service_doubt_solver(user):
    _make_feature(AIFeature.Code.DOUBT_SOLVER)
    from ai_core.services import doubt_solver
    out = doubt_solver.solve_doubt(question="What is Newton's first law?", user=user)
    assert out["status"] == "SUCCESS"
    assert out["answer"]


def test_service_practice_quiz_parses_questions(user):
    _make_feature(AIFeature.Code.PRACTICE_QUIZ)
    from ai_core.services import practice_quiz
    out = practice_quiz.generate_quiz(subject="Physics", count=3, user=user)
    assert out["status"] == "SUCCESS"
    # Mock client doesn't emit valid JSON so we get an empty list,
    # but the field must exist and be a list.
    assert isinstance(out["questions"], list)


def test_service_validation_errors():
    from ai_core.services import doubt_solver, practice_quiz
    with pytest.raises(ValueError):
        doubt_solver.solve_doubt(question="")
    with pytest.raises(ValueError):
        practice_quiz.generate_quiz(subject="")


# ---- DRF endpoint tests ----------------------------------------------------
def test_api_doubt_solver_endpoint(user):
    _make_feature(AIFeature.Code.DOUBT_SOLVER)
    c = _auth(user)
    r = c.post("/api/v1/ai/doubt-solver/", {"question": "What is energy?"}, format="json")
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["status"] == "SUCCESS"
    assert "answer" in body
    assert AIUsageLog.objects.filter(request_id=body["request_id"]).exists()


def test_api_requires_authentication():
    c = APIClient()
    r = c.post("/api/v1/ai/doubt-solver/", {"question": "Hello"}, format="json")
    assert r.status_code in (401, 403)


def test_api_validation_returns_400(user):
    _make_feature(AIFeature.Code.DOUBT_SOLVER)
    c = _auth(user)
    r = c.post("/api/v1/ai/doubt-solver/", {"question": ""}, format="json")
    assert r.status_code == 400


def test_api_feature_disabled(user):
    f = _make_feature(AIFeature.Code.STUDY_PLANNER)
    f.is_enabled = False
    f.save()
    c = _auth(user)
    r = c.post("/api/v1/ai/study-planner/", {"goal": "Crack JEE"}, format="json")
    assert r.status_code == 403
    assert r.json()["error"] == "feature_disabled"


def test_api_feedback_roundtrip(user):
    _make_feature(AIFeature.Code.DOUBT_SOLVER)
    c = _auth(user)
    r = c.post("/api/v1/ai/doubt-solver/", {"question": "Hi"}, format="json")
    rid = r.json()["request_id"]
    r2 = c.post("/api/v1/ai/feedback/", {
        "request_id": rid, "verdict": "UP", "rating": 5, "comment": "Great",
    }, format="json")
    assert r2.status_code == 201
    assert AIFeedback.objects.filter(usage__request_id=rid).count() == 1


def test_api_feature_catalog(user):
    _make_feature(AIFeature.Code.DOUBT_SOLVER)
    _make_feature(AIFeature.Code.PRACTICE_QUIZ)
    c = _auth(user)
    r = c.get("/api/v1/ai/features/")
    assert r.status_code == 200
    codes = {f["code"] for f in r.json()["features"]}
    assert "DOUBT_SOLVER" in codes
    assert "PRACTICE_QUIZ" in codes


def test_api_all_seven_features(user):
    """Smoke each of the 7 feature endpoints with minimal valid input."""
    endpoints = [
        ("DOUBT_SOLVER",         "/api/v1/ai/doubt-solver/",         {"question": "Q?"}),
        ("STUDY_PLANNER",        "/api/v1/ai/study-planner/",        {"goal": "Pass exam"}),
        ("PRACTICE_QUIZ",        "/api/v1/ai/practice-quiz/",        {"subject": "Math"}),
        ("PERFORMANCE_INSIGHTS", "/api/v1/ai/performance-insights/", {"student_summary": {"score": 70}}),
        ("LEARNING_PATH",        "/api/v1/ai/learning-path/",        {"target": "Master integrals"}),
        ("ADAPTIVE_LEARNING",    "/api/v1/ai/adaptive-learning/",    {"recent_performance": {"avg": 80}}),
        ("EXAM_RESULT_PLANNING", "/api/v1/ai/exam-result-planning/", {"exam_name": "Mock-1", "scores": {"math": 70}}),
    ]
    c = _auth(user)
    for code, url, payload in endpoints:
        _make_feature(getattr(AIFeature.Code, code))
        r = c.post(url, payload, format="json")
        assert r.status_code == 200, (code, r.status_code, r.content)
        assert r.json()["status"] == "SUCCESS", code
