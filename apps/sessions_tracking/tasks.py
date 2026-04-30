"""Celery tasks for session management."""
from celery import shared_task
from django.utils import timezone


@shared_task(name='sessions_tracking.tasks.purge_expired_sessions')
def purge_expired_sessions():
    """Mark expired sessions as EXPIRED and clean up stale records."""
    from sessions_tracking.models import UserSession

    now = timezone.now()
    expired = UserSession.objects.filter(
        status='ACTIVE',
        expires_at__lt=now,
    ).update(
        status='EXPIRED',
        ended_at=now,
        end_reason='Session expired',
    )
    return f'Purged {expired} expired session(s)'
