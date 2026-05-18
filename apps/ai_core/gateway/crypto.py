"""Fernet-based encryption helpers for provider API keys.

If no FERNET key is configured we fall back to plain-text storage with a
visible marker — keys still round-trip but operators are warned via logs.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

_PLAIN_PREFIX = "plain::"
_FERNET_PREFIX = "fernet::"


def _get_fernet():
    try:
        from cryptography.fernet import Fernet  # type: ignore
    except Exception:  # pragma: no cover - cryptography is in requirements
        return None
    raw = os.environ.get("AI_GATEWAY_FERNET_KEY") or os.environ.get("DJANGO_SECRET_KEY")
    if not raw:
        return None
    # Derive a Fernet-compatible 32-byte url-safe base64 key.
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(plain: str) -> str:
    if not plain:
        return ""
    f = _get_fernet()
    if f is None:
        logger.warning("AI gateway: no Fernet key configured; storing API key as plaintext.")
        return _PLAIN_PREFIX + plain
    return _FERNET_PREFIX + f.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_api_key(stored: str) -> str:
    if not stored:
        return ""
    if stored.startswith(_PLAIN_PREFIX):
        return stored[len(_PLAIN_PREFIX):]
    if stored.startswith(_FERNET_PREFIX):
        f = _get_fernet()
        if f is None:
            logger.error("AI gateway: encrypted key found but no Fernet key configured.")
            return ""
        try:
            return f.decrypt(stored[len(_FERNET_PREFIX):].encode("ascii")).decode("utf-8")
        except Exception:  # pragma: no cover
            logger.exception("AI gateway: failed to decrypt API key")
            return ""
    # Legacy unprefixed value — treat as plaintext.
    return stored
