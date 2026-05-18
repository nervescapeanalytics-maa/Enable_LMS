"""Feature service: AI Doubt Solver."""
from __future__ import annotations

from typing import Any

from .. import gateway
from ..models import AIFeature


def solve_doubt(*, question: str, subject: str = "", topic: str = "",
                grade: str = "", user=None, tenant_id=None, **extra) -> dict:
    """Answer a student's doubt. Returns gateway response as dict."""
    if not question or not question.strip():
        raise ValueError("question is required")
    variables = {
        "user_message": question,
        "subject": subject,
        "topic": topic,
        "grade": grade,
        **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.DOUBT_SOLVER,
        messages=[{"role": "user", "content": question}],
        variables=variables,
        user=user,
        tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["answer"] = resp.text
    out["sources"] = []  # Reserved for future RAG citation chunks
    return out
