"""OpenAI Chat / Embeddings / Whisper / TTS client (thin)."""
from __future__ import annotations

import json
import logging
import urllib.request

from .base import BaseClient, RawCompletion

logger = logging.getLogger(__name__)


class OpenAIClient(BaseClient):
    name = "openai"

    def _post(self, path: str, payload: dict, timeout: int = 30) -> dict:
        base = (self.provider.base_url or "https://api.openai.com").rstrip("/")
        url = f"{base}/v1/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider.extra_headers:
            headers.update(self.provider.extra_headers)
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def chat(self, *, model_name: str, system: str, user: str, **opts) -> RawCompletion:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": user})
        payload = {
            "model": model_name,
            "messages": msgs,
            "temperature": opts.get("temperature", 0.4),
            "max_tokens": opts.get("max_tokens", 1024),
        }
        out = self._post("chat/completions", payload, timeout=self.provider.timeout_seconds or 30)
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage") or {}
        return RawCompletion(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw=out,
        )

    def embed(self, *, model_name: str, texts: list[str], **opts) -> RawCompletion:
        out = self._post("embeddings", {"model": model_name, "input": texts})
        emb = out["data"][0]["embedding"] if out.get("data") else []
        usage = out.get("usage") or {}
        return RawCompletion(
            embedding=emb,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=0,
            raw=out,
        )
