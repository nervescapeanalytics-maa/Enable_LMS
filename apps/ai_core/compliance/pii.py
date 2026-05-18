"""PII detection + redaction.

Patterns intentionally err on the side of *redacting* rather than missing
sensitive data. Each match is replaced with a typed placeholder so audit
logs still surface that something was detected.
"""
from __future__ import annotations

import re

# Each tuple: (label, compiled regex)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL",   re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    # US SSN
    ("SSN",     re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Indian Aadhaar (12 digits, optional spaces) — exclude pure-digit runs of other lengths.
    ("AADHAAR", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    # Indian PAN
    ("PAN",     re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    # Credit card (very loose 13-19 digit run with optional separators)
    ("CARD",    re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    # International phone (E.164-ish + common local formats)
    ("PHONE",   re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?)?\d{3}[ -]?\d{4}(?!\d)")),
    # IPv4
    ("IPV4",    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def detect_pii(text: str) -> list[tuple[str, str]]:
    """Return a list of (label, match_text) tuples found in *text*."""
    if not text:
        return []
    found: list[tuple[str, str]] = []
    for label, rx in _PATTERNS:
        for m in rx.finditer(text):
            found.append((label, m.group(0)))
    return found


def redact_pii(text: str) -> str:
    """Return *text* with every PII match replaced by `[REDACTED_<LABEL>]`."""
    if not text:
        return text
    out = text
    for label, rx in _PATTERNS:
        out = rx.sub(f"[REDACTED_{label}]", out)
    return out


def has_pii(text: str) -> bool:
    return bool(detect_pii(text))
