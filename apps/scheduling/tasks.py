"""
Scheduling - Celery Tasks

Automated background tasks:
1. generate_recurring_sessions — Nightly: create class sessions from rules for next 30 days
2. set_youtube_standby — Every 15 min: set up YouTube streams 12h before class
3. send_pre_class_notifications — Every 5 min: notify 30 min before class
4. handle_teacher_noshow — Every 5 min: cancel if teacher didn't go live within 30 min
5. archive_old_classes — Daily: archive completed classes older than 30 days
6. send_class_live_notifications — Every minute: notify students when class goes live
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('lms')


# ---------------------------------------------------------------------------
# 1. Nightly Session Generation
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.generate_recurring_sessions')
def generate_recurring_sessions():
    """
    Run every night. Reads all active recurring rules and creates
    ScheduledClass sessions for the next 30 days.
    Skips blackout dates automatically.
    """
    from scheduling.services import generate_all_sessions
    count = generate_all_sessions(horizon_days=30)
    logger.info(f"[generate_recurring_sessions] Created {count} sessions total.")
    return {'sessions_created': count}


# ---------------------------------------------------------------------------
# 2. YouTube Standby (12 hours before class)
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.set_youtube_standby')
def set_youtube_standby():
    """
    Check for SCHEDULED classes within the next 12 hours.
    Set up the YouTube live stream and move status to STANDBY.
    The teacher will then see a "Go Live" button.
    """
    from classes.models import ScheduledClass
    from datetime import datetime, date as dt_date

    now = timezone.now()
    cutoff = now + timedelta(hours=12)

    classes = ScheduledClass.objects.filter(
        status=ScheduledClass.ClassStatus.SCHEDULED,
        scheduled_date__lte=cutoff.date(),
    )

    standby_count = 0
    for cls in classes:
        # Build full datetime
        cls_datetime = timezone.make_aware(
            datetime.combine(cls.scheduled_date, cls.start_time),
            timezone.get_current_timezone()
        )

        if now <= cls_datetime <= cutoff:
            # In a real system, this is where we call YouTube API
            # to create the broadcast and get the embed URL + stream key.
            # For now, we just update the status.
            cls.status = 'STANDBY'
            cls.save(update_fields=['status', 'updated_at'])
            standby_count += 1
            logger.info(f"[set_youtube_standby] Class {cls.class_code} → STANDBY")

    return {'standby_count': standby_count}


# ---------------------------------------------------------------------------
# 3. Pre-class Notifications (30 minutes before)
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.send_pre_class_notifications')
def send_pre_class_notifications():
    """
    Find classes starting in the next 30-35 minutes and send notifications
    to teachers and enrolled students.
    """
    from classes.models import ScheduledClass
    from scheduling.notification_service import (
        notify_teacher_pre_class,
        notify_students_pre_class,
    )
    from datetime import datetime

    now = timezone.now()
    window_start = now + timedelta(minutes=25)
    window_end = now + timedelta(minutes=35)

    # Find standby classes in the notification window
    classes = ScheduledClass.objects.filter(
        status='STANDBY',
    )

    notified = 0
    for cls in classes:
        cls_datetime = timezone.make_aware(
            datetime.combine(cls.scheduled_date, cls.start_time),
            timezone.get_current_timezone()
        )
        if window_start <= cls_datetime <= window_end:
            # Check if already notified (use meta)
            meta = cls.class_meta or {}
            if meta.get('pre_class_notified'):
                continue

            notify_teacher_pre_class(cls)
            notify_students_pre_class(cls)

            meta['pre_class_notified'] = True
            cls.class_meta = meta
            cls.save(update_fields=['class_meta', 'updated_at'])
            notified += 1

    return {'notified_classes': notified}


# ---------------------------------------------------------------------------
# 4. Teacher No-Show Handling (30 min after class time)
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.handle_teacher_noshow')
def handle_teacher_noshow():
    """
    If a class is in STANDBY and 30+ minutes past its scheduled time,
    the teacher did not go live. Auto-cancel and notify.
    """
    from classes.models import ScheduledClass
    from scheduling.notification_service import (
        notify_students_class_cancelled,
        notify_admin_teacher_noshow,
    )
    from datetime import datetime

    now = timezone.now()
    noshow_threshold = now - timedelta(minutes=30)

    classes = ScheduledClass.objects.filter(status='STANDBY')

    cancelled = 0
    for cls in classes:
        cls_datetime = timezone.make_aware(
            datetime.combine(cls.scheduled_date, cls.start_time),
            timezone.get_current_timezone()
        )
        if cls_datetime <= noshow_threshold:
            cls.status = ScheduledClass.ClassStatus.CANCELLED
            cls.cancellation_reason = 'Teacher no-show — auto-cancelled after 30 minutes.'
            cls.cancelled_at = now
            cls.save(update_fields=[
                'status', 'cancellation_reason', 'cancelled_at', 'updated_at'
            ])

            notify_students_class_cancelled(cls)
            notify_admin_teacher_noshow(cls)
            cancelled += 1
            logger.warning(f"[teacher_noshow] Class {cls.class_code} cancelled (teacher no-show)")

    return {'cancelled_count': cancelled}


# ---------------------------------------------------------------------------
# 5. Archive Old Classes (30 days after completion)
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.archive_old_classes')
def archive_old_classes():
    """
    Move COMPLETED classes older than 30 days to ARCHIVED status.
    Recordings remain accessible.
    """
    from classes.models import ScheduledClass

    cutoff = timezone.now() - timedelta(days=30)
    updated = ScheduledClass.objects.filter(
        status=ScheduledClass.ClassStatus.COMPLETED,
        actual_end_time__lte=cutoff,
    ).update(status='ARCHIVED')

    logger.info(f"[archive_old_classes] Archived {updated} classes.")
    return {'archived_count': updated}


# ---------------------------------------------------------------------------
# 6. Class Live Notifications
# ---------------------------------------------------------------------------
@shared_task(name='scheduling.tasks.send_class_live_notifications')
def send_class_live_notifications():
    """
    When a class transitions to LIVE status, notify enrolled students.
    Check for newly-live classes that haven't had notifications sent yet.
    """
    from classes.models import ScheduledClass
    from scheduling.notification_service import notify_students_class_live

    classes = ScheduledClass.objects.filter(status=ScheduledClass.ClassStatus.LIVE)

    notified = 0
    for cls in classes:
        meta = cls.class_meta or {}
        if meta.get('live_notified'):
            continue

        notify_students_class_live(cls)
        meta['live_notified'] = True
        cls.class_meta = meta
        cls.save(update_fields=['class_meta', 'updated_at'])
        notified += 1

    return {'notified_classes': notified}
