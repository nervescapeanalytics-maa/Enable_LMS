"""
LMS Enterprise - Attendance Models
Normalized replacement for legacy [users_Attendance] / [teacher_Attendance]
which stored D1-D31 columns. Now one row per attendance event.
"""
import uuid
from django.db import models
from django.utils import timezone


class Attendance(models.Model):
    """Per-day attendance record for students and teachers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='attendance_records')

    # Who
    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'

    user_type = models.CharField(max_length=10, choices=UserType.choices)
    user_id = models.UUIDField(db_index=True)
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True)

    # When
    attendance_date = models.DateField()
    month = models.IntegerField()
    year = models.IntegerField()
    academic_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL, null=True, blank=True
    )

    # What
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        HALF_DAY = 'HALF_DAY', 'Half Day'
        LEAVE = 'LEAVE', 'On Leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        EXCUSED = 'EXCUSED', 'Excused'

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABSENT)

    # Time
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)

    # Source
    class Source(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual Entry'
        LIVE_CLASS = 'LIVE_CLASS', 'Live Class Auto'
        BIOMETRIC = 'BIOMETRIC', 'Biometric'
        QR_CODE = 'QR_CODE', 'QR Code'
        GEOFENCE = 'GEOFENCE', 'Geofence'
        SYSTEM = 'SYSTEM', 'System Generated'

    source = models.CharField(max_length=15, choices=Source.choices, default=Source.MANUAL)
    source_reference_id = models.UUIDField(null=True, blank=True, help_text='Link to ScheduledClass or session')

    # For live class auto attendance
    live_class = models.ForeignKey(
        'classes.ScheduledClass', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_records'
    )
    watch_duration_seconds = models.IntegerField(null=True, blank=True)
    watch_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Audit
    marked_by = models.UUIDField(null=True, blank=True)
    marked_by_type = models.CharField(max_length=10, null=True, blank=True)
    marked_at = models.DateTimeField(default=timezone.now)

    # Corrections
    is_corrected = models.BooleanField(default=False)
    original_status = models.CharField(max_length=10, null=True, blank=True)
    corrected_by = models.UUIDField(null=True, blank=True)
    corrected_at = models.DateTimeField(null=True, blank=True)
    correction_reason = models.TextField(null=True, blank=True)

    remarks = models.CharField(max_length=500, null=True, blank=True)

    # Extensions
    attendance_meta = models.JSONField(null=True, blank=True)
    ext_att_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_att_2 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'attendance'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user_type', 'user_id', 'attendance_date'],
                name='uq_attendance_per_user_per_day'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'user_type', 'user_id', 'attendance_date'], name='idx_att_user_date'),
            models.Index(fields=['tenant', 'attendance_date', 'status'], name='idx_att_date_status'),
            models.Index(fields=['tenant', 'batch', 'attendance_date'], name='idx_att_batch_date'),
        ]


class AttendanceCorrectionRequest(models.Model):
    """Correction request for attendance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='correction_requests')
    requested_by = models.UUIDField()
    requested_by_type = models.CharField(max_length=10)
    requested_status = models.CharField(max_length=10, choices=Attendance.Status.choices)
    reason = models.TextField()
    supporting_document = models.URLField(max_length=500, null=True, blank=True)

    class RequestStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    status = models.CharField(max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    reviewed_by = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'attendance_correction_requests'


class AttendanceSummary(models.Model):
    """Monthly attendance summary (denormalized)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    user_type = models.CharField(max_length=10)
    user_id = models.UUIDField()
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True)
    academic_session = models.ForeignKey('academics.AcademicSession', on_delete=models.SET_NULL, null=True, blank=True)
    month = models.IntegerField()
    year = models.IntegerField()

    total_working_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    late_days = models.IntegerField(default=0)
    half_days = models.IntegerField(default=0)
    leave_days = models.IntegerField(default=0)
    holiday_days = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    last_calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_summaries'
        verbose_name_plural = 'Attendance summaries'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user_type', 'user_id', 'month', 'year'],
                name='uq_attendance_summary_monthly'
            ),
        ]
