"""
Scheduling - Business Logic Services

Core services for:
1. Generating class sessions from recurring rules
2. Enrolling students (manual / class group / CSV)
3. Duplicating & superseding recurring rules
4. Handling blackout dates
5. Marking per-session attendance
"""
import logging
from datetime import date, datetime, timedelta, time as dt_time
from dateutil.rrule import rrulestr
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('lms')


# ---------------------------------------------------------------------------
# 1. Session Generation from Recurring Rules
# ---------------------------------------------------------------------------
def generate_sessions_for_rule(rule, horizon_days=30):
    """
    Read a RecurringRule and create ScheduledClass instances for the next
    `horizon_days` days. Skips blackout dates and already-generated dates.
    Called nightly by the Celery beat task.
    """
    from classes.models import ScheduledClass
    from scheduling.models import BlackoutDate

    today = date.today()
    start = rule.generated_until + timedelta(days=1) if rule.generated_until else rule.start_date
    if start < today:
        start = today
    end = today + timedelta(days=horizon_days)
    if rule.end_date and rule.end_date < end:
        end = rule.end_date

    if start > end:
        return 0

    # Get blackout dates for this tenant
    blackout_dates = set(
        BlackoutDate.objects.filter(
            tenant=rule.tenant,
            date__gte=start,
            date__lte=end,
        ).values_list('date', flat=True)
    )

    # Parse rrule
    try:
        rr = rrulestr(rule.rrule, dtstart=datetime.combine(start, dt_time.min))
    except Exception as e:
        logger.error(f"Invalid RRULE for rule {rule.id}: {e}")
        return 0

    # Get dates from rrule
    occurrences = rr.between(
        datetime.combine(start, dt_time.min),
        datetime.combine(end, dt_time(23, 59, 59)),
        inc=True,
    )

    created_count = 0
    for occ in occurrences:
        occ_date = occ.date()

        # Skip blackout dates
        if occ_date in blackout_dates:
            logger.info(f"Skipping {rule.title} on {occ_date} (blackout)")
            continue

        # Check if already exists
        exists = ScheduledClass.objects.filter(
            tenant=rule.tenant,
            class_meta__recurring_rule_id=str(rule.id),
            scheduled_date=occ_date,
        ).exists()
        if exists:
            continue

        # Build class code
        class_code = f"RC-{rule.id.hex[:8]}-{occ_date.strftime('%Y%m%d')}"

        # Calculate end time
        start_dt = datetime.combine(occ_date, rule.start_time)
        end_dt = start_dt + timedelta(minutes=rule.duration_mins)

        ScheduledClass.objects.create(
            tenant=rule.tenant,
            class_code=class_code,
            title=rule.title,
            description=rule.description or '',
            scheduled_date=occ_date,
            start_time=rule.start_time,
            end_time=end_dt.time(),
            duration_minutes=rule.duration_mins,
            class_timezone=rule.timezone,
            subject=rule.subject.subject_type if rule.subject else None,
            teacher=rule.teacher,
            batch=rule.batch,
            youtube_channel=rule.youtube_channel,
            status=ScheduledClass.ClassStatus.SCHEDULED,
            class_meta={
                'recurring_rule_id': str(rule.id),
                'session_type': 'recurring',
            },
        )
        created_count += 1

    # Update generated_until
    rule.generated_until = end
    rule.save(update_fields=['generated_until', 'updated_at'])
    logger.info(f"Generated {created_count} sessions for rule '{rule.title}' until {end}")
    return created_count


def generate_all_sessions(horizon_days=30):
    """Generate sessions for ALL active recurring rules."""
    from scheduling.models import RecurringRule
    total = 0
    rules = RecurringRule.objects.filter(status=RecurringRule.RuleStatus.ACTIVE)
    for rule in rules:
        total += generate_sessions_for_rule(rule, horizon_days)
    return total


# ---------------------------------------------------------------------------
# 2. Enrollment Services
# ---------------------------------------------------------------------------
def enroll_students_manual(tenant, rule_or_instance, student_ids, enrolled_by, is_recurring=True):
    """Enroll specific students by ID."""
    from scheduling.models import Enrollment
    from accounts.models import Student

    created = 0
    for sid in student_ids:
        try:
            student = Student.objects.get(id=sid, tenant=tenant)
        except Student.DoesNotExist:
            continue

        kwargs = {
            'tenant': tenant,
            'student': student,
            'method': Enrollment.EnrollmentMethod.MANUAL,
            'enrolled_by': enrolled_by,
        }
        if is_recurring:
            kwargs['recurring_rule'] = rule_or_instance
            if Enrollment.objects.filter(
                student=student, recurring_rule=rule_or_instance, is_active=True
            ).exists():
                continue
        else:
            kwargs['class_instance'] = rule_or_instance
            if Enrollment.objects.filter(
                student=student, class_instance=rule_or_instance, is_active=True
            ).exists():
                continue

        Enrollment.objects.create(**kwargs)
        created += 1

    return created


def enroll_by_class_group(tenant, rule_or_instance, batch_id, enrolled_by, is_recurring=True):
    """Enroll all students in a batch/class group."""
    from academics.models import Users

    batch_students = Users.objects.filter(
        batch_id=batch_id, is_active=True
    ).values_list('student_id', flat=True)

    return enroll_students_manual(
        tenant, rule_or_instance, list(batch_students), enrolled_by, is_recurring
    )


def enroll_by_csv_emails(tenant, rule_or_instance, emails, enrolled_by, is_recurring=True):
    """Enroll students by email addresses (CSV upload)."""
    from academics.models import Users

    student_ids = list(
        Users.objects.filter(
            tenant=tenant, email__in=emails, is_active=True
        ).values_list('student_id', flat=True)
    )
    return enroll_students_manual(
        tenant, rule_or_instance, student_ids, enrolled_by, is_recurring
    )


# ---------------------------------------------------------------------------
# 3. Duplicate & Supersede Rule
# ---------------------------------------------------------------------------
@transaction.atomic
def duplicate_and_supersede(original_rule, effective_from, changes=None):
    """
    Duplicate a recurring rule, apply changes, and supersede the original.
    - effective_from must be >= tomorrow
    - All enrollments are auto-migrated
    - Future sessions after effective_from from old rule are cancelled
    """
    from scheduling.models import RecurringRule, Enrollment
    from classes.models import ScheduledClass

    if effective_from <= date.today():
        raise ValueError("Effective From must be at least tomorrow.")

    changes = changes or {}

    # Create new rule (copy of original)
    new_rule = RecurringRule(
        tenant=original_rule.tenant,
        title=changes.get('title', original_rule.title),
        description=changes.get('description', original_rule.description),
        subject=original_rule.subject,
        teacher=original_rule.teacher,
        batch=original_rule.batch,
        rrule=changes.get('rrule', original_rule.rrule),
        start_time=changes.get('start_time', original_rule.start_time),
        duration_mins=changes.get('duration_mins', original_rule.duration_mins),
        timezone=original_rule.timezone,
        start_date=effective_from,
        end_date=original_rule.end_date,
        status=RecurringRule.RuleStatus.ACTIVE,
        parent_rule=original_rule,
        effective_from=effective_from,
        youtube_channel=original_rule.youtube_channel,
        created_by=original_rule.created_by,
    )

    # Apply FK changes
    if 'teacher_id' in changes:
        from accounts.models import Teacher
        new_rule.teacher = Teacher.objects.get(id=changes['teacher_id'])
    if 'subject_id' in changes:
        from academics.models import Subject
        new_rule.subject = Subject.objects.get(id=changes['subject_id'])

    new_rule.save()

    # Supersede old rule
    original_rule.status = RecurringRule.RuleStatus.SUPERSEDED
    original_rule.superseded_by = new_rule
    original_rule.end_date = effective_from - timedelta(days=1)
    original_rule.save(update_fields=['status', 'superseded_by', 'end_date', 'updated_at'])

    # Auto-migrate enrollments
    active_enrollments = Enrollment.objects.filter(
        recurring_rule=original_rule, is_active=True
    )
    for enrollment in active_enrollments:
        Enrollment.objects.create(
            tenant=enrollment.tenant,
            student=enrollment.student,
            recurring_rule=new_rule,
            method=Enrollment.EnrollmentMethod.AUTO_MIGRATION,
            enrolled_by=enrollment.enrolled_by,
        )

    # Cancel future sessions from old rule after effective_from
    future_sessions = ScheduledClass.objects.filter(
        tenant=original_rule.tenant,
        class_meta__recurring_rule_id=str(original_rule.id),
        scheduled_date__gte=effective_from,
        status__in=[
            ScheduledClass.ClassStatus.SCHEDULED,
            ScheduledClass.ClassStatus.DRAFT,
        ],
    )
    cancelled_count = future_sessions.update(
        status=ScheduledClass.ClassStatus.CANCELLED,
        cancellation_reason=f"Schedule superseded by new rule (effective {effective_from})",
        cancelled_at=timezone.now(),
    )

    logger.info(
        f"Rule {original_rule.id} superseded by {new_rule.id}. "
        f"Migrated {active_enrollments.count()} enrollments, "
        f"cancelled {cancelled_count} future sessions."
    )

    return new_rule


# ---------------------------------------------------------------------------
# 4. Bulk Attendance Marking
# ---------------------------------------------------------------------------
@transaction.atomic
def mark_bulk_attendance(tenant, class_instance_id, records, marked_by_teacher):
    """
    Mark attendance for multiple students in a single class session.
    records: list of {"student_id": uuid, "status": "PRESENT|ABSENT|LATE"}
    """
    from scheduling.models import ClassAttendance
    from classes.models import ScheduledClass
    from accounts.models import Student

    class_instance = ScheduledClass.objects.get(id=class_instance_id, tenant=tenant)

    saved = 0
    for record in records:
        student = Student.objects.get(id=record['student_id'], tenant=tenant)
        att, created = ClassAttendance.objects.update_or_create(
            tenant=tenant,
            class_instance=class_instance,
            student=student,
            defaults={
                'status': record['status'],
                'marked_by': marked_by_teacher,
                'marked_at': timezone.now(),
            }
        )
        saved += 1

    return saved
