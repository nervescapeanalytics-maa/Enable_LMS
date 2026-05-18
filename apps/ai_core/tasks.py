"""Celery tasks for AI governance — retention, beat-driven housekeeping."""
from __future__ import annotations

import logging

from celery import shared_task

from .compliance.retention import (
    purge_old_audit_logs,
    purge_old_feedback,
    purge_old_usage_logs,
)

logger = logging.getLogger(__name__)


@shared_task(name="ai_core.tasks.purge_ai_retention")
def purge_ai_retention() -> dict:
    """Periodic cleanup of AI logs. Wired to celery-beat in production."""
    usage = purge_old_usage_logs()
    audit = purge_old_audit_logs()
    feedback = purge_old_feedback()
    logger.info("ai_core.retention purge: usage=%s audit=%s feedback=%s",
                usage, audit, feedback)
    return {"usage": usage, "audit": audit, "feedback": feedback}
