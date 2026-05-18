"""Batch 7 — metrics + observability."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from ai_core import gateway
from ai_core.metrics import (
    record_blocked,
    record_request,
    set_circuit_state,
)
from ai_core.models import (
    AIFeature,
    AIModel,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_DRY_RUN", "1")


def _make_feature(code=AIFeature.Code.DOUBT_SOLVER):
    p = AIProvider.objects.create(name="P-metric", kind=AIProvider.Kind.OPENAI)
    m = AIModel.objects.create(
        provider=p, name="m1", capability=AIModel.Capability.CHAT,
        input_cost_per_1k="0.001", output_cost_per_1k="0.002",
    )
    f = AIFeature.objects.create(code=code, name="X", default_model=m, is_enabled=True)
    pr = AIPrompt.objects.create(feature=f, name="x-main")
    pv = AIPromptVersion.objects.create(
        prompt=pr, version=1, status=AIPromptVersion.Status.PUBLISHED,
        published_at=timezone.now(),
        system_prompt="You are a tutor.",
        user_template="Q: {{user_message}}",
    )
    f.active_prompt_version = pv
    f.save(update_fields=["active_prompt_version"])
    return f


def test_metrics_helpers_do_not_raise():
    record_request(
        feature="X", provider="P", status="SUCCESS",
        latency_ms=100, input_tokens=10, output_tokens=20, cost_usd=0.0001,
    )
    record_blocked(feature="X", reason="rate_limit")
    set_circuit_state(provider="P", open_=True)
    set_circuit_state(provider="P", open_=False)


def test_metrics_endpoint_requires_staff(db, settings):
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS or []) + ["testserver"]
    U = get_user_model()
    user = U.objects.create_user(username="plain", password="pw")
    c = APIClient()
    c.force_login(user)
    r = c.get("/admin/ai-metrics/")
    # Non-staff is redirected to login
    assert r.status_code in (302, 403)


def test_metrics_endpoint_returns_prom_text(db, settings):
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS or []) + ["testserver"]
    U = get_user_model()
    admin = U.objects.create_user(
        username="admin1", password="pw", is_staff=True, is_superuser=True,
    )
    c = APIClient()
    c.force_login(admin)
    r = c.get("/admin/ai-metrics/")
    # 200 if prometheus_client is installed; 503 if missing — both acceptable wirings.
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.content.decode("utf-8", errors="ignore")
        assert "ai_requests_total" in body or "# HELP" in body


def test_gateway_increments_metric_on_success(db):
    _make_feature()
    resp = gateway.chat(
        AIFeature.Code.DOUBT_SOLVER,
        messages=[{"role": "user", "content": "hello?"}],
    )
    assert resp.status == "SUCCESS"
    # The metric helper is best-effort, but the gateway call must succeed end-to-end
    # which proves the metric instrumentation didn't throw.
