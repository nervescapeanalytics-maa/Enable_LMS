"""Batch 2 — AI Gateway service layer tests.

Validates: routing, mock client integration, audit/usage/cost rows, prompt
template rendering, rate-limit / quota enforcement, circuit breaker, and
provider failover.
"""
from __future__ import annotations

import os

import pytest
from django.core.cache import cache
from django.utils import timezone

from ai_core import gateway
from ai_core.gateway import (
    BudgetExceeded,
    FeatureDisabled,
    NoProviderAvailable,
    RateLimited,
)
from ai_core.gateway import breaker as breaker_mod
from ai_core.gateway.clients.mock_client import MockClient
from ai_core.gateway.prompts import render_prompt_version, render_template
from ai_core.models import (
    AIAuditLog,
    AICostTracking,
    AIFeature,
    AIModel,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
    AIUsageLog,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_dry_run(monkeypatch):
    """Force MockClient regardless of provider api_key state."""
    monkeypatch.setenv("AI_GATEWAY_DRY_RUN", "1")
    cache.clear()
    yield
    cache.clear()


def _make_feature(code=AIFeature.Code.DOUBT_SOLVER, *, with_prompt=True, **fkwargs):
    p = AIProvider.objects.create(name=f"P-{code}", kind=AIProvider.Kind.OPENAI, priority=10)
    m = AIModel.objects.create(
        provider=p, name="gpt-test", capability=AIModel.Capability.CHAT,
        input_cost_per_1k="0.001", output_cost_per_1k="0.002",
    )
    f = AIFeature.objects.create(
        code=code, name=str(code), default_model=m, is_enabled=True,
        **fkwargs,
    )
    if with_prompt:
        pr = AIPrompt.objects.create(feature=f, name=f"{code}-main")
        pv = AIPromptVersion.objects.create(
            prompt=pr, version=1, status=AIPromptVersion.Status.PUBLISHED,
            published_at=timezone.now(),
            system_prompt="You are a helpful tutor for {{subject}}.",
            user_template="Question: {{user_message}}",
            variables={"subject": "math"},
        )
        f.active_prompt_version = pv
        f.save(update_fields=["active_prompt_version"])
    return f, p, m


def test_render_template_jinja_and_fallback():
    assert "Hello Alice" in render_template("Hello {{name}}", {"name": "Alice"})


def test_chat_happy_path_writes_usage_audit_cost():
    f, p, m = _make_feature()
    resp = gateway.chat(
        f.code,
        messages=[{"role": "user", "content": "What is 2+2?"}],
        variables={"subject": "arithmetic"},
    )
    assert resp.status == "SUCCESS"
    assert resp.provider_name == p.name
    assert resp.model_name == m.name
    assert resp.text  # mock returns non-empty
    assert resp.total_tokens > 0
    assert resp.cost_usd >= 0

    assert AIUsageLog.objects.filter(feature=f, status="SUCCESS").count() == 1
    assert AIAuditLog.objects.filter(feature_code=f.code).count() == 1
    cost_row = AICostTracking.objects.get(feature=f, model=m)
    assert cost_row.requests == 1


def test_disabled_feature_raises():
    f, _, _ = _make_feature(code=AIFeature.Code.STUDY_PLANNER)
    f.is_enabled = False
    f.save()
    with pytest.raises(FeatureDisabled):
        gateway.chat(f.code, messages=[{"role": "user", "content": "hi"}])


def test_unknown_feature_raises():
    with pytest.raises(FeatureDisabled):
        gateway.chat("DOES_NOT_EXIST", messages=[{"role": "user", "content": "hi"}])


def test_rate_limit_enforced():
    f, _, _ = _make_feature(
        code=AIFeature.Code.PRACTICE_QUIZ,
        rate_limit_per_minute=2,
    )
    msgs = [{"role": "user", "content": "Q?"}]
    gateway.chat(f.code, messages=msgs)
    gateway.chat(f.code, messages=msgs)
    with pytest.raises(RateLimited):
        gateway.chat(f.code, messages=msgs)


def test_daily_request_budget_enforced():
    f, _, _ = _make_feature(
        code=AIFeature.Code.PERFORMANCE_INSIGHTS,
        daily_request_budget=1,
    )
    gateway.chat(f.code, messages=[{"role": "user", "content": "Q1"}])
    with pytest.raises(BudgetExceeded):
        gateway.chat(f.code, messages=[{"role": "user", "content": "Q2"}])


def test_failover_to_fallback_provider(monkeypatch):
    f, primary_provider, primary_model = _make_feature(code=AIFeature.Code.LEARNING_PATH)
    fb_provider = AIProvider.objects.create(name="FB", kind=AIProvider.Kind.LOCAL, priority=20)
    fb_model = AIModel.objects.create(
        provider=fb_provider, name="fb-model", capability=AIModel.Capability.CHAT,
        input_cost_per_1k="0.001", output_cost_per_1k="0.002",
    )
    f.fallback_models.add(fb_model)

    real_chat = MockClient.chat

    def flaky_chat(self, **kw):
        if self.provider.id == primary_provider.id:
            raise RuntimeError("boom")
        return real_chat(self, **kw)

    monkeypatch.setattr(MockClient, "chat", flaky_chat)

    resp = gateway.chat(f.code, messages=[{"role": "user", "content": "Hi"}])
    assert resp.status == "SUCCESS"
    assert resp.provider_name == fb_provider.name
    assert resp.fallback_used is True

    primary_provider.refresh_from_db()
    assert primary_provider.consecutive_failures >= 1


def test_circuit_breaker_opens_after_threshold(monkeypatch):
    f, primary_provider, _ = _make_feature(code=AIFeature.Code.ADAPTIVE_LEARNING)

    def boom(self, **kw):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(MockClient, "chat", boom)

    # Hit failures until threshold; only ONE provider so each attempt also
    # raises NoProviderAvailable/UpstreamError.
    for _ in range(breaker_mod.FAIL_THRESHOLD):
        with pytest.raises(Exception):
            gateway.chat(f.code, messages=[{"role": "user", "content": "x"}])

    primary_provider.refresh_from_db()
    assert primary_provider.consecutive_failures >= breaker_mod.FAIL_THRESHOLD
    assert primary_provider.circuit_open_until is not None
    assert primary_provider.status == AIProvider.Status.OUTAGE


def test_no_provider_available_raises():
    f, _, m = _make_feature(code=AIFeature.Code.EXAM_RESULT_PLANNING)
    # Disable the only model + provider
    m.is_enabled = False
    m.save()
    with pytest.raises(NoProviderAvailable):
        gateway.chat(f.code, messages=[{"role": "user", "content": "Hi"}])


def test_render_prompt_preview_without_call():
    f, _, _ = _make_feature(code=AIFeature.Code.DOUBT_SOLVER)
    system, user = gateway.render_prompt(
        f.code, {"subject": "physics", "user_message": "Define momentum"},
    )
    assert "physics" in system
    assert "momentum" in user
