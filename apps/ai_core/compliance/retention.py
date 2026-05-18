"""Retention helpers — called from Celery beat tasks."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def _days(name: str, default: int) -> int:
    return int(getattr(settings, name, default) or default)


def purge_old_usage_logs() -> int:
    """Delete AIUsageLog rows older than AI_GATEWAY_USAGE_RETENTION_DAYS."""
    from ..models import AIUsageLog
    cutoff = timezone.now() - timedelta(days=_days("AI_GATEWAY_USAGE_RETENTION_DAYS", 90))
    deleted, _ = AIUsageLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def purge_old_audit_logs() -> int:
    """Delete AIAuditLog rows older than AI_GATEWAY_AUDIT_RETENTION_DAYS."""
    from ..models import AIAuditLog
    cutoff = timezone.now() - timedelta(days=_days("AI_GATEWAY_AUDIT_RETENTION_DAYS", 365))
    deleted, _ = AIAuditLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def purge_old_feedback() -> int:
    from ..models import AIFeedback
    cutoff = timezone.now() - timedelta(days=_days("AI_GATEWAY_FEEDBACK_RETENTION_DAYS", 365))
    deleted, _ = AIFeedback.objects.filter(created_at__lt=cutoff).delete()
    return deleted
