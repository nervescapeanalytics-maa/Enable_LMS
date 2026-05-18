"""Feature service: AI Learning Path."""
from __future__ import annotations

from .. import gateway
from ..models import AIFeature, AILearningPath


def generate_learning_path(*, student=None, target: str, current_level: str = "",
                           duration_weeks: int = 4, user=None, tenant_id=None,
                           persist: bool = False, **extra) -> dict:
    if not target:
        raise ValueError("target is required")
    user_msg = (
        f"Generate a {duration_weeks}-week learning path.\n"
        f"Target: {target}\nCurrent level: {current_level or 'unknown'}\n"
        f"Output milestones, topics per week and practice activities."
    )
    variables = {
        "user_message": user_msg, "target": target,
        "current_level": current_level, "duration_weeks": duration_weeks,
        **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.LEARNING_PATH,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables, user=user, tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["path"] = resp.text

    if persist and student is not None:
        try:
            path = AILearningPath.objects.create(
                tenant_id=tenant_id,
                student=student,
                kind=AILearningPath.Kind.LEARNING_PATH,
                title=f"Learning path: {target[:80]}",
                summary=target,
                plan={"text": resp.text, "duration_weeks": duration_weeks},
            )
            out["learning_path_id"] = str(path.id)
        except Exception as exc:
            out["persist_error"] = str(exc)
    return out
