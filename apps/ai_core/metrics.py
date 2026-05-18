"""Prometheus metrics for the AI gateway.

This module is import-safe even when prometheus_client isn't installed —
we fall back to no-op stand-ins so tests and minimal deployments work.
"""
from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore
    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROM_AVAILABLE = False

    class _Noop:
        def labels(self, *a, **kw): return self
        def inc(self, *a, **kw): pass
        def dec(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass

    def Counter(*a, **kw): return _Noop()           # type: ignore
    def Gauge(*a, **kw): return _Noop()             # type: ignore
    def Histogram(*a, **kw): return _Noop()         # type: ignore


# --- Definitions -----------------------------------------------------------

ai_requests_total = Counter(
    "ai_requests_total",
    "AI gateway requests handled, partitioned by feature/provider/status.",
    labelnames=("feature", "provider", "status"),
)

ai_request_latency_ms = Histogram(
    "ai_request_latency_ms",
    "AI gateway end-to-end latency in milliseconds.",
    labelnames=("feature", "provider"),
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000),
)

ai_tokens_total = Counter(
    "ai_tokens_total",
    "Total tokens consumed (input + output combined).",
    labelnames=("feature", "provider", "direction"),  # direction = input|output
)

ai_cost_usd_total = Counter(
    "ai_cost_usd_total",
    "Cumulative AI spend in USD (sum of per-request cost estimates).",
    labelnames=("feature", "provider"),
)

ai_provider_circuit_open = Gauge(
    "ai_provider_circuit_open",
    "1 if a provider's circuit breaker is open, else 0.",
    labelnames=("provider",),
)

ai_blocked_total = Counter(
    "ai_blocked_total",
    "Requests blocked by compliance / safety guards.",
    labelnames=("feature", "reason"),
)


# --- Helpers ---------------------------------------------------------------

def record_request(*, feature: str, provider: str, status: str,
                   latency_ms: float, input_tokens: int, output_tokens: int,
                   cost_usd: float) -> None:
    try:
        ai_requests_total.labels(feature, provider, status).inc()
        ai_request_latency_ms.labels(feature, provider).observe(latency_ms)
        if input_tokens:
            ai_tokens_total.labels(feature, provider, "input").inc(input_tokens)
        if output_tokens:
            ai_tokens_total.labels(feature, provider, "output").inc(output_tokens)
        if cost_usd:
            ai_cost_usd_total.labels(feature, provider).inc(float(cost_usd))
    except Exception:
        pass


def record_blocked(*, feature: str, reason: str) -> None:
    try:
        ai_blocked_total.labels(feature, reason).inc()
    except Exception:
        pass


def set_circuit_state(*, provider: str, open_: bool) -> None:
    try:
        ai_provider_circuit_open.labels(provider).set(1 if open_ else 0)
    except Exception:
        pass
