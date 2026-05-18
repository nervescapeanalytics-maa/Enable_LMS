"""Feature service: Adaptive Learning."""
from __future__ import annotations

from .. import gateway
from ..models import AIFeature


def next_step(*, recent_performance: dict, current_topic: str = "",
              user=None, tenant_id=None, **extra) -> dict:
    user_msg = (
        f"Given a student's recent performance, recommend the next adaptive "
        f"learning activity. Current topic: {current_topic or 'unknown'}. "
        f"Recent: {recent_performance}"
    )
    variables = {
        "user_message": user_msg, "current_topic": current_topic,
        **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.ADAPTIVE_LEARNING,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables, user=user, tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["recommendation"] = resp.text
    return out
