"""
LMS Enterprise - Session, Device & Activity Tracking Models
Replaces legacy: login_history_student, login_history_teacher, session
"""
import uuid
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# User Device
# ---------------------------------------------------------------------------
class UserDevice(models.Model):
    """Registered devices for users."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='devices')

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    device_fingerprint = models.CharField(max_length=500, unique=True)
    device_name = models.CharField(max_length=200, null=True, blank=True)

    class DeviceType(models.TextChoices):
        DESKTOP = 'DESKTOP', 'Desktop'
        LAPTOP = 'LAPTOP', 'Laptop'
        MOBILE = 'MOBILE', 'Mobile'
        TABLET = 'TABLET', 'Tablet'
        OTHER = 'OTHER', 'Other'

    device_type = models.CharField(max_length=10, choices=DeviceType.choices, null=True, blank=True)
    os_name = models.CharField(max_length=100, null=True, blank=True)
    os_version = models.CharField(max_length=50, null=True, blank=True)
    browser_name = models.CharField(max_length=100, null=True, blank=True)
    browser_version = models.CharField(max_length=50, null=True, blank=True)
    screen_resolution = models.CharField(max_length=20, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    is_trusted = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.CharField(max_length=500, null=True, blank=True)

    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    total_sessions = models.IntegerField(default=0)

    push_token = models.TextField(null=True, blank=True)
    push_platform = models.CharField(max_length=20, null=True, blank=True)

    device_meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'user_devices'
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'user_type'], name='idx_device_user'),
        ]


# ---------------------------------------------------------------------------
# User Session
# ---------------------------------------------------------------------------
class UserSession(models.Model):
    """User session tracking. Replaces legacy [session]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='user_sessions')

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    session_token = models.CharField(max_length=500, unique=True, db_index=True)
    refresh_token_hash = models.CharField(max_length=500, null=True, blank=True)

    device = models.ForeignKey(UserDevice, on_delete=models.SET_NULL, null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    geo_city = models.CharField(max_length=100, null=True, blank=True)
    geo_state = models.CharField(max_length=100, null=True, blank=True)
    geo_country = models.CharField(max_length=100, null=True, blank=True)
    geo_coordinates = models.CharField(max_length=50, null=True, blank=True)

    started_at = models.DateTimeField(default=timezone.now)
    last_activity_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class SessionStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        LOGGED_OUT = 'LOGGED_OUT', 'Logged Out'
        REVOKED = 'REVOKED', 'Revoked'
        FORCE_TERMINATED = 'FORCE_TERMINATED', 'Force Terminated'

    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.ACTIVE)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=500, null=True, blank=True)

    # Duration
    total_active_seconds = models.IntegerField(default=0)

    # Anti-sharing
    concurrent_session_check = models.BooleanField(default=True)
    is_primary_session = models.BooleanField(default=True)

    session_meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'status'], name='idx_session_user_status'),
            models.Index(fields=['session_token'], name='idx_session_token'),
            models.Index(fields=['tenant', 'status', 'expires_at'], name='idx_session_expiry'),
        ]


# ---------------------------------------------------------------------------
# Login History
# ---------------------------------------------------------------------------
class LoginHistory(models.Model):
    """Login attempt log. Replaces legacy [login_history_student], [login_history_teacher]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='login_history')

    user_id = models.UUIDField(null=True, blank=True)
    user_type = models.CharField(max_length=10, null=True, blank=True)
    username_attempted = models.CharField(max_length=200)

    class LoginResult(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        BLOCKED = 'BLOCKED', 'Blocked'
        MFA_REQUIRED = 'MFA_REQUIRED', 'MFA Required'
        MFA_FAILED = 'MFA_FAILED', 'MFA Failed'
        ACCOUNT_LOCKED = 'ACCOUNT_LOCKED', 'Account Locked'
        INACTIVE = 'INACTIVE', 'Inactive Account'

    result = models.CharField(max_length=20, choices=LoginResult.choices)
    failure_reason = models.CharField(max_length=500, null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device = models.ForeignKey(UserDevice, on_delete=models.SET_NULL, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    geo_city = models.CharField(max_length=100, null=True, blank=True)
    geo_country = models.CharField(max_length=100, null=True, blank=True)

    session_id = models.UUIDField(null=True, blank=True)

    attempted_at = models.DateTimeField(default=timezone.now)

    # Anomaly
    is_suspicious = models.BooleanField(default=False)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    risk_factors = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'login_history'
        ordering = ['-attempted_at']
        verbose_name_plural = 'Login history'
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'attempted_at'], name='idx_login_user_time'),
            models.Index(fields=['tenant', 'ip_address'], name='idx_login_ip'),
            models.Index(fields=['tenant', 'result'], name='idx_login_result'),
        ]


# ---------------------------------------------------------------------------
# User Activity Log
# ---------------------------------------------------------------------------
class UserActivity(models.Model):
    """Granular user activity tracking for analytics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='user_activities')

    session = models.ForeignKey(UserSession, on_delete=models.SET_NULL, null=True, blank=True)
    user_id = models.UUIDField()
    user_type = models.CharField(max_length=10)

    class ActivityType(models.TextChoices):
        PAGE_VIEW = 'PAGE_VIEW', 'Page View'
        CLASS_JOIN = 'CLASS_JOIN', 'Class Join'
        CLASS_LEAVE = 'CLASS_LEAVE', 'Class Leave'
        TEST_START = 'TEST_START', 'Test Start'
        TEST_SUBMIT = 'TEST_SUBMIT', 'Test Submit'
        MATERIAL_VIEW = 'MATERIAL_VIEW', 'Material View'
        MATERIAL_DOWNLOAD = 'MATERIAL_DOWNLOAD', 'Material Download'
        PROFILE_UPDATE = 'PROFILE_UPDATE', 'Profile Update'
        SETTINGS_CHANGE = 'SETTINGS_CHANGE', 'Settings Change'
        MESSAGE_SENT = 'MESSAGE_SENT', 'Message Sent'
        TICKET_CREATED = 'TICKET_CREATED', 'Ticket Created'
        CUSTOM = 'CUSTOM', 'Custom'

    activity_type = models.CharField(max_length=25, choices=ActivityType.choices)
    activity_description = models.CharField(max_length=500, null=True, blank=True)

    # Resource reference
    resource_type = models.CharField(max_length=50, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=500, null=True, blank=True)

    # Context
    page_url = models.URLField(max_length=1000, null=True, blank=True)
    referrer_url = models.URLField(max_length=1000, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    activity_data = models.JSONField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'user_activities'
        ordering = ['-occurred_at']
        verbose_name_plural = 'User activities'
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'occurred_at'], name='idx_activity_user_time'),
            models.Index(fields=['tenant', 'activity_type'], name='idx_activity_type'),
        ]
