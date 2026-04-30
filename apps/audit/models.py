"""
LMS Enterprise - Audit & Compliance Models
Full audit trail, data retention policies, backup management.
"""
import uuid
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Comprehensive audit log for all system events."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='audit_logs', null=True, blank=True
    )

    # Who
    user_id = models.UUIDField(null=True, blank=True)
    user_type = models.CharField(max_length=20, null=True, blank=True)
    username = models.CharField(max_length=200, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.UUIDField(null=True, blank=True)

    # What
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Login Failed'
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Password Change'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
        PERMISSION_CHANGE = 'PERMISSION_CHANGE', 'Permission Change'
        EXPORT = 'EXPORT', 'Data Export'
        IMPORT = 'IMPORT', 'Data Import'
        SETTINGS_CHANGE = 'SETTINGS_CHANGE', 'Settings Change'
        SYSTEM = 'SYSTEM', 'System Event'
        API_CALL = 'API_CALL', 'API Call'

    action = models.CharField(max_length=20, choices=ActionType.choices)
    action_description = models.CharField(max_length=1000, null=True, blank=True)

    # Where
    resource_type = models.CharField(max_length=100, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=500, null=True, blank=True)

    # API context
    http_method = models.CharField(max_length=10, null=True, blank=True)
    request_path = models.CharField(max_length=1000, null=True, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    response_status = models.IntegerField(null=True, blank=True)

    # Change tracking
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)

    # Severity
    class Severity(models.TextChoices):
        DEBUG = 'DEBUG', 'Debug'
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'
        CRITICAL = 'CRITICAL', 'Critical'

    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    is_security_event = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    audit_meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'action', 'created_at'], name='idx_audit_action_time'),
            models.Index(fields=['tenant', 'user_id'], name='idx_audit_user'),
            models.Index(fields=['tenant', 'resource_type', 'resource_id'], name='idx_audit_resource'),
            models.Index(fields=['tenant', 'is_security_event', 'created_at'], name='idx_audit_security'),
        ]

    def __str__(self):
        return f"[{self.action}] {self.resource_type} by {self.username}"


class AuditPurgePolicy(models.Model):
    """Data retention / purge policies per resource type."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True)

    resource_type = models.CharField(max_length=100)
    retention_days = models.IntegerField(default=365)
    action_on_expiry = models.CharField(
        max_length=20, default='ARCHIVE',
        choices=[('DELETE', 'Delete'), ('ARCHIVE', 'Archive'), ('ANONYMIZE', 'Anonymize')]
    )
    archive_location = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    last_purge_at = models.DateTimeField(null=True, blank=True)
    next_purge_at = models.DateTimeField(null=True, blank=True)
    records_purged = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'audit_purge_policies'
        verbose_name_plural = 'Audit purge policies'


class BackupPolicy(models.Model):
    """Database backup policies."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    policy_name = models.CharField(max_length=200, unique=True)

    class BackupType(models.TextChoices):
        FULL = 'FULL', 'Full Backup'
        INCREMENTAL = 'INCREMENTAL', 'Incremental'
        WAL_ARCHIVE = 'WAL_ARCHIVE', 'WAL Archive'
        LOGICAL = 'LOGICAL', 'Logical (pg_dump)'

    backup_type = models.CharField(max_length=15, choices=BackupType.choices, default=BackupType.FULL)

    schedule_cron = models.CharField(max_length=100, default='0 2 * * *')
    retention_days = models.IntegerField(default=30)
    hot_backup_path = models.CharField(max_length=500, default='/backup/hot')
    cold_backup_path = models.CharField(max_length=500, default='/backup/cold')
    compression_enabled = models.BooleanField(default=True)
    encryption_enabled = models.BooleanField(default=False)
    encryption_key_id = models.CharField(max_length=200, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'backup_policies'
        verbose_name_plural = 'Backup policies'


class BackupHistory(models.Model):
    """Backup execution history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    policy = models.ForeignKey(BackupPolicy, on_delete=models.CASCADE, related_name='history')

    class BackupStatus(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        PARTIAL = 'PARTIAL', 'Partial'

    status = models.CharField(max_length=10, choices=BackupStatus.choices, default=BackupStatus.RUNNING)

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    backup_size_bytes = models.BigIntegerField(null=True, blank=True)
    backup_path = models.CharField(max_length=1000, null=True, blank=True)
    checksum = models.CharField(max_length=128, null=True, blank=True)

    error_message = models.TextField(null=True, blank=True)
    tables_backed_up = models.IntegerField(null=True, blank=True)
    rows_backed_up = models.BigIntegerField(null=True, blank=True)

    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'backup_history'
        ordering = ['-started_at']
        verbose_name_plural = 'Backup history'
