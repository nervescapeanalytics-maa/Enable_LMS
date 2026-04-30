"""
LMS Enterprise - Classes & YouTube Streaming Models
YouTube Channel, ScheduledClass, ClassAccessToken, ClassWatchTime
"""
import uuid
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# YouTube Channel Configuration
# ---------------------------------------------------------------------------
class YouTubeChannel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='youtube_channels')

    # Channel Identity
    channel_id = models.CharField(max_length=100)
    channel_name = models.CharField(max_length=255, null=True, blank=True)
    channel_url = models.URLField(max_length=500, null=True, blank=True)

    # OAuth Credentials (Encrypted)
    client_id = models.TextField(null=True, blank=True)
    client_secret = models.TextField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Permissions
    scopes = models.JSONField(default=list, blank=True)

    # Ownership
    owned_by_tenant = models.BooleanField(default=True)
    primary_channel = models.BooleanField(default=False)

    # Quota
    daily_quota_limit = models.IntegerField(default=10000)
    quota_used_today = models.IntegerField(default=0)
    quota_reset_at = models.DateTimeField(null=True, blank=True)

    # Status
    class ChannelStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        REVOKED = 'REVOKED', 'Revoked'
        QUOTA_EXCEEDED = 'QUOTA_EXCEEDED', 'Quota Exceeded'

    status = models.CharField(max_length=20, choices=ChannelStatus.choices, default=ChannelStatus.INACTIVE)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    class VerificationStatus(models.TextChoices):
        VERIFIED = 'VERIFIED', 'Verified'
        PENDING = 'PENDING', 'Pending'
        FAILED = 'FAILED', 'Failed'

    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)

    # Assigned Teacher
    assigned_teacher = models.ForeignKey(
        'accounts.Teacher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='youtube_channels'
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    channel_meta = models.JSONField(null=True, blank=True)
    ext_channel_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_channel_2 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'youtube_channels'
        verbose_name = 'YouTube Channel'
        verbose_name_plural = 'YouTube Channels'
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_yt_channel_status'),
        ]

    def __str__(self):
        return f"{self.channel_name} ({self.channel_id})"


# ---------------------------------------------------------------------------
# Scheduled Class
# ---------------------------------------------------------------------------
class ScheduledClass(models.Model):
    """Live/Recorded class with YouTube integration."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='classes')

    # Identity
    class_code = models.CharField(max_length=50)

    # Basic Info
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)

    # Schedule
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField(null=True, blank=True)
    class_timezone = models.CharField(max_length=50, default='Asia/Kolkata', db_column='timezone')

    # Academic Link
    class SubjectChoice(models.TextChoices):
        PHYSICS = 'PHYSICS', 'Physics'
        CHEMISTRY = 'CHEMISTRY', 'Chemistry'
        MATHEMATICS = 'MATHEMATICS', 'Mathematics'
        BIOLOGY = 'BIOLOGY', 'Biology'

    subject = models.CharField(max_length=20, choices=SubjectChoice.choices, null=True, blank=True)
    chapter = models.ForeignKey('academics.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('academics.Topic', on_delete=models.SET_NULL, null=True, blank=True)
    topics_covered = models.JSONField(default=list, blank=True)
    learning_objectives = models.JSONField(default=list, blank=True)

    # YouTube Configuration
    youtube_channel = models.ForeignKey(YouTubeChannel, on_delete=models.SET_NULL, null=True, blank=True)
    youtube_broadcast_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_stream_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_stream_key = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_stream_url = models.URLField(max_length=500, null=True, blank=True)
    youtube_watch_url = models.URLField(max_length=500, null=True, blank=True)
    youtube_embed_url = models.URLField(max_length=500, null=True, blank=True)
    youtube_recording_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_recording_url = models.URLField(max_length=500, null=True, blank=True)

    # Privacy & Access
    class PrivacyStatus(models.TextChoices):
        PRIVATE = 'PRIVATE', 'Private'
        UNLISTED = 'UNLISTED', 'Unlisted'

    privacy_status = models.CharField(max_length=10, choices=PrivacyStatus.choices, default=PrivacyStatus.UNLISTED)

    class AccessType(models.TextChoices):
        BATCH_ONLY = 'BATCH_ONLY', 'Batch Only'
        MULTI_BATCH = 'MULTI_BATCH', 'Multi-Batch'
        ALL_STUDENTS = 'ALL_STUDENTS', 'All Students'
        CUSTOM = 'CUSTOM', 'Custom'

    access_type = models.CharField(max_length=15, choices=AccessType.choices, default=AccessType.BATCH_ONLY)
    allowed_batches = models.JSONField(default=list, blank=True)
    allowed_students = models.JSONField(default=list, blank=True)
    requires_enrollment_check = models.BooleanField(default=True)

    # Access Token
    access_token = models.CharField(max_length=500, unique=True, null=True, blank=True)
    access_token_expires_at = models.DateTimeField(null=True, blank=True)

    # Attendance
    class AttendanceMode(models.TextChoices):
        AUTO = 'AUTO', 'Automatic'
        MANUAL = 'MANUAL', 'Manual'
        HYBRID = 'HYBRID', 'Hybrid'

    attendance_mode = models.CharField(max_length=10, choices=AttendanceMode.choices, default=AttendanceMode.AUTO)
    auto_attendance_threshold_minutes = models.IntegerField(default=15)
    min_watch_percent_for_present = models.IntegerField(default=70)

    # Lifecycle
    class ClassStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        STANDBY = 'STANDBY', 'Standby'
        LIVE = 'LIVE', 'Live'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
        ARCHIVED = 'ARCHIVED', 'Archived'

    status = models.CharField(max_length=15, choices=ClassStatus.choices, default=ClassStatus.DRAFT)
    created_by_id = models.UUIDField(null=True, blank=True)
    created_by_type = models.CharField(max_length=10, null=True, blank=True)

    # Live Tracking
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        'accounts.Teacher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='started_classes'
    )
    ended_by = models.ForeignKey(
        'accounts.Teacher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ended_classes'
    )

    # Teacher Join Tracking
    teacher_joined_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the teacher actually joined/started the class'
    )
    teacher_join_notified = models.BooleanField(
        default=False,
        help_text='Whether a notification was sent confirming the teacher has joined'
    )

    # Stats
    expected_students = models.IntegerField(null=True, blank=True)
    peak_live_viewers = models.IntegerField(null=True, blank=True)
    total_unique_viewers = models.IntegerField(null=True, blank=True)
    average_watch_duration_seconds = models.IntegerField(null=True, blank=True)
    total_chat_messages = models.IntegerField(null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.UUIDField(null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)

    # Rescheduling
    rescheduled_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rescheduled_to'
    )
    reschedule_count = models.IntegerField(default=0, help_text='Number of times this class has been rescheduled. Incremented automatically when a class is moved to a new date/time.')

    # Recurring series link
    recurring_template = models.ForeignKey(
        'RecurringClassTemplate', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='generated_classes',
        help_text="Set automatically when this class was generated from a recurring template"
    )
    is_recurring_instance = models.BooleanField(default=False)

    # Resources
    attached_materials = models.JSONField(default=list, blank=True)
    pre_class_quiz_id = models.UUIDField(null=True, blank=True)
    post_class_quiz_id = models.UUIDField(null=True, blank=True)

    # Relations
    teacher = models.ForeignKey(
        'accounts.Teacher', on_delete=models.CASCADE, related_name='classes'
    )
    batch = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='classes'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Extensions
    class_meta = models.JSONField(null=True, blank=True)
    ext_class_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_class_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_class_3 = models.JSONField(null=True, blank=True)
    ext_class_4 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ext_class_5 = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'scheduled_classes'
        ordering = ['-scheduled_date', '-start_time']
        verbose_name = 'Live Class'
        verbose_name_plural = 'Live Classes'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'class_code'],
                name='uq_class_code_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'scheduled_date'], name='idx_class_date'),
            models.Index(fields=['tenant', 'status'], name='idx_class_status'),
            models.Index(fields=['tenant', 'teacher'], name='idx_class_teacher'),
            models.Index(fields=['tenant', 'batch'], name='idx_class_batch'),
        ]

    def __str__(self):
        return f"{self.class_code} - {self.title}"


# ---------------------------------------------------------------------------
# Recurring Class Template
# ---------------------------------------------------------------------------
class RecurringClassTemplate(models.Model):
    """
    Defines a recurring live class schedule.
    A Celery beat task reads these daily and auto-generates ScheduledClass
    instances (and optionally YouTube broadcasts) for upcoming dates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='recurring_templates')

    # Identity
    title = models.CharField(max_length=500, help_text="e.g. Physics Daily – Batch A")
    description = models.TextField(null=True, blank=True)
    class_code_prefix = models.CharField(
        max_length=30,
        help_text="Auto-generated class codes will be <PREFIX>-YYYYMMDD. e.g. PHY-A"
    )

    # ── Recurrence ──────────────────────────────────────────────────────────
    class RecurrenceType(models.TextChoices):
        DAILY    = 'DAILY',    'Every Day'
        WEEKDAYS = 'WEEKDAYS', 'Weekdays Only (Mon–Fri)'
        WEEKLY   = 'WEEKLY',   'Specific Days of Week'

    recurrence_type = models.CharField(
        max_length=10, choices=RecurrenceType.choices, default=RecurrenceType.DAILY
    )
    # For WEEKLY: list of weekday integers 0=Mon … 6=Sun e.g. [0,2,4] = Mon/Wed/Fri
    recurrence_days = models.JSONField(
        default=list, blank=True,
        help_text="For 'Specific Days': list of weekday numbers [0=Mon … 6=Sun]"
    )

    # ── Timing ──────────────────────────────────────────────────────────────
    start_time = models.TimeField(help_text="Class start time (uses class_timezone)")
    end_time   = models.TimeField(help_text="Class end time")
    duration_minutes = models.IntegerField(null=True, blank=True)
    class_timezone = models.CharField(max_length=50, default='Asia/Kolkata')

    # ── Schedule window ──────────────────────────────────────────────────────
    effective_from  = models.DateField(help_text="Start generating classes from this date")
    effective_until = models.DateField(
        null=True, blank=True,
        help_text="Stop generating after this date. Leave blank to run indefinitely."
    )

    # ── Teacher & Academic ────────────────────────────────────────────────────
    teacher = models.ForeignKey(
        'accounts.Teacher', on_delete=models.CASCADE, related_name='recurring_templates'
    )
    batch = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recurring_templates'
    )

    class SubjectChoice(models.TextChoices):
        PHYSICS     = 'PHYSICS',     'Physics'
        CHEMISTRY   = 'CHEMISTRY',   'Chemistry'
        MATHEMATICS = 'MATHEMATICS', 'Mathematics'
        BIOLOGY     = 'BIOLOGY',     'Biology'

    subject = models.CharField(max_length=20, choices=SubjectChoice.choices, null=True, blank=True)

    # ── YouTube Settings ──────────────────────────────────────────────────────
    youtube_channel = models.ForeignKey(
        YouTubeChannel, on_delete=models.SET_NULL, null=True, blank=True
    )

    class PrivacyStatus(models.TextChoices):
        PRIVATE  = 'PRIVATE',  'Private'
        UNLISTED = 'UNLISTED', 'Unlisted'

    privacy_status = models.CharField(
        max_length=10, choices=PrivacyStatus.choices, default=PrivacyStatus.UNLISTED
    )
    auto_create_broadcast = models.BooleanField(
        default=True,
        help_text="Automatically create a YouTube Live broadcast for each generated class"
    )
    advance_create_hours = models.IntegerField(
        default=1,
        help_text="Create the YouTube broadcast this many hours before class start time"
    )

    # ── Access Control ────────────────────────────────────────────────────────
    class AccessType(models.TextChoices):
        BATCH_ONLY   = 'BATCH_ONLY',   'Batch Only'
        MULTI_BATCH  = 'MULTI_BATCH',  'Multi-Batch'
        ALL_STUDENTS = 'ALL_STUDENTS', 'All Students'
        CUSTOM       = 'CUSTOM',       'Custom'

    access_type     = models.CharField(max_length=15, choices=AccessType.choices, default=AccessType.BATCH_ONLY)
    allowed_batches  = models.JSONField(default=list, blank=True)
    allowed_students = models.JSONField(default=list, blank=True)

    # ── Attendance ────────────────────────────────────────────────────────────
    class AttendanceMode(models.TextChoices):
        AUTO   = 'AUTO',   'Automatic'
        MANUAL = 'MANUAL', 'Manual'
        HYBRID = 'HYBRID', 'Hybrid'

    attendance_mode                  = models.CharField(max_length=10, choices=AttendanceMode.choices, default=AttendanceMode.AUTO)
    auto_attendance_threshold_minutes = models.IntegerField(default=15)
    min_watch_percent_for_present     = models.IntegerField(default=70)

    # ── State ──────────────────────────────────────────────────────────────────
    is_active             = models.BooleanField(default=True)
    last_generated_date   = models.DateField(
        null=True, blank=True,
        help_text="Most recent date a class was auto-generated for this template"
    )
    total_classes_generated = models.IntegerField(default=0)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recurring_class_templates'
        ordering = ['title']
        indexes = [
            models.Index(fields=['tenant', 'is_active'], name='idx_rct_tenant_active'),
            models.Index(fields=['tenant', 'teacher'],   name='idx_rct_tenant_teacher'),
        ]

    def __str__(self):
        return f"{self.class_code_prefix} | {self.title} ({self.get_recurrence_type_display()})"

    def should_run_on(self, date) -> bool:
        """Return True if this template should generate a class on `date`."""
        import datetime
        if self.effective_from and date < self.effective_from:
            return False
        if self.effective_until and date > self.effective_until:
            return False
        if self.recurrence_type == self.RecurrenceType.DAILY:
            return True
        if self.recurrence_type == self.RecurrenceType.WEEKDAYS:
            return date.weekday() < 5          # 0–4 = Mon–Fri
        if self.recurrence_type == self.RecurrenceType.WEEKLY:
            return date.weekday() in (self.recurrence_days or [])
        return False


# ---------------------------------------------------------------------------
# Class Access Token
# ---------------------------------------------------------------------------
class ClassAccessToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    scheduled_class = models.ForeignKey(ScheduledClass, on_delete=models.CASCADE, related_name='access_tokens')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='class_access_tokens')

    token = models.CharField(max_length=500, unique=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_device = models.ForeignKey(
        'sessions_tracking.UserDevice', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    used_ip = models.GenericIPAddressField(null=True, blank=True)

    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=500, null=True, blank=True)

    token_meta = models.JSONField(null=True, blank=True)
    ext_token_1 = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'class_access_tokens'
        verbose_name = 'Class Access Token'
        verbose_name_plural = 'Class Access Tokens'
        indexes = [
            models.Index(fields=['scheduled_class', 'student'], name='idx_cat_class_student'),
            models.Index(fields=['token'], name='idx_cat_token'),
        ]


# ---------------------------------------------------------------------------
# Class Watch Time
# ---------------------------------------------------------------------------
class ClassWatchTime(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    scheduled_class = models.ForeignKey(ScheduledClass, on_delete=models.CASCADE, related_name='watch_times')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='watch_times')
    session = models.ForeignKey(
        'sessions_tracking.UserSession', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    watch_session_id = models.CharField(max_length=200, unique=True)

    # Timing
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    total_watch_seconds = models.IntegerField(default=0)

    # Engagement
    video_progress_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_timestamp_reached = models.IntegerField(null=True, blank=True)
    rewind_count = models.IntegerField(default=0)
    forward_count = models.IntegerField(default=0)
    pause_count = models.IntegerField(default=0)
    playback_speed = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)

    # Quality
    average_quality = models.CharField(max_length=10, null=True, blank=True)
    buffering_count = models.IntegerField(default=0)
    buffering_duration_seconds = models.IntegerField(default=0)

    # Interaction
    chat_messages_sent = models.IntegerField(default=0)
    questions_asked = models.IntegerField(default=0)
    polls_participated = models.IntegerField(default=0)

    # Attention
    tab_switches = models.IntegerField(default=0)
    idle_periods = models.IntegerField(default=0)

    # Device
    device = models.ForeignKey(
        'sessions_tracking.UserDevice', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    device_type = models.CharField(max_length=50, null=True, blank=True)

    # Status
    is_live_watch = models.BooleanField(default=True)

    class CompletionStatus(models.TextChoices):
        PARTIAL = 'PARTIAL', 'Partial'
        COMPLETED = 'COMPLETED', 'Completed'
        MINIMAL = 'MINIMAL', 'Minimal'

    completion_status = models.CharField(max_length=15, choices=CompletionStatus.choices, default=CompletionStatus.PARTIAL)

    # Extensions
    watch_meta = models.JSONField(null=True, blank=True)
    engagement_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ext_watch_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_watch_2 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'class_watch_times'
        verbose_name = 'Class Watch Time'
        verbose_name_plural = 'Class Watch Times'
        indexes = [
            models.Index(fields=['tenant', 'scheduled_class', 'student'], name='idx_cwt_class_student'),
        ]


# ---------------------------------------------------------------------------
# Proxy models to surface system_config items under "Live Classes & YouTube"
# ---------------------------------------------------------------------------
from system_config.models import ClassLinkConfig as _ClassLinkConfig
from system_config.models import IntegrationConfig as _IntegrationConfig


class ClassLinkConfigProxy(_ClassLinkConfig):
    class Meta:
        proxy = True
        verbose_name = 'Streaming Platform'
        verbose_name_plural = 'Streaming Platforms'


class IntegrationConfigProxy(_IntegrationConfig):
    class Meta:
        proxy = True
        verbose_name = 'YouTube Integration Config'
        verbose_name_plural = 'YouTube Integration Configs'
