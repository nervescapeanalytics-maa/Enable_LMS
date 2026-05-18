"""Feature service: Practice Quiz generator."""
from __future__ import annotations

import json
import re

from .. import gateway
from ..models import AIFeature


def _extract_json(text: str):
    """Best-effort grab the first JSON array/object from a string."""
    if not text:
        return None
    # Strip ```json fences
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    payload = m.group(1) if m else text
    try:
        return json.loads(payload)
    except Exception:
        pass
    # Find the first {...} or [...] block.
    for start, end in ((payload.find("["), payload.rfind("]")),
                       (payload.find("{"), payload.rfind("}"))):
        if 0 <= start < end:
            try:
                return json.loads(payload[start:end + 1])
            except Exception:
                continue
    return None


def generate_quiz(*, subject: str, topic: str = "", difficulty: str = "medium",
                  count: int = 5, question_types: list | None = None,
                  user=None, tenant_id=None, **extra) -> dict:
    if not subject:
        raise ValueError("subject is required")
    count = max(1, min(int(count or 5), 25))
    types = question_types or ["mcq"]
    user_msg = (
        f"Generate {count} {difficulty} practice questions in JSON.\n"
        f"Subject: {subject}\nTopic: {topic or 'general'}\n"
        f"Question types: {', '.join(types)}\n"
        f"Each question should have: id, type, prompt, options (for MCQ), "
        f"correct_answer, explanation, marks. Return a JSON array."
    )
    variables = {
        "user_message": user_msg,
        "subject": subject, "topic": topic,
        "difficulty": difficulty, "count": count,
        "question_types": ", ".join(types),
        **extra,
    }
    resp = gateway.chat(
        AIFeature.Code.PRACTICE_QUIZ,
        messages=[{"role": "user", "content": user_msg}],
        variables=variables,
        user=user, tenant_id=tenant_id,
    )
    out = resp.to_dict()
    out["raw"] = resp.text
    parsed = _extract_json(resp.text)
    out["questions"] = parsed if isinstance(parsed, list) else []
    return out
