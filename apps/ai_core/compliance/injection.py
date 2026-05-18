"""Lightweight prompt-injection detector.

Looks for telltale phrases that attempt to override the system prompt
or exfiltrate it. Heuristic only — defense-in-depth, not a panacea.
"""
from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"ignore\s+(?:\w+\s+){0,4}(instructions|prompts|rules|directives)", re.I),
    re.compile(r"disregard\s+(?:\w+\s+){0,4}(instructions|prompts|rules)", re.I),
    re.compile(r"reveal\s+(?:\w+\s+){0,3}(system\s+prompt|hidden\s+prompt|instructions)", re.I),
    re.compile(r"print\s+(?:\w+\s+){0,3}(system\s+prompt|instructions)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I),
    re.compile(r"act\s+as\s+(an?\s+)?(admin|root|system|dan)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"bypass\s+(safety|filter|guardrails?)", re.I),
    re.compile(r"</?system>|</?prompt>", re.I),
]


def is_prompt_injection(text: str) -> bool:
    if not text:
        return False
    for rx in _PATTERNS:
        if rx.search(text):
            return True
    return False
