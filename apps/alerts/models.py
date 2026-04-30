"""
LMS Enterprise - Alerting & Monitoring Models
Rule-based alerts for session tracking, attendance, live classes, reporting, etc.
"""
import uuid
from django.db import models
from django.utils import timezone


class AlertRule(models.Model):
    """Configurable alert rule that triggers notifications when conditions are met."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='alert_rules')

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')

    class Category(models.TextChoices):
        SESSION_TRACKING = 'SESSION_TRACKING', 'Session & Activity Tracking'
        ATTENDANCE = 'ATTENDANCE', 'Attendance'
        LIVE_CLASSES = 'LIVE_CLASSES', 'Live Classes'
        ASSESSMENTS = 'ASSESSMENTS', 'Assessments & Tests'
        SECURITY = 'SECURITY', 'Security'
        SYSTEM = 'SYSTEM', 'System Health'

    category = models.CharField(max_length=20, choices=Category.choices)

    class RuleType(models.TextChoices):
        FAILED_LOGIN_STREAK = 'FAILED_LOGIN_STREAK', 'Failed Login Streak (X consecutive failures)'
        SUSPICIOUS_LOGIN = 'SUSPICIOUS_LOGIN', 'Suspicious Login Detected'
        CONCURRENT_SESSIONS = 'CONCURRENT_SESSIONS', 'Too Many Concurrent Sessions'
        INACTIVE_SESSION = 'INACTIVE_SESSION', 'Session Inactive Too Long'
        LOW_ATTENDANCE = 'LOW_ATTENDANCE', 'Attendance Below Threshold (%)'
        ABSENT_STREAK = 'ABSENT_STREAK', 'Absent Streak (X consecutive days)'
        LOW_CLASS_ATTENDANCE = 'LOW_CLASS_ATTENDANCE', 'Live Class Attendance Below Threshold'
        CLASS_NOT_STARTED = 'CLASS_NOT_STARTED', 'Scheduled Class Not Started'
        LOW_TEST_SCORE = 'LOW_TEST_SCORE', 'Average Test Score Below Threshold'
        TEST_NOT_SUBMITTED = 'TEST_NOT_SUBMITTED', 'Test Not Submitted by Deadline'
        BRUTE_FORCE = 'BRUTE_FORCE', 'Brute Force Attack Detected'
        NEW_DEVICE_LOGIN = 'NEW_DEVICE_LOGIN', 'Login from New/Unknown Device'
        HIGH_ERROR_RATE = 'HIGH_ERROR_RATE', 'High Error Rate Detected'
        DB_SLOW_QUERIES = 'DB_SLOW_QUERIES', 'Slow Database Queries'
        # ── Real-time student/teacher activity rules ──
        STUDENT_NO_LOGIN_7D = 'STUDENT_NO_LOGIN_7D', 'Student No Login for N Days'
        STUDENT_MULTIPLE_LATES = 'STUDENT_MULTIPLE_LATES', 'Student Late N Times in Window'
        TEACHER_NO_SHOW = 'TEACHER_NO_SHOW', 'Teacher Absent Without Leave'
        TEACHER_LATE_TO_CLASS = 'TEACHER_LATE_TO_CLASS', 'Teacher Late to Scheduled Class'
        PARENT_PORTAL_INACTIVE = 'PARENT_PORTAL_INACTIVE', 'Parent Portal Never Used'
        STUDENT_LOW_ATTEND_PCT = 'STUDENT_LOW_ATTEND_PCT', 'Student Attendance % < Threshold'
        TEACHER_LOW_ATTEND_PCT = 'TEACHER_LOW_ATTEND_PCT', 'Teacher Attendance % < Threshold'
        BATCH_LOW_AVG_ATTEND = 'BATCH_LOW_AVG_ATTEND', 'Batch Avg Attendance % < Threshold'

    rule_type = models.CharField(max_length=30, choices=RuleType.choices)

    threshold = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                    help_text='Threshold value (e.g., 3 for failures, 75 for percentage)')
    time_window_minutes = models.IntegerField(default=60, help_text='Time window in minutes to evaluate the rule')

    class Severity(models.TextChoices):
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        CRITICAL = 'CRITICAL', 'Critical'

    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)

    class NotifyMethod(models.TextChoices):
        ADMIN_PANEL = 'ADMIN_PANEL', 'Admin Panel Notification'
        EMAIL = 'EMAIL', 'Email'
        BOTH = 'BOTH', 'Admin Panel + Email'

    notify_method = models.CharField(max_length=12, choices=NotifyMethod.choices, default=NotifyMethod.ADMIN_PANEL)
    notify_emails = models.TextField(blank=True, default='', help_text='Comma-separated email addresses for notifications')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'alert_rules'
        ordering = ['-created_at']
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.name}"


class AlertLog(models.Model):
    """Log of triggered alerts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='alert_logs')
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='logs')

    message = models.TextField()
    details = models.JSONField(null=True, blank=True)

    class Severity(models.TextChoices):
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        CRITICAL = 'CRITICAL', 'Critical'

    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)

    triggered_at = models.DateTimeField(default=timezone.now)

    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=200, blank=True, default='')
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    is_email_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'alert_logs'
        ordering = ['-triggered_at']
        verbose_name = 'Alert Log'
        verbose_name_plural = 'Alert Logs'

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.rule.name} — {self.triggered_at.strftime('%Y-%m-%d %H:%M')}"
