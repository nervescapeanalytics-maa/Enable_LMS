"""Circuit-breaker logic over AIProvider rows.

A provider is considered "open" (skip) when:
  - is_enabled is False, OR
  - status == OUTAGE / DISABLED, OR
  - circuit_open_until is set and in the future.

Thresholds:
  - 5 consecutive failures → open for 60 seconds (exponential up to 10 minutes).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from ..metrics import set_circuit_state

logger = logging.getLogger(__name__)

FAIL_THRESHOLD = 5
BASE_OPEN_SECONDS = 60
MAX_OPEN_SECONDS = 600


def is_provider_open(provider) -> bool:
    if not provider.is_enabled:
        return True
    if provider.status in ("OUTAGE", "DISABLED"):
        return True
    if provider.circuit_open_until and provider.circuit_open_until > timezone.now():
        return True
    return False


def record_success(provider, latency_ms: int) -> None:
    now = timezone.now()
    # Reset failure counter; ease open window.
    provider.consecutive_failures = 0
    provider.last_success_at = now
    provider.circuit_open_until = None
    if provider.status == "DEGRADED":
        provider.status = "ACTIVE"
    # Rolling avg latency (EMA, alpha=0.2)
    if provider.avg_latency_ms <= 0:
        provider.avg_latency_ms = float(latency_ms)
    else:
        provider.avg_latency_ms = round(0.8 * provider.avg_latency_ms + 0.2 * latency_ms, 2)
    # Rolling success rate (EMA, alpha=0.05)
    provider.success_rate = round(min(1.0, 0.95 * (provider.success_rate or 0.0) + 0.05 * 1.0), 4)
    provider.save(update_fields=[
        "consecutive_failures", "last_success_at", "circuit_open_until",
        "status", "avg_latency_ms", "success_rate", "updated_at",
    ])
    set_circuit_state(provider=provider.name, open_=False)


def record_failure(provider, *, reason: str = "") -> None:
    now = timezone.now()
    provider.consecutive_failures = (provider.consecutive_failures or 0) + 1
    provider.last_failure_at = now
    provider.success_rate = round(max(0.0, 0.95 * (provider.success_rate or 0.0) + 0.05 * 0.0), 4)
    if provider.consecutive_failures >= FAIL_THRESHOLD:
        # Exponential open window.
        seconds = min(MAX_OPEN_SECONDS, BASE_OPEN_SECONDS * 2 ** max(0, provider.consecutive_failures - FAIL_THRESHOLD))
        provider.circuit_open_until = now + timedelta(seconds=seconds)
        provider.status = "OUTAGE"
        logger.warning("AI provider %s circuit OPEN for %ss (reason=%s)", provider.name, seconds, reason)
    else:
        provider.status = "DEGRADED"
    provider.save(update_fields=[
        "consecutive_failures", "last_failure_at", "circuit_open_until",
        "status", "success_rate", "updated_at",
    ])
    set_circuit_state(
        provider=provider.name,
        open_=bool(provider.circuit_open_until and provider.circuit_open_until > now),
    )
