"""Google Gemini generativelanguage.googleapis.com client (thin)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import BaseClient, RawCompletion


class GoogleClient(BaseClient):
    name = "google"

    def chat(self, *, model_name: str, system: str, user: str, **opts) -> RawCompletion:
        base = (self.provider.base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        url = f"{base}/v1beta/models/{model_name}:generateContent?key={urllib.parse.quote(self.api_key)}"
        parts = []
        if system:
            parts.append({"text": f"[SYSTEM]\n{system}"})
        parts.append({"text": user})
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": opts.get("temperature", 0.4),
                "maxOutputTokens": opts.get("max_tokens", 1024),
            },
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.provider.timeout_seconds or 30) as r:
            out = json.loads(r.read().decode("utf-8"))
        cands = out.get("candidates") or []
        text = ""
        if cands:
            text = "".join(p.get("text", "") for p in (cands[0].get("content") or {}).get("parts", []))
        meta = out.get("usageMetadata") or {}
        return RawCompletion(
            text=text,
            input_tokens=int(meta.get("promptTokenCount", 0)),
            output_tokens=int(meta.get("candidatesTokenCount", 0)),
            raw=out,
        )
