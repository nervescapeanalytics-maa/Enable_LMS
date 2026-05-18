"""AI safety / compliance subsystem (Batch 5).

Sub-modules:
  pii           — detect + redact personally-identifiable information
  injection     — guard against prompt-injection patterns
  profanity     — basic offensive-language filter
  exam_mode     — block AI use during locked exam sessions
  retention     — celery task helpers for log purging
  export        — GDPR / FERPA user data export

The public entrypoints used by the gateway are:
  - apply_input_guards(req, system_text, user_text)  → (system_text, user_text, redacted_user)
  - apply_output_guards(req, response_text)          → (response_text, redacted_text, flag_reason)
"""
from __future__ import annotations

from .pii import redact_pii
from .injection import is_prompt_injection
from .profanity import is_profane
from .exam_mode import assert_not_in_locked_exam


def apply_input_guards(req, system_text: str, user_text: str) -> tuple[str, str, str]:
    """Run safety checks on inbound text. Raises SafetyBlocked when fatal.

    Returns: (system_text, user_text, redacted_user_for_audit)
    """
    from ..gateway.exceptions import SafetyBlocked

    assert_not_in_locked_exam(req)

    if is_prompt_injection(user_text):
        raise SafetyBlocked(
            "Prompt-injection pattern detected in user input.",
            reason="prompt_injection",
        )
    if is_profane(user_text):
        raise SafetyBlocked(
            "Profanity detected in user input.", reason="profanity",
        )

    redacted_user = redact_pii(user_text)
    return system_text, user_text, redacted_user


def apply_output_guards(req, response_text: str) -> tuple[str, str, str]:
    """Run safety checks on the model's response.

    Returns: (final_response_text, redacted_response_for_audit, flag_reason)
    `flag_reason` is empty unless content was flagged.
    """
    flag = ""
    if is_profane(response_text):
        flag = "profanity_output"
    redacted = redact_pii(response_text)
    return response_text, redacted, flag


__all__ = [
    "apply_input_guards",
    "apply_output_guards",
    "redact_pii",
    "is_prompt_injection",
    "is_profane",
    "assert_not_in_locked_exam",
]
