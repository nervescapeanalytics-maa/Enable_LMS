"""Plain dataclasses used by the gateway API."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class GatewayRequest:
    feature_code: str
    messages: list[ChatMessage] = field(default_factory=list)
    user: Any = None  # accounts.User-like instance (or None)
    tenant_id: Any = None  # UUID/str/None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    user_role: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayResponse:
    request_id: str
    feature_code: str
    text: str = ""
    embedding: list[float] | None = None
    raw: Any = None

    # Routing trail
    provider_name: str = ""
    model_name: str = ""
    prompt_version: int | None = None

    # Cost / usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0

    # Safety / status
    status: str = "SUCCESS"  # SUCCESS | FAILED | TIMEOUT | BLOCKED | RATE_LIMITED | FALLBACK
    fallback_used: bool = False
    flagged: bool = False
    flag_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "feature_code": self.feature_code,
            "text": self.text,
            "provider": self.provider_name,
            "model": self.model_name,
            "prompt_version": self.prompt_version,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
            },
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "flagged": self.flagged,
        }
