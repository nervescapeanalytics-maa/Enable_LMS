"""
LMS Enterprise - Real-Time Event Models
For CDC-backed real-time event queue (pre-WebSocket dispatch).
"""
import uuid
from django.db import models
from django.utils import timezone


class RealtimeEvent(models.Model):
    """Persistent event log for WebSocket/push delivery."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='realtime_events', null=True, blank=True
    )

    class EventType(models.TextChoices):
        CLASS_STARTED = 'CLASS_STARTED', 'Class Started'
        CLASS_ENDED = 'CLASS_ENDED', 'Class Ended'
        TEST_PUBLISHED = 'TEST_PUBLISHED', 'Test Published'
        TEST_RESULT = 'TEST_RESULT', 'Test Result Available'
        ANNOUNCEMENT = 'ANNOUNCEMENT', 'New Announcement'
        NOTIFICATION = 'NOTIFICATION', 'Notification'
        ATTENDANCE_MARKED = 'ATTENDANCE_MARKED', 'Attendance Marked'
        SESSION_TERMINATED = 'SESSION_TERMINATED', 'Session Terminated'
        SYSTEM_ALERT = 'SYSTEM_ALERT', 'System Alert'
        CHAT_MESSAGE = 'CHAT_MESSAGE', 'Chat Message'
        CUSTOM = 'CUSTOM', 'Custom Event'

    event_type = models.CharField(max_length=25, choices=EventType.choices)
    event_key = models.CharField(max_length=200, null=True, blank=True)

    # Target
    target_type = models.CharField(max_length=20, null=True, blank=True, help_text='USER, BATCH, TENANT, BROADCAST')
    target_id = models.UUIDField(null=True, blank=True)
    target_channel = models.CharField(max_length=500, null=True, blank=True)

    # Payload
    payload = models.JSONField(default=dict)
    priority = models.IntegerField(default=5)

    # Delivery
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_attempts = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'realtime_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'event_type', 'is_delivered'], name='idx_rt_event_delivery'),
            models.Index(fields=['target_channel', 'is_delivered'], name='idx_rt_event_channel'),
        ]
