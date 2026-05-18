"""Feature service: Exam Result Planning."""
from __future__ import annotations

from .. import gateway
from ..models import AIFeature


def plan_from_result(*, exam_name: str, scores: dict, target_score: float = None,
                     weak_topics: list | None = None, user=None,
                     tenant_id=None, **extra) -> dict:
    if not exam_name:
        raise ValueError("exam_name is required")
    weak = ", ".join(weak_topics or []) or "none flagged"
    user_msg = (
        f"Analyze the student's {exam_name} result and recommend a "
        f"score-improvement plan.\nScores: {scores}\n"
        f"Target score: {target_score if target_score is not None else 'maximise'}\n"
        f"Weak topics: {weak}"
    )
    variables = {
        "user_message": user_msg, "exam_name": exam_name,
        "target_score": target_score, "weak_topics": weak, **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.EXAM_RESULT_PLANNING,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables, user=user, tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["plan"] = resp.text
    return out
