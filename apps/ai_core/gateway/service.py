"""Top-level orchestrator.

`gateway.chat(...)` / `gateway.embed(...)` are the single entry points used
by every feature service. The orchestrator handles:

  1. Feature resolution (tenant-scoped → global fallback)
  2. Quota / rate-limit / budget pre-checks
  3. Prompt template render
  4. Provider/model failover chain
  5. Circuit-breaker awareness
  6. Per-attempt timing
  7. Token + cost metering
  8. Audit log writes
  9. Monthly budget consumption update
"""
from __future__ import annotations

import logging
import time
from typing import Any

from django.db import transaction

from ..compliance import apply_input_guards, apply_output_guards
from ..metrics import record_blocked, record_request
from .breaker import is_provider_open, record_failure, record_success
from .budget import (
    check_and_consume_request,
    check_token_and_cost_budgets,
    pre_check_monthly_budgets,
)
from .clients import get_client_for_provider
from .exceptions import (
    AIGatewayError,
    FeatureDisabled,
    NoProviderAvailable,
    UpstreamError,
)
from .meter import estimate_cost_usd, write_usage_and_audit
from .prompts import render_prompt_version, render_template
from .router import (
    resolve_active_prompt_version,
    resolve_feature,
    resolve_model_chain,
)
from .types import ChatMessage, GatewayRequest, GatewayResponse

logger = logging.getLogger(__name__)


def _last_user_text(messages: list[ChatMessage]) -> str:
    for m in reversed(messages or []):
        if m.role == "user":
            return m.content
    return ""


def _build_request(
    feature_code: str,
    *,
    messages: list[ChatMessage] | list[dict] | None = None,
    user=None,
    tenant_id=None,
    variables: dict[str, Any] | None = None,
    user_role: str = "",
    ip_address: str = "",
    user_agent: str = "",
    correlation_id: str = "",
    extra: dict[str, Any] | None = None,
) -> GatewayRequest:
    msgs: list[ChatMessage] = []
    for m in messages or []:
        if isinstance(m, ChatMessage):
            msgs.append(m)
        elif isinstance(m, dict):
            msgs.append(ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                name=m.get("name"),
                metadata=m.get("metadata", {}) or {},
            ))
    return GatewayRequest(
        feature_code=feature_code,
        messages=msgs,
        user=user,
        tenant_id=tenant_id,
        variables=variables or {},
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        extra=extra or {},
    )


def chat(
    feature_code: str,
    *,
    messages: list | None = None,
    user=None,
    tenant_id=None,
    variables: dict[str, Any] | None = None,
    user_role: str = "",
    ip_address: str = "",
    user_agent: str = "",
    correlation_id: str = "",
    **opts,
) -> GatewayResponse:
    """Run a chat completion through the gateway. Returns `GatewayResponse`."""
    req = _build_request(
        feature_code,
        messages=messages,
        user=user,
        tenant_id=tenant_id,
        variables=variables,
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )

    feature = resolve_feature(feature_code, tenant_id)
    if not feature:
        raise FeatureDisabled(f"AI feature '{feature_code}' is not configured")
    if not feature.is_enabled:
        raise FeatureDisabled(f"AI feature '{feature_code}' is disabled")

    try:
        pre_check_monthly_budgets(feature, tenant_id)
        check_and_consume_request(feature, user, tenant_id)
    except AIGatewayError as exc:
        record_blocked(feature=feature_code, reason=getattr(exc, "code", "blocked"))
        raise

    # Prompt: prefer feature's active prompt version; else use raw last-user message.
    pv = resolve_active_prompt_version(feature)
    last_user = _last_user_text(req.messages)
    if pv:
        vars_ = {"user_message": last_user, **(req.variables or {})}
        system_text, user_text = render_prompt_version(pv, vars_)
        prompt_version_num = pv.version
    else:
        system_text = ""
        user_text = last_user
        prompt_version_num = None

    # Compliance input guards (PII redaction for audit, injection / profanity block)
    try:
        system_text, user_text, redacted_user = apply_input_guards(req, system_text, user_text)
    except AIGatewayError as exc:
        record_blocked(feature=feature_code, reason=getattr(exc, "code", "safety_blocked"))
        raise

    chain = resolve_model_chain(feature, capability="CHAT")
    if not chain:
        raise NoProviderAvailable(f"No enabled models configured for '{feature_code}'")

    response = GatewayResponse(request_id=req.request_id, feature_code=feature_code)
    last_exc: Exception | None = None
    fallback = False

    for idx, model in enumerate(chain):
        provider = model.provider
        if is_provider_open(provider):
            logger.info("ai.gateway: circuit-open skip provider=%s", provider.name)
            continue
        client = get_client_for_provider(provider)
        t0 = time.monotonic()
        try:
            raw = client.chat(
                model_name=model.name,
                system=system_text,
                user=user_text,
                temperature=opts.get("temperature", 0.4),
                max_tokens=opts.get("max_tokens", min(1024, model.max_output_tokens or 1024)),
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            record_success(provider, latency_ms)
            cost = estimate_cost_usd(model, raw.input_tokens, raw.output_tokens)
            response.text = raw.text or ""
            response.raw = raw.raw
            response.provider_name = provider.name
            response.model_name = model.name
            response.prompt_version = prompt_version_num
            response.input_tokens = raw.input_tokens
            response.output_tokens = raw.output_tokens
            response.total_tokens = raw.input_tokens + raw.output_tokens
            response.cost_usd = cost
            response.latency_ms = latency_ms
            response.status = "SUCCESS"
            response.fallback_used = fallback

            # Compliance output guards
            final_text, redacted_response, flag_reason = apply_output_guards(req, raw.text or "")
            response.text = final_text
            if flag_reason:
                response.flagged = True
                response.flag_reason = flag_reason

            try:
                with transaction.atomic():
                    write_usage_and_audit(
                        request=req,
                        feature=feature,
                        provider=provider,
                        model=model,
                        prompt_version=pv,
                        response=response,
                        rendered_system=system_text,
                        rendered_user=user_text,
                        raw_response_text=raw.text or "",
                        redacted_user=redacted_user,
                        redacted_response=redacted_response,
                    )
            except Exception:
                logger.exception("ai.gateway: failed to write usage/audit")

            try:
                check_token_and_cost_budgets(
                    feature, tenant_id,
                    tokens=response.total_tokens, cost_usd=response.cost_usd,
                )
            except Exception:
                logger.exception("ai.gateway: budget bump failed")

            record_request(
                feature=feature_code, provider=provider.name, status=response.status,
                latency_ms=latency_ms, input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens, cost_usd=float(cost),
            )
            return response
        except AIGatewayError:
            raise
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "ai.gateway: provider %s/%s failed (%s); trying next",
                provider.name, model.name, exc,
            )
            record_failure(provider, reason=str(exc)[:200])
            fallback = True
            continue

    msg = f"All providers failed for '{feature_code}'"
    record_request(
        feature=feature_code, provider="(none)", status="FAILED",
        latency_ms=0, input_tokens=0, output_tokens=0, cost_usd=0.0,
    )
    if last_exc:
        raise UpstreamError(msg, cause=str(last_exc)) from last_exc
    raise NoProviderAvailable(msg)


def embed(
    feature_code: str,
    texts: list[str],
    *,
    user=None,
    tenant_id=None,
    user_role: str = "",
    **opts,
) -> GatewayResponse:
    """Run an embedding through the gateway."""
    req = _build_request(feature_code, user=user, tenant_id=tenant_id, user_role=user_role)
    feature = resolve_feature(feature_code, tenant_id)
    if not feature or not feature.is_enabled:
        raise FeatureDisabled(f"AI feature '{feature_code}' is not available")
    pre_check_monthly_budgets(feature, tenant_id)
    check_and_consume_request(feature, user, tenant_id)

    chain = resolve_model_chain(feature, capability="EMBEDDING")
    if not chain:
        raise NoProviderAvailable(f"No embedding model configured for '{feature_code}'")

    response = GatewayResponse(request_id=req.request_id, feature_code=feature_code)
    last_exc = None
    for model in chain:
        provider = model.provider
        if is_provider_open(provider):
            continue
        client = get_client_for_provider(provider)
        t0 = time.monotonic()
        try:
            raw = client.embed(model_name=model.name, texts=texts)
            latency_ms = int((time.monotonic() - t0) * 1000)
            record_success(provider, latency_ms)
            cost = estimate_cost_usd(model, raw.input_tokens, 0)
            response.embedding = raw.embedding
            response.provider_name = provider.name
            response.model_name = model.name
            response.input_tokens = raw.input_tokens
            response.total_tokens = raw.input_tokens
            response.cost_usd = cost
            response.latency_ms = latency_ms
            response.status = "SUCCESS"
            try:
                check_token_and_cost_budgets(
                    feature, tenant_id, tokens=raw.input_tokens, cost_usd=cost,
                )
            except Exception:
                logger.exception("ai.gateway: budget bump failed")
            return response
        except Exception as exc:
            last_exc = exc
            record_failure(provider, reason=str(exc)[:200])
            continue
    if last_exc:
        raise UpstreamError("All embedding providers failed", cause=str(last_exc)) from last_exc
    raise NoProviderAvailable("All embedding providers in outage")


def transcribe(feature_code: str, audio_bytes: bytes, *, user=None, tenant_id=None, **opts) -> GatewayResponse:
    """Speech-to-text via the gateway."""
    req = _build_request(feature_code, user=user, tenant_id=tenant_id)
    feature = resolve_feature(feature_code, tenant_id)
    if not feature or not feature.is_enabled:
        raise FeatureDisabled(f"AI feature '{feature_code}' is not available")
    pre_check_monthly_budgets(feature, tenant_id)
    check_and_consume_request(feature, user, tenant_id)
    chain = resolve_model_chain(feature, capability="STT")
    if not chain:
        raise NoProviderAvailable(f"No STT model configured for '{feature_code}'")
    response = GatewayResponse(request_id=req.request_id, feature_code=feature_code)
    last_exc = None
    for model in chain:
        provider = model.provider
        if is_provider_open(provider):
            continue
        client = get_client_for_provider(provider)
        t0 = time.monotonic()
        try:
            raw = client.transcribe(model_name=model.name, audio_bytes=audio_bytes)
            latency_ms = int((time.monotonic() - t0) * 1000)
            record_success(provider, latency_ms)
            response.text = raw.text
            response.provider_name = provider.name
            response.model_name = model.name
            response.output_tokens = raw.output_tokens
            response.total_tokens = raw.output_tokens
            response.latency_ms = latency_ms
            response.status = "SUCCESS"
            return response
        except Exception as exc:
            last_exc = exc
            record_failure(provider, reason=str(exc)[:200])
    if last_exc:
        raise UpstreamError("All STT providers failed", cause=str(last_exc)) from last_exc
    raise NoProviderAvailable("All STT providers in outage")


def tts(feature_code: str, text: str, *, user=None, tenant_id=None, **opts) -> bytes:
    """Text-to-speech via the gateway. Returns audio bytes."""
    req = _build_request(feature_code, user=user, tenant_id=tenant_id)
    feature = resolve_feature(feature_code, tenant_id)
    if not feature or not feature.is_enabled:
        raise FeatureDisabled(f"AI feature '{feature_code}' is not available")
    pre_check_monthly_budgets(feature, tenant_id)
    check_and_consume_request(feature, user, tenant_id)
    chain = resolve_model_chain(feature, capability="TTS")
    if not chain:
        raise NoProviderAvailable(f"No TTS model configured for '{feature_code}'")
    last_exc = None
    for model in chain:
        provider = model.provider
        if is_provider_open(provider):
            continue
        client = get_client_for_provider(provider)
        t0 = time.monotonic()
        try:
            data = client.tts(model_name=model.name, text=text)
            record_success(provider, int((time.monotonic() - t0) * 1000))
            return data
        except Exception as exc:
            last_exc = exc
            record_failure(provider, reason=str(exc)[:200])
    if last_exc:
        raise UpstreamError("All TTS providers failed", cause=str(last_exc)) from last_exc
    raise NoProviderAvailable("All TTS providers in outage")


def render_prompt(feature_code: str, variables: dict[str, Any], *, tenant_id=None) -> tuple[str, str]:
    """Render a feature's prompt without making an upstream call (preview)."""
    feature = resolve_feature(feature_code, tenant_id)
    if not feature:
        raise FeatureDisabled(f"AI feature '{feature_code}' not configured")
    pv = resolve_active_prompt_version(feature)
    if not pv:
        return "", render_template(variables.get("user_message", ""), variables)
    return render_prompt_version(pv, variables)
