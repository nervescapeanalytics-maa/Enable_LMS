"""Token + cost accounting.

Writes:
  - `AIUsageLog`  per request
  - `AIAuditLog`  per request (redacted prompt + response)
  - `AICostTracking` aggregated daily roll-up (upsert via F() expressions)
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db.models import F

from ..models import AIAuditLog, AICostTracking, AIUsageLog

logger = logging.getLogger(__name__)


def _decimal(v) -> Decimal:
    return Decimal(str(v or 0))


def estimate_cost_usd(model, input_tokens: int, output_tokens: int) -> float:
    """Cost = (input/1000)*in_price + (output/1000)*out_price."""
    if not model:
        return 0.0
    ic = float(model.input_cost_per_1k or 0)
    oc = float(model.output_cost_per_1k or 0)
    return round((input_tokens / 1000.0) * ic + (output_tokens / 1000.0) * oc, 6)


def write_usage_and_audit(
    *,
    request,
    feature,
    provider,
    model,
    prompt_version,
    response,
    rendered_system: str = "",
    rendered_user: str = "",
    raw_response_text: str = "",
    redacted_user: str = "",
    redacted_response: str = "",
) -> AIUsageLog:
    """Persist one usage row + paired audit row.

    `request` is the gateway `GatewayRequest`; `response` is the `GatewayResponse`.
    """
    tenant_id = getattr(request, "tenant_id", None) or None
    user = getattr(request, "user", None)
    user_pk = getattr(user, "pk", None) if user else None

    usage = AIUsageLog.objects.create(
        tenant_id=tenant_id,
        request_id=request.request_id,
        correlation_id=request.correlation_id or "",
        status=response.status,
        feature=feature,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        user_id=user_pk,  # FK column for `user` FK
        user_role=request.user_role or "",
        actor_type="user" if user_pk else "system",
        actor_id=str(user_pk) if user_pk else "",
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        total_tokens=response.total_tokens,
        cost_usd=_decimal(response.cost_usd),
        latency_ms=response.latency_ms,
        confidence_score=None,
        abuse_score=None,
        metadata={
            "fallback_used": response.fallback_used,
            "flagged": response.flagged,
            "flag_reason": response.flag_reason,
            "ip": request.ip_address,
        },
    )

    AIAuditLog.objects.create(
        tenant_id=tenant_id,
        usage=usage,
        feature_code=feature.code if feature else "",
        model_name=model.name if model else "",
        provider_name=provider.name if provider else "",
        prompt_text=(rendered_system + "\n---\n" + rendered_user)[:20000],
        response_text=(raw_response_text or response.text)[:20000],
        redacted_prompt=redacted_user[:20000],
        redacted_response=redacted_response[:20000],
        ip_address=request.ip_address or None,
        user_agent=request.user_agent or "",
        flagged=response.flagged,
        flag_reason=response.flag_reason or "",
    )

    # Daily roll-up
    today = date.today()
    obj, _created = AICostTracking.objects.get_or_create(
        tenant_id=tenant_id,
        date=today,
        feature=feature,
        model=model,
        defaults={
            "provider": provider,
            "requests": 0,
            "failed_requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": Decimal("0"),
        },
    )
    AICostTracking.objects.filter(pk=obj.pk).update(
        requests=F("requests") + 1,
        failed_requests=F("failed_requests") + (1 if response.status != "SUCCESS" else 0),
        input_tokens=F("input_tokens") + response.input_tokens,
        output_tokens=F("output_tokens") + response.output_tokens,
        total_tokens=F("total_tokens") + response.total_tokens,
        cost_usd=F("cost_usd") + _decimal(response.cost_usd),
    )
    return usage
