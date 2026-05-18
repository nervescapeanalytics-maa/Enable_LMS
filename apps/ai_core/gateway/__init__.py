"""
AI Gateway — the single entry-point for every AI feature in the platform.

Public API (synchronous, thread-safe):

    from ai_core.gateway import chat, embed, transcribe, tts, render_prompt

All calls accept a `feature_code` and resolve provider/model/prompt/quotas/etc.
from the `AIFeature` policy row. The gateway is responsible for:

  * resolving the active prompt version & rendering its template
  * resolving the model (default + failover chain)
  * enforcing per-tenant + per-user budgets & rate limits
  * dispatching to the correct provider client
  * accounting tokens & cost into `AIUsageLog` + `AICostTracking`
  * writing a redacted `AIAuditLog` row
  * tripping the circuit breaker on persistent failures
  * surfacing structured exceptions for callers

When no real API keys are present (development / CI), the gateway falls back
to the deterministic `MockClient` so the rest of the stack is fully testable.
"""
from __future__ import annotations

from .exceptions import (  # noqa: F401
    AIGatewayError,
    BudgetExceeded,
    FeatureDisabled,
    NoProviderAvailable,
    RateLimited,
    SafetyBlocked,
    UpstreamError,
)
from .service import (  # noqa: F401
    chat,
    embed,
    render_prompt,
    transcribe,
    tts,
)
from .types import (  # noqa: F401
    ChatMessage,
    GatewayRequest,
    GatewayResponse,
)
