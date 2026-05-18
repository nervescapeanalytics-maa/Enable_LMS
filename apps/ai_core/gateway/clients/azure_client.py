"""Azure OpenAI client — same wire format as OpenAI but different URL + auth."""
from __future__ import annotations

import json
import urllib.request

from .base import BaseClient, RawCompletion


class AzureOpenAIClient(BaseClient):
    name = "azure_openai"

    def chat(self, *, model_name: str, system: str, user: str, **opts) -> RawCompletion:
        base = (self.provider.base_url or "").rstrip("/")
        if not base:
            raise RuntimeError("Azure OpenAI provider missing base_url (resource endpoint)")
        # base_url should be the resource endpoint;
        # `model_name` is the deployment name.
        api_version = (self.provider.extra_headers or {}).get("api-version", "2024-06-01")
        url = f"{base}/openai/deployments/{model_name}/chat/completions?api-version={api_version}"
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": user})
        payload = {
            "messages": msgs,
            "temperature": opts.get("temperature", 0.4),
            "max_tokens": opts.get("max_tokens", 1024),
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.provider.timeout_seconds or 30) as r:
            out = json.loads(r.read().decode("utf-8"))
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage") or {}
        return RawCompletion(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw=out,
        )
