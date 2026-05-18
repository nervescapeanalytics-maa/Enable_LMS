"""Anthropic Messages API client (thin)."""
from __future__ import annotations

import json
import urllib.request

from .base import BaseClient, RawCompletion


class AnthropicClient(BaseClient):
    name = "anthropic"

    def chat(self, *, model_name: str, system: str, user: str, **opts) -> RawCompletion:
        base = (self.provider.base_url or "https://api.anthropic.com").rstrip("/")
        url = f"{base}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "max_tokens": opts.get("max_tokens", 1024),
            "temperature": opts.get("temperature", 0.4),
            "system": system or "",
            "messages": [{"role": "user", "content": user}],
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.provider.timeout_seconds or 30) as r:
            out = json.loads(r.read().decode("utf-8"))
        text = "".join(block.get("text", "") for block in out.get("content", []))
        usage = out.get("usage") or {}
        return RawCompletion(
            text=text,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            raw=out,
        )
