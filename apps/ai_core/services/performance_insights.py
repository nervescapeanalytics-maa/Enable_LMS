"""Feature service: Performance Insights."""
from __future__ import annotations

from .. import gateway
from ..models import AIFeature


def analyze_performance(*, student_summary: dict, period: str = "last 30 days",
                        user=None, tenant_id=None, **extra) -> dict:
    """`student_summary` is a free-form dict of attendance, scores, etc."""
    if not student_summary:
        raise ValueError("student_summary is required")
    summary_lines = []
    for k, v in (student_summary or {}).items():
        summary_lines.append(f"- {k}: {v}")
    user_msg = (
        f"Analyze this student's performance for {period} and write a concise "
        f"insight report (strengths, weaknesses, 3 actionable recommendations). "
        f"Data:\n" + "\n".join(summary_lines)
    )
    variables = {"user_message": user_msg, "period": period, **extra}
    resp = gateway.chat(
        AIFeature.Code.PERFORMANCE_INSIGHTS,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables, user=user, tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["insights"] = resp.text
    return out
