"""Tiny profanity filter (default-deny on a small built-in list).

The real list is intentionally short — replace via the
`AI_GATEWAY_PROFANITY_EXTRA` Django setting in production deployments.
"""
from __future__ import annotations

import re

from django.conf import settings

_BASE_LIST = {
    # Mild explicit words; production deployments should extend via settings.
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "cunt",
}


def _word_set() -> set[str]:
    extra = getattr(settings, "AI_GATEWAY_PROFANITY_EXTRA", None) or []
    return _BASE_LIST | {w.lower() for w in extra}


_WORD_RX = re.compile(r"[A-Za-z']+")


def is_profane(text: str) -> bool:
    if not text:
        return False
    bad = _word_set()
    for token in _WORD_RX.findall(text.lower()):
        if token in bad:
            return True
    return False
