"""Kind → BaseClient registry + factory.

Honors `AI_GATEWAY_DRY_RUN` (default true) → forces MockClient regardless
of provider config; this keeps unit tests and offline dev safe by default.
"""
from __future__ import annotations

import logging
import os

from django.conf import settings

from ..crypto import decrypt_api_key
from .anthropic_client import AnthropicClient
from .azure_client import AzureOpenAIClient
from .base import BaseClient
from .google_client import GoogleClient
from .local_client import LocalClient
from .mock_client import MockClient
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)

KIND_REGISTRY: dict[str, type[BaseClient]] = {
    "OPENAI": OpenAIClient,
    "ANTHROPIC": AnthropicClient,
    "AZURE_OPENAI": AzureOpenAIClient,
    "GOOGLE": GoogleClient,
    "LOCAL": LocalClient,
    # The following kinds reuse closest-match clients for now:
    "HUGGINGFACE": LocalClient,
    "OPENROUTER": OpenAIClient,
    "WHISPER": OpenAIClient,
}


def _dry_run() -> bool:
    explicit = os.getenv("AI_GATEWAY_DRY_RUN")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return bool(getattr(settings, "AI_GATEWAY_DRY_RUN", True))


def get_client_for_provider(provider) -> BaseClient:
    """Build the appropriate client instance, decrypting the API key once."""
    if _dry_run() or not provider.api_key_encrypted:
        return MockClient(provider, api_key="")
    cls = KIND_REGISTRY.get(provider.kind, MockClient)
    try:
        api_key = decrypt_api_key(provider.api_key_encrypted) if provider.api_key_encrypted else ""
    except Exception as exc:  # pragma: no cover
        logger.warning("AI provider key decrypt failed; falling back to mock (%s)", exc)
        return MockClient(provider, api_key="")
    return cls(provider, api_key=api_key)
