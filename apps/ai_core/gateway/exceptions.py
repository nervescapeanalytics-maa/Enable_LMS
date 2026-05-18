"""Structured exceptions raised by the AI gateway."""
from __future__ import annotations


class AIGatewayError(Exception):
    """Base error for the AI gateway."""

    code = "ai_gateway_error"
    http_status = 500

    def __init__(self, message: str = "", *, code: str | None = None, **extra):
        super().__init__(message)
        if code:
            self.code = code
        self.extra = extra

    def to_dict(self) -> dict:
        return {"error": self.code, "message": str(self), **self.extra}


class FeatureDisabled(AIGatewayError):
    code = "feature_disabled"
    http_status = 403


class NoProviderAvailable(AIGatewayError):
    code = "no_provider_available"
    http_status = 503


class RateLimited(AIGatewayError):
    code = "rate_limited"
    http_status = 429


class BudgetExceeded(AIGatewayError):
    code = "budget_exceeded"
    http_status = 429


class SafetyBlocked(AIGatewayError):
    code = "safety_blocked"
    http_status = 400


class UpstreamError(AIGatewayError):
    code = "upstream_error"
    http_status = 502
