"""Exam-mode gate.

Students with an active *locked* exam attempt must not be able to invoke
the AI gateway. We look this up best-effort:
  - try to import `assessments.models.AssessmentAttempt` (or similar)
  - check for an open attempt with `lock_ai=True` or status in flight

If the assessments app or schema isn't present, this gate is a no-op.
"""
from __future__ import annotations

from contextlib import suppress


def assert_not_in_locked_exam(req) -> None:
    """Raise `SafetyBlocked` if the request user is mid-exam under AI lock."""
    from ..gateway.exceptions import SafetyBlocked

    user = getattr(req, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return

    # Tenants can opt out via extra={"force_allow_in_exam": True} (admin tooling).
    extra = getattr(req, "extra", {}) or {}
    if extra.get("force_allow_in_exam"):
        return

    with suppress(Exception):
        from assessments.models import AssessmentAttempt  # type: ignore

        qs = AssessmentAttempt.objects.filter(student__user=user).filter(
            status__in=("IN_PROGRESS", "ACTIVE", "STARTED"),
        )
        # Look for a flag on the parent assessment — common patterns:
        for attempt in qs.select_related("assessment").only(
            "id", "status", "assessment__id", "assessment__lock_ai_tools",
        ):
            if getattr(attempt.assessment, "lock_ai_tools", False):
                raise SafetyBlocked(
                    "AI tools are locked during this exam.",
                    reason="exam_lockdown",
                    attempt_id=str(attempt.id),
                )
