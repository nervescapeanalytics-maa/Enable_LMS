"""
Attendance Service Layer
Business logic for attendance marking, validation, and reporting.
Keeps views and models thin.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Avg
from django.utils import timezone


class AttendanceService:
    """Service for attendance operations."""

    def __init__(self, repository=None):
        self.repository = repository or AttendanceRepository()

    def mark_student_attendance(self, tenant_id, user_id, attendance_date,
                                status, batch_id=None, marked_by=None,
                                source='MANUAL', **kwargs):
        """Mark attendance for a student."""
        from attendance.models import Attendance

        defaults = {
            'status': status,
            'batch_id': batch_id,
            'month': attendance_date.month,
            'year': attendance_date.year,
            'source': source,
            'marked_by': marked_by,
            'marked_at': timezone.now(),
        }
        defaults.update(kwargs)

        obj, created = Attendance.objects.update_or_create(
            tenant_id=tenant_id,
            user_type='STUDENT',
            user_id=user_id,
            attendance_date=attendance_date,
            defaults=defaults,
        )
        return obj, created

    def mark_teacher_attendance(self, tenant_id, user_id, attendance_date,
                                status, marked_by=None, source='MANUAL',
                                **kwargs):
        """Mark attendance for a teacher (including self-attendance)."""
        from attendance.models import Attendance

        defaults = {
            'status': status,
            'month': attendance_date.month,
            'year': attendance_date.year,
            'source': source,
            'marked_by': marked_by or user_id,
            'marked_at': timezone.now(),
        }
        defaults.update(kwargs)

        obj, created = Attendance.objects.update_or_create(
            tenant_id=tenant_id,
            user_type='TEACHER',
            user_id=user_id,
            attendance_date=attendance_date,
            defaults=defaults,
        )
        return obj, created

    def auto_mark_from_live_class(self, scheduled_class, watch_times):
        """
        Auto-mark attendance from live class watch data.
        watch_times: list of ClassWatchTime objects
        """
        from attendance.models import Attendance
        from system_config.models import AttendanceRule

        rule = AttendanceRule.objects.filter(
            tenant=scheduled_class.tenant,
            applies_to__in=['STUDENT', 'ALL'],
            auto_mark_from_live_class=True,
            is_active=True,
        ).first()

        if not rule:
            return []

        min_pct = rule.min_watch_percentage
        results = []

        for wt in watch_times:
            pct = Decimal(str(wt.watch_percentage or 0))
            if pct >= min_pct:
                status = 'PRESENT'
            elif pct >= (min_pct / 2):
                status = 'HALF_DAY'
            elif pct > 0:
                status = 'LATE'
            else:
                status = 'ABSENT'

            obj, created = Attendance.objects.update_or_create(
                tenant=scheduled_class.tenant,
                user_type='STUDENT',
                user_id=wt.user_id,
                attendance_date=scheduled_class.scheduled_date,
                defaults={
                    'status': status,
                    'batch_id': getattr(scheduled_class, 'batch_id', None),
                    'month': scheduled_class.scheduled_date.month,
                    'year': scheduled_class.scheduled_date.year,
                    'source': 'LIVE_CLASS',
                    'live_class': scheduled_class,
                    'watch_duration_seconds': wt.total_watch_seconds,
                    'watch_percentage': wt.watch_percentage,
                    'marked_at': timezone.now(),
                },
            )
            results.append((obj, created))

        return results

    def get_attendance_summary(self, tenant_id, user_type, user_id, month, year):
        """Calculate attendance summary for a user for a given month."""
        from attendance.models import Attendance, AttendanceSummary

        records = Attendance.objects.filter(
            tenant_id=tenant_id,
            user_type=user_type,
            user_id=user_id,
            month=month,
            year=year,
        )

        total = records.count()
        present = records.filter(status='PRESENT').count()
        absent = records.filter(status='ABSENT').count()
        late = records.filter(status='LATE').count()
        half = records.filter(status='HALF_DAY').count()
        leave = records.filter(status='LEAVE').count()
        holiday = records.filter(status='HOLIDAY').count()

        working_days = total - holiday
        pct = (Decimal(present + late) / Decimal(working_days) * 100) if working_days > 0 else Decimal('0.00')

        summary, _ = AttendanceSummary.objects.update_or_create(
            tenant_id=tenant_id,
            user_type=user_type,
            user_id=user_id,
            month=month,
            year=year,
            defaults={
                'total_working_days': working_days,
                'present_days': present,
                'absent_days': absent,
                'late_days': late,
                'half_days': half,
                'leave_days': leave,
                'holiday_days': holiday,
                'attendance_percentage': pct,
            }
        )
        return summary

    def get_batch_attendance_report(self, tenant_id, batch_id, attendance_date):
        """Get attendance report for an entire batch on a given date."""
        from attendance.models import Attendance
        from academics.models import Users

        students = Users.objects.filter(
            batch_id=batch_id,
            is_active=True,
        ).values_list('student_id', flat=True)

        records = Attendance.objects.filter(
            tenant_id=tenant_id,
            user_type='STUDENT',
            user_id__in=students,
            attendance_date=attendance_date,
        )

        data = {
            'total_students': len(students),
            'marked': records.count(),
            'present': records.filter(status='PRESENT').count(),
            'absent': records.filter(status='ABSENT').count(),
            'late': records.filter(status='LATE').count(),
            'half_day': records.filter(status='HALF_DAY').count(),
            'leave': records.filter(status='LEAVE').count(),
            'not_marked': len(students) - records.count(),
        }
        return data


class AttendanceRepository:
    """Data access layer for Attendance."""

    def get_by_user_date(self, tenant_id, user_type, user_id, attendance_date):
        from attendance.models import Attendance
        return Attendance.objects.filter(
            tenant_id=tenant_id,
            user_type=user_type,
            user_id=user_id,
            attendance_date=attendance_date,
        ).first()

    def get_user_monthly(self, tenant_id, user_type, user_id, month, year):
        from attendance.models import Attendance
        return Attendance.objects.filter(
            tenant_id=tenant_id,
            user_type=user_type,
            user_id=user_id,
            month=month,
            year=year,
        ).order_by('attendance_date')

    def filter_active_rules(self, tenant_id, applies_to=None):
        from system_config.models import AttendanceRule
        qs = AttendanceRule.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        )
        if applies_to:
            qs = qs.filter(applies_to__in=[applies_to, 'ALL'])
        return qs
