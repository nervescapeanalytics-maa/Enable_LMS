"""Feature service: AI Study Planner."""
from __future__ import annotations

from .. import gateway
from ..models import AIFeature


def generate_plan(*, goal: str, exam_date: str = "", current_level: str = "",
                  subjects: list | None = None, hours_per_day: int = 2,
                  user=None, tenant_id=None, **extra) -> dict:
    if not goal:
        raise ValueError("goal is required")
    user_msg = (
        f"Build a personalized study plan.\n"
        f"Goal: {goal}\n"
        f"Exam date: {exam_date or 'not specified'}\n"
        f"Current level: {current_level or 'unknown'}\n"
        f"Subjects: {', '.join(subjects or []) or 'general'}\n"
        f"Daily study hours: {hours_per_day}\n"
    )
    variables = {
        "user_message": user_msg,
        "goal": goal,
        "exam_date": exam_date,
        "subjects": ", ".join(subjects or []),
        "hours_per_day": hours_per_day,
        "current_level": current_level,
        **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.STUDY_PLANNER,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables,
        user=user,
        tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["plan"] = resp.text
    return out
