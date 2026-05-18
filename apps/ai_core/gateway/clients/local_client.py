"""Local / self-hosted endpoint client.

Targets either an OpenAI-compatible local server (e.g. vLLM, LM Studio, Ollama
with the OpenAI plugin, llama.cpp server) at provider.base_url.
"""
from __future__ import annotations

from .openai_client import OpenAIClient


class LocalClient(OpenAIClient):
    name = "local"
