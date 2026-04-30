"""
LMS Enterprise - Scheduling Models
RecurringRule, Enrollment, BlackoutDate, ClassAttendance (per-session)

These models implement the EduAssist system prompt's data model:
- recurring_rules: Master template for repeating classes
- enrollments: Student enrollment to recurring rules or ad-hoc sessions
- blackout_dates: Holidays/closures that skip recurring classes
- class_attendance: Per-session attendance marked by teacher (Present/Absent/Late)
"""
import uuid
from django.db import models
from django.utils import timezone as dj_timezone


# ---------------------------------------------------------------------------
# Recurring Rule — Master template for repeating classes
# ---------------------------------------------------------------------------
class RecurringRule(models.Model):
    """
    The master schedule template created once by the admin.
    Every night the system reads active rules and auto-creates
    ScheduledClass instances (class_instances) for the next 30 days.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='recurring_rules'
    )

    # ── Identity ──
    title = models.CharField(max_length=500, help_text="Name of the class schedule")
    description = models.TextField(null=True, blank=True)

    # ── Academic link ──
    subject = models.ForeignKey(
        'academics.Subject', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recurring_rules'
    )
    teacher = models.ForeignKey(
        'accounts.Teacher', on_delete=models.CASCADE,
        related_name='recurring_rules'
    )
    batch = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recurring_rules'
    )

    # ── Schedule (RRULE-based) ──
    rrule = models.TextField(
        help_text="iCalendar RRULE string, e.g. FREQ=WEEKLY;BYDAY=MO,WE,FR"
    )
    start_time = models.TimeField(help_text="Class start time each day (local)")
    duration_mins = models.IntegerField(default=60, help_text="Duration of each session in minutes")
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')

    # ── Date range ──
    start_date = models.DateField(help_text="When the schedule begins")
    end_date = models.DateField(
        null=True, blank=True,
        help_text="When the schedule ends (blank = runs forever)"
    )

    # ── Lifecycle ──
    class RuleStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        PAUSED = 'PAUSED', 'Paused'
        SUPERSEDED = 'SUPERSEDED', 'Superseded'
        ENDED = 'ENDED', 'Ended'

    status = models.CharField(
        max_length=15, choices=RuleStatus.choices,
        default=RuleStatus.DRAFT
    )

    # ── Auto-generation tracking ──
    generated_until = models.DateField(
        null=True, blank=True,
        help_text="How far ahead sessions have been created (internal)"
    )

    # ── Supersede / Duplicate chain ──
    parent_rule = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='child_rules',
        help_text="If duplicated from another rule, the original's ID"
    )
    superseded_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supersedes',
        help_text="ID of the new rule that replaced this one"
    )
    effective_from = models.DateField(
        null=True, blank=True,
        help_text="Date from which the new rule takes effect (must be >= tomorrow)"
    )

    # ── YouTube config ──
    youtube_channel = models.ForeignKey(
        'classes.YouTubeChannel', on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Default YouTube channel for all sessions generated from this rule"
    )

    # ── Audit ──
    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Extensions ──
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'recurring_rules'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_rr_status'),
            models.Index(fields=['tenant', 'teacher'], name='idx_rr_teacher'),
            models.Index(fields=['tenant', 'subject'], name='idx_rr_subject'),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# Enrollment — student ↔ recurring rule or ad-hoc session
# ---------------------------------------------------------------------------
class Enrollment(models.Model):
    """
    Which students are in which class.
    For recurring: linked to recurring_rule (student sees all future sessions).
    For ad-hoc: linked to a specific ScheduledClass instance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='enrollments'
    )

    student = models.ForeignKey(
        'accounts.Student', on_delete=models.CASCADE,
        related_name='enrollments'
    )

    # Link to recurring schedule OR a specific class instance
    recurring_rule = models.ForeignKey(
        RecurringRule, on_delete=models.CASCADE,
        null=True, blank=True, related_name='enrollments',
        help_text="For recurring classes"
    )
    class_instance = models.ForeignKey(
        'classes.ScheduledClass', on_delete=models.CASCADE,
        null=True, blank=True, related_name='enrollments',
        help_text="For ad-hoc / one-off classes"
    )

    # ── How enrolled ──
    class EnrollmentMethod(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual'
        CLASS_GROUP = 'CLASS_GROUP', 'Class Group'
        CSV_UPLOAD = 'CSV_UPLOAD', 'CSV Upload'
        AUTO_MIGRATION = 'AUTO_MIGRATION', 'Auto Migration (Schedule Update)'

    method = models.CharField(
        max_length=20, choices=EnrollmentMethod.choices,
        default=EnrollmentMethod.MANUAL
    )

    enrolled_by = models.UUIDField(null=True, blank=True, help_text="Admin who enrolled")
    class_group = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="If enrolled via class group"
    )

    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(default=dj_timezone.now)
    unenrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'recurring_rule'],
                condition=models.Q(recurring_rule__isnull=False, is_active=True),
                name='uq_enrollment_recurring'
            ),
            models.UniqueConstraint(
                fields=['student', 'class_instance'],
                condition=models.Q(class_instance__isnull=False, is_active=True),
                name='uq_enrollment_adhoc'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'student'], name='idx_enroll_student'),
            models.Index(fields=['tenant', 'recurring_rule'], name='idx_enroll_rule'),
            models.Index(fields=['tenant', 'class_instance'], name='idx_enroll_class'),
        ]

    def __str__(self):
        target = self.recurring_rule or self.class_instance
        return f"{self.student} → {target}"


# ---------------------------------------------------------------------------
# Blackout Date — Holidays / school closure days
# ---------------------------------------------------------------------------
class BlackoutDate(models.Model):
    """
    Holidays and school closure days.
    When a recurring class falls on one of these dates, the system
    automatically skips it — no session is created for that day.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='blackout_dates'
    )

    date = models.DateField()
    reason = models.CharField(max_length=500, help_text="e.g. 'Diwali Holiday'")

    # Optional: apply to specific batches only, blank = all
    applies_to_batches = models.JSONField(
        default=list, blank=True,
        help_text="List of batch UUIDs; empty = applies to all"
    )

    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = 'blackout_dates'
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'date'],
                name='uq_blackout_date_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'date'], name='idx_blackout_date'),
        ]

    def __str__(self):
        return f"{self.date} — {self.reason}"


# ---------------------------------------------------------------------------
# Class Attendance — Per-session teacher-marked attendance
# ---------------------------------------------------------------------------
class ClassAttendance(models.Model):
    """
    Teacher-marked attendance per class session.
    Separate from the daily Attendance model and from automatic watch time.
    Teacher marks each student as Present, Absent, or Late.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='class_attendance_records'
    )

    class_instance = models.ForeignKey(
        'classes.ScheduledClass', on_delete=models.CASCADE,
        related_name='class_attendance'
    )
    student = models.ForeignKey(
        'accounts.Student', on_delete=models.CASCADE,
        related_name='class_attendance'
    )

    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'

    status = models.CharField(
        max_length=10, choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT
    )

    marked_by = models.ForeignKey(
        'accounts.Teacher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='marked_class_attendance'
    )
    marked_at = models.DateTimeField(default=dj_timezone.now)
    remarks = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'class_attendance'
        constraints = [
            models.UniqueConstraint(
                fields=['class_instance', 'student'],
                name='uq_class_attendance_per_student'
            ),
        ]
        indexes = [
            models.Index(
                fields=['tenant', 'class_instance', 'status'],
                name='idx_class_att_status'
            ),
        ]

    def __str__(self):
        return f"{self.student} — {self.class_instance} — {self.status}"
