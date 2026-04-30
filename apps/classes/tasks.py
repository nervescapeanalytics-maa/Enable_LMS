"""
LMS Enterprise – Celery Tasks for Classes & YouTube
=====================================================

Beat-scheduled tasks:
  • reset_youtube_quota           — 12:05 AM daily
  • generate_recurring_classes    — 6:00 AM daily (creates next-day classes)
  • create_pending_youtube_broadcasts — every 30 minutes (creates broadcasts ~1hr before start)

On-demand tasks (called from admin actions / signals):
  • create_youtube_broadcast_for_class(class_id)
  • go_live_for_class(class_id)
  • end_broadcast_for_class(class_id)
"""

import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. QUOTA RESET  (runs daily 12:05 AM via beat_schedule)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name='classes.tasks.reset_youtube_quota', bind=True, max_retries=3)
def reset_youtube_quota(self):
    """Reset quota_used_today to 0 for all YouTube channels."""
    try:
        from classes.services.youtube_service import YouTubeService
        count = YouTubeService.reset_quota_for_all_channels()
        logger.info("[reset_youtube_quota] Reset quota for %d channels", count)
        return {"reset_channels": count}
    except Exception as exc:
        logger.exception("[reset_youtube_quota] Failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)


# ══════════════════════════════════════════════════════════════════════════════
# 2. GENERATE RECURRING CLASSES  (runs daily 6:00 AM via beat_schedule)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name='classes.tasks.generate_recurring_classes', bind=True, max_retries=2)
def generate_recurring_classes(self):
    """
    Reads all active RecurringClassTemplate records and auto-creates
    ScheduledClass instances for TOMORROW if none already exist.

    Also queues YouTube broadcast creation if the template has
    auto_create_broadcast=True.
    """
    try:
        from classes.models import RecurringClassTemplate, ScheduledClass

        tomorrow = date.today() + timedelta(days=1)
        templates = RecurringClassTemplate.objects.filter(
            is_active=True,
            effective_from__lte=tomorrow,
        ).select_related('teacher', 'batch', 'youtube_channel', 'tenant')

        created_count = 0
        skipped_count = 0

        for tmpl in templates:
            # Skip if past effective_until
            if tmpl.effective_until and tomorrow > tmpl.effective_until:
                continue

            # Skip if recurrence pattern doesn't include tomorrow
            if not tmpl.should_run_on(tomorrow):
                continue

            # Skip if a class for this template + date already exists
            already_exists = ScheduledClass.objects.filter(
                recurring_template=tmpl,
                scheduled_date=tomorrow,
            ).exists()

            if already_exists:
                skipped_count += 1
                continue

            # Build a unique class code: PREFIX-YYYYMMDD
            class_code = f"{tmpl.class_code_prefix}-{tomorrow.strftime('%Y%m%d')}"

            # Create the ScheduledClass instance
            cls = ScheduledClass.objects.create(
                tenant=tmpl.tenant,
                class_code=class_code,
                title=tmpl.title,
                description=tmpl.description,
                scheduled_date=tomorrow,
                start_time=tmpl.start_time,
                end_time=tmpl.end_time,
                duration_minutes=tmpl.duration_minutes,
                class_timezone=tmpl.class_timezone,
                teacher=tmpl.teacher,
                batch=tmpl.batch,
                subject=tmpl.subject,
                youtube_channel=tmpl.youtube_channel,
                privacy_status=tmpl.privacy_status,
                access_type=tmpl.access_type,
                allowed_batches=tmpl.allowed_batches,
                allowed_students=tmpl.allowed_students,
                attendance_mode=tmpl.attendance_mode,
                auto_attendance_threshold_minutes=tmpl.auto_attendance_threshold_minutes,
                min_watch_percent_for_present=tmpl.min_watch_percent_for_present,
                status=ScheduledClass.ClassStatus.SCHEDULED,
                recurring_template=tmpl,
                is_recurring_instance=True,
            )

            # Update template tracking fields
            tmpl.last_generated_date = tomorrow
            tmpl.total_classes_generated += 1
            tmpl.save(update_fields=['last_generated_date', 'total_classes_generated', 'updated_at'])

            created_count += 1
            logger.info(
                "[generate_recurring_classes] Created %s (template=%s)",
                class_code, tmpl.id,
            )

            # Queue YouTube broadcast creation if needed
            if tmpl.auto_create_broadcast and tmpl.youtube_channel:
                create_youtube_broadcast_for_class.delay(str(cls.id))

        logger.info(
            "[generate_recurring_classes] Done. created=%d skipped=%d",
            created_count, skipped_count,
        )
        return {"created": created_count, "skipped": skipped_count}

    except Exception as exc:
        logger.exception("[generate_recurring_classes] Failed: %s", exc)
        raise self.retry(exc=exc, countdown=600)


# ══════════════════════════════════════════════════════════════════════════════
# 3. CREATE YOUTUBE BROADCAST FOR A SPECIFIC CLASS  (on-demand)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name='classes.tasks.create_youtube_broadcast_for_class', bind=True, max_retries=3)
def create_youtube_broadcast_for_class(self, scheduled_class_id: str):
    """
    Create (or recreate) a YouTube Live broadcast for the given ScheduledClass.
    Safe to call multiple times – skips if broadcast already exists.
    """
    try:
        from classes.models import ScheduledClass
        from classes.services.youtube_service import YouTubeService, YouTubeServiceError

        cls = ScheduledClass.objects.select_related('youtube_channel').get(id=scheduled_class_id)

        if cls.youtube_broadcast_id:
            logger.info(
                "[create_youtube_broadcast] Class %s already has broadcast %s, skipping",
                cls.class_code, cls.youtube_broadcast_id,
            )
            return {"status": "skipped", "broadcast_id": cls.youtube_broadcast_id}

        if not cls.youtube_channel:
            logger.warning(
                "[create_youtube_broadcast] Class %s has no youtube_channel set, skipping",
                cls.class_code,
            )
            return {"status": "no_channel"}

        svc = YouTubeService(cls.youtube_channel)
        result = svc.create_broadcast_for_class(cls)

        logger.info(
            "[create_youtube_broadcast] Broadcast created for %s: %s",
            cls.class_code, result["watch_url"],
        )
        return {"status": "created", **result}

    except Exception as exc:
        logger.exception(
            "[create_youtube_broadcast] Failed for class %s: %s",
            scheduled_class_id, exc,
        )
        raise self.retry(exc=exc, countdown=120)


# ══════════════════════════════════════════════════════════════════════════════
# 4. SWEEP: CREATE BROADCASTS FOR ALL UPCOMING CLASSES  (runs every 30 min)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name='classes.tasks.create_pending_youtube_broadcasts', bind=True, max_retries=2)
def create_pending_youtube_broadcasts(self):
    """
    Find all SCHEDULED classes that:
      - start within the next 2 hours
      - have a youtube_channel assigned
      - do NOT yet have a youtube_broadcast_id
    and create their broadcasts.
    """
    try:
        from classes.models import ScheduledClass
        from django.db.models import Q

        now       = timezone.now()
        cutoff    = now + timedelta(hours=2)

        # Get today's date in each class's timezone is complex; we simplify
        # by using UTC date range and filtering at Python level.
        candidates = ScheduledClass.objects.filter(
            status=ScheduledClass.ClassStatus.SCHEDULED,
            youtube_channel__isnull=False,
            youtube_broadcast_id__isnull=True,
        ).select_related('youtube_channel').order_by('scheduled_date', 'start_time')

        queued = 0
        for cls in candidates:
            # Build naive datetime for comparison
            import pytz
            tz = pytz.timezone(cls.class_timezone or 'Asia/Kolkata')
            class_start = tz.localize(
                datetime.combine(cls.scheduled_date, cls.start_time)
            ).astimezone(pytz.utc).replace(tzinfo=None)
            class_start_aware = timezone.make_aware(
                datetime.combine(cls.scheduled_date, cls.start_time), tz
            )

            if now <= class_start_aware <= cutoff:
                create_youtube_broadcast_for_class.delay(str(cls.id))
                queued += 1

        logger.info("[create_pending_youtube_broadcasts] Queued %d broadcast creations", queued)
        return {"queued": queued}

    except Exception as exc:
        logger.exception("[create_pending_youtube_broadcasts] Failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)


# ══════════════════════════════════════════════════════════════════════════════
# 5. GO LIVE / END BROADCAST  (on-demand, called from admin or API)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(name='classes.tasks.go_live_for_class', bind=True, max_retries=2)
def go_live_for_class(self, scheduled_class_id: str):
    """Transition YouTube broadcast to LIVE status."""
    try:
        from classes.models import ScheduledClass
        from classes.services.youtube_service import YouTubeService

        cls = ScheduledClass.objects.select_related('youtube_channel').get(id=scheduled_class_id)
        svc = YouTubeService(cls.youtube_channel)
        svc.go_live(cls)

        cls.actual_start_time = timezone.now()
        cls.status = ScheduledClass.ClassStatus.LIVE
        cls.save(update_fields=['actual_start_time', 'status', 'updated_at'])

        logger.info("[go_live_for_class] Class %s is now LIVE", cls.class_code)
        return {"status": "live", "class_code": cls.class_code}

    except Exception as exc:
        logger.exception("[go_live_for_class] Failed for %s: %s", scheduled_class_id, exc)
        raise self.retry(exc=exc, countdown=30)


@shared_task(name='classes.tasks.end_broadcast_for_class', bind=True, max_retries=2)
def end_broadcast_for_class(self, scheduled_class_id: str):
    """Transition YouTube broadcast to COMPLETE status and mark class done."""
    try:
        from classes.models import ScheduledClass
        from classes.services.youtube_service import YouTubeService

        cls = ScheduledClass.objects.select_related('youtube_channel').get(id=scheduled_class_id)
        svc = YouTubeService(cls.youtube_channel)
        svc.end_broadcast(cls)

        cls.actual_end_time = timezone.now()
        cls.status = ScheduledClass.ClassStatus.COMPLETED
        cls.save(update_fields=['actual_end_time', 'status', 'updated_at'])

        logger.info("[end_broadcast_for_class] Class %s COMPLETED", cls.class_code)
        return {"status": "completed", "class_code": cls.class_code}

    except Exception as exc:
        logger.exception("[end_broadcast_for_class] Failed for %s: %s", scheduled_class_id, exc)
        raise self.retry(exc=exc, countdown=30)
