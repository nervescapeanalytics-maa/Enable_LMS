# =============================================================================
# LMS Enterprise - Celery Configuration
# /u01/app/django/apps/lms_enterprise/celery.py
# =============================================================================
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')

app = Celery('lms_enterprise')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic tasks (Celery Beat)
app.conf.beat_schedule = {
    # Purge expired sessions every hour
    'purge-expired-sessions': {
        'task': 'sessions_tracking.tasks.purge_expired_sessions',
        'schedule': 3600.0,
    },
    # Calculate attendance summaries daily at 11:30 PM
    'calculate-attendance-summaries': {
        'task': 'attendance.tasks.calculate_daily_summaries',
        'schedule': crontab(hour=23, minute=30),
    },
    # Reset YouTube quota counters daily at 12:05 AM
    'reset-youtube-quota': {
        'task': 'classes.tasks.reset_youtube_quota',
        'schedule': crontab(hour=0, minute=5),
    },
    # Auto-generate recurring class instances for tomorrow (runs 6:00 AM daily)
    'generate-recurring-classes': {
        'task': 'classes.tasks.generate_recurring_classes',
        'schedule': {
            'hour': 6,
            'minute': 0,
        },
    },
    # Create YouTube broadcasts for classes starting within the next 2 hours (every 30 min)
    'create-pending-youtube-broadcasts': {
        'task': 'classes.tasks.create_pending_youtube_broadcasts',
        'schedule': 1800.0,
    },
    # Run audit purge weekly (Sunday 3 AM)
    'audit-purge': {
        'task': 'audit.tasks.run_purge_policies',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },

    # ── EduAssist Scheduling Tasks ──

    # Generate recurring class sessions nightly at 1 AM
    'generate-recurring-sessions': {
        'task': 'scheduling.tasks.generate_recurring_sessions',
        'schedule': crontab(hour=1, minute=0),
    },
    # Set YouTube streams to STANDBY 12h before class (check every 15 min)
    'set-youtube-standby': {
        'task': 'scheduling.tasks.set_youtube_standby',
        'schedule': crontab(minute='*/15'),
    },
    # Send pre-class notifications 30 min before (check every 5 min)
    'send-pre-class-notifications': {
        'task': 'scheduling.tasks.send_pre_class_notifications',
        'schedule': crontab(minute='*/5'),
    },
    # Handle teacher no-show 30 min after start (check every 5 min)
    'handle-teacher-noshow': {
        'task': 'scheduling.tasks.handle_teacher_noshow',
        'schedule': crontab(minute='*/5'),
    },
    # Archive old classes daily at 2 AM
    'archive-old-classes': {
        'task': 'scheduling.tasks.archive_old_classes',
        'schedule': crontab(hour=2, minute=0),
    },
    # Send notifications when class goes LIVE (check every minute)
    'send-class-live-notifications': {
        'task': 'scheduling.tasks.send_class_live_notifications',
        'schedule': crontab(minute='*/1'),
    },

    # ── Alerting & Monitoring ──
    # Evaluate alert rules every 5 minutes
    'evaluate-alert-rules': {
        'task': 'alerts.evaluate_alert_rules',
        'schedule': crontab(minute='*/5'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
