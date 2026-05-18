"""User data export for FERPA / GDPR right-to-access requests."""
from __future__ import annotations

from typing import Iterable


def _serialize_usage(row):
    return {
        "request_id": row.request_id,
        "correlation_id": row.correlation_id,
        "feature": row.feature.code if row.feature_id else None,
        "model": row.model.name if row.model_id else None,
        "provider": row.provider.name if row.provider_id else None,
        "status": row.status,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
        "cost_usd": str(row.cost_usd),
        "latency_ms": row.latency_ms,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_audit(row):
    return {
        "feature": row.feature_code,
        "model": row.model_name,
        "provider": row.provider_name,
        "redacted_prompt": row.redacted_prompt,
        "redacted_response": row.redacted_response,
        "flagged": row.flagged,
        "flag_reason": row.flag_reason,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_feedback(row):
    return {
        "usage_request_id": row.usage.request_id if row.usage_id else None,
        "verdict": row.verdict,
        "rating": row.rating,
        "comment": row.comment,
        "created_at": row.created_at.isoformat(),
    }


def export_user_ai_data(user) -> dict:
    """Return a dict containing all AI-related records for *user*."""
    from ..models import AIAuditLog, AIFeedback, AIUsageLog

    if user is None or not getattr(user, "pk", None):
        return {"user_id": None, "usage": [], "audit": [], "feedback": []}

    usage = AIUsageLog.objects.filter(user_id=user.pk).select_related("feature", "model", "provider")
    audit = AIAuditLog.objects.filter(user_id=user.pk)
    feedback = AIFeedback.objects.filter(user_id=user.pk).select_related("usage")

    return {
        "user_id": user.pk,
        "username": getattr(user, "username", ""),
        "email": getattr(user, "email", ""),
        "usage":    [_serialize_usage(r)   for r in usage],
        "audit":    [_serialize_audit(r)   for r in audit],
        "feedback": [_serialize_feedback(r) for r in feedback],
    }


def delete_user_ai_data(user) -> dict:
    """Hard-delete a user's AI history. Returns counts per table."""
    from ..models import AIAuditLog, AIFeedback, AIUsageLog
    if user is None or not getattr(user, "pk", None):
        return {"usage": 0, "audit": 0, "feedback": 0}
    fb, _   = AIFeedback.objects.filter(user_id=user.pk).delete()
    au, _   = AIAuditLog.objects.filter(user_id=user.pk).delete()
    us, _   = AIUsageLog.objects.filter(user_id=user.pk).delete()
    return {"usage": us, "audit": au, "feedback": fb}
