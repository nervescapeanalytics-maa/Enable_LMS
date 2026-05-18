"""Abstract base for provider clients."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass
class RawCompletion:
    text: str = ""
    embedding: list[float] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None


class BaseClient(abc.ABC):
    """A thin synchronous adapter over a single AIProvider row."""

    def __init__(self, provider, api_key: str = "", **kwargs):
        self.provider = provider
        self.api_key = api_key
        self.kwargs = kwargs

    # ---- capability hooks (override the ones you support) ----
    def chat(self, *, model_name: str, system: str, user: str, **opts) -> RawCompletion:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement chat")

    def embed(self, *, model_name: str, texts: list[str], **opts) -> RawCompletion:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement embed")

    def transcribe(self, *, model_name: str, audio_bytes: bytes, **opts) -> RawCompletion:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement transcribe")

    def tts(self, *, model_name: str, text: str, **opts) -> bytes:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement tts")
