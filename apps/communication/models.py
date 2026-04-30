"""
LMS Enterprise - Communication Models
Support Tickets, Announcements, Direct Messages, Notifications, Notice Board
Replaces legacy: Help, News, Notic_Board, news_users
"""
import uuid
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Support Ticket
# ---------------------------------------------------------------------------
class SupportTicket(models.Model):
    """Support ticket / help request. Replaces legacy [Help]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='support_tickets')

    ticket_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()

    class Category(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical Issue'
        ACCOUNT = 'ACCOUNT', 'Account Related'
        PAYMENT = 'PAYMENT', 'Payment Issue'
        CONTENT = 'CONTENT', 'Content Query'
        EXAM = 'EXAM', 'Exam Related'
        GENERAL = 'GENERAL', 'General'
        FEEDBACK = 'FEEDBACK', 'Feedback'

    category = models.CharField(max_length=15, choices=Category.choices, default=Category.GENERAL)

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    class TicketStatus(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        WAITING = 'WAITING', 'Waiting on User'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'
        REOPENED = 'REOPENED', 'Reopened'

    status = models.CharField(max_length=15, choices=TicketStatus.choices, default=TicketStatus.OPEN)

    # Submitter
    submitted_by_id = models.UUIDField()
    submitted_by_type = models.CharField(max_length=10)
    submitted_by_name = models.CharField(max_length=200, null=True, blank=True)
    submitted_by_email = models.EmailField(null=True, blank=True)

    # Assignee
    assigned_to_id = models.UUIDField(null=True, blank=True)
    assigned_to_type = models.CharField(max_length=10, null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)

    # Attachments
    attachments = models.JSONField(default=list, blank=True)

    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.UUIDField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)
    satisfaction_rating = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # SLA
    first_response_at = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)

    ticket_meta = models.JSONField(null=True, blank=True)
    ext_ticket_1 = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'support_tickets'
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_ticket_status'),
            models.Index(fields=['tenant', 'submitted_by_id'], name='idx_ticket_submitter'),
        ]


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.UUIDField()
    sender_type = models.CharField(max_length=10)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    message = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    is_internal_note = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ticket_messages'
        ordering = ['created_at']


# ---------------------------------------------------------------------------
# Announcement / Notice Board
# ---------------------------------------------------------------------------
class Announcement(models.Model):
    """Announcements / Notice Board. Replaces legacy [News], [Notic_Board]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='announcements')

    title = models.CharField(max_length=500)
    content = models.TextField()
    content_html = models.TextField(null=True, blank=True)
    summary = models.CharField(max_length=500, null=True, blank=True)
    thumbnail = models.URLField(max_length=500, null=True, blank=True)

    class AnnouncementType(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        ACADEMIC = 'ACADEMIC', 'Academic'
        EXAM = 'EXAM', 'Exam'
        EVENT = 'EVENT', 'Event'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        URGENT = 'URGENT', 'Urgent'

    announcement_type = models.CharField(max_length=15, choices=AnnouncementType.choices, default=AnnouncementType.GENERAL)

    class TargetAudience(models.TextChoices):
        ALL = 'ALL', 'All Users'
        STUDENTS = 'STUDENTS', 'Students Only'
        TEACHERS = 'TEACHERS', 'Teachers Only'
        BATCH = 'BATCH', 'Specific Batch'
        CUSTOM = 'CUSTOM', 'Custom'

    target_audience = models.CharField(max_length=10, choices=TargetAudience.choices, default=TargetAudience.ALL)
    target_batches = models.JSONField(default=list, blank=True)
    target_user_ids = models.JSONField(default=list, blank=True)

    is_pinned = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_by_id = models.UUIDField()
    created_by_type = models.CharField(max_length=10)
    created_by_name = models.CharField(max_length=200, null=True, blank=True)

    attachments = models.JSONField(default=list, blank=True)
    view_count = models.IntegerField(default=0)
    acknowledgement_required = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'announcements'
        ordering = ['-is_pinned', '-published_at']
        indexes = [
            models.Index(fields=['tenant', 'is_published', 'target_audience'], name='idx_announcement_audience'),
        ]


class AnnouncementRead(models.Model):
    """Tracks who read/acknowledged an announcement. Replaces legacy [news_users]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    user_id = models.UUIDField()
    user_type = models.CharField(max_length=10)
    read_at = models.DateTimeField(default=timezone.now)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'announcement_reads'
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user_id'],
                name='uq_announcement_read'
            ),
        ]


# ---------------------------------------------------------------------------
# Direct Message
# ---------------------------------------------------------------------------
class DirectMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='direct_messages')

    sender_id = models.UUIDField()
    sender_type = models.CharField(max_length=10)
    sender_name = models.CharField(max_length=200, null=True, blank=True)

    recipient_id = models.UUIDField()
    recipient_type = models.CharField(max_length=10)
    recipient_name = models.CharField(max_length=200, null=True, blank=True)

    subject = models.CharField(max_length=500, null=True, blank=True)
    message = models.TextField()
    attachments = models.JSONField(default=list, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    parent_message = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    thread_id = models.UUIDField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_recipient = models.BooleanField(default=False)

    class Meta:
        db_table = 'direct_messages'
        indexes = [
            models.Index(fields=['tenant', 'recipient_id', 'is_read'], name='idx_dm_recipient'),
            models.Index(fields=['tenant', 'sender_id'], name='idx_dm_sender'),
        ]


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='notifications')

    user_id = models.UUIDField()
    user_type = models.CharField(max_length=10)

    class NotificationType(models.TextChoices):
        INFO = 'INFO', 'Information'
        WARNING = 'WARNING', 'Warning'
        SUCCESS = 'SUCCESS', 'Success'
        ERROR = 'ERROR', 'Error'
        ACTION = 'ACTION_REQUIRED', 'Action Required'

    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.INFO)

    class Channel(models.TextChoices):
        IN_APP = 'IN_APP', 'In-App'
        EMAIL = 'EMAIL', 'Email'
        SMS = 'SMS', 'SMS'
        PUSH = 'PUSH', 'Push'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'

    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)

    title = models.CharField(max_length=500)
    message = models.TextField()
    action_url = models.URLField(max_length=500, null=True, blank=True)
    action_data = models.JSONField(null=True, blank=True)

    # Source
    source_type = models.CharField(max_length=50, null=True, blank=True)
    source_id = models.UUIDField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_error = models.TextField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'is_read'], name='idx_notif_user_read'),
            models.Index(fields=['tenant', 'user_id', 'channel'], name='idx_notif_user_channel'),
        ]
