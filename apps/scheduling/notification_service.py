"""
Scheduling - Notification Service

Handles sending notifications for class events:
- 30 minutes before class (teacher + students)
- Class goes live (students)
- Class cancelled (students)
- Teacher no-show (admin email + student push)
- Schedule changes (students)

Uses the existing Notification model from the communication app.
"""
import logging
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('lms')


def _get_enrolled_students(class_instance):
    """Get all actively enrolled students for a class instance."""
    from scheduling.models import Enrollment

    # Check if this is from a recurring rule
    meta = class_instance.class_meta or {}
    rule_id = meta.get('recurring_rule_id')

    student_ids = set()

    # From recurring rule
    if rule_id:
        rule_enrollments = Enrollment.objects.filter(
            recurring_rule_id=rule_id, is_active=True
        ).values_list('student_id', flat=True)
        student_ids.update(rule_enrollments)

    # Direct ad-hoc enrollments
    adhoc_enrollments = Enrollment.objects.filter(
        class_instance=class_instance, is_active=True
    ).values_list('student_id', flat=True)
    student_ids.update(adhoc_enrollments)

    if not student_ids:
        return []

    from academics.models import Users
    return list(Users.objects.filter(student_id__in=student_ids, is_active=True))


def _create_notification(tenant, user_id, user_type, title, message,
                         notification_type='INFO', channel='PUSH',
                         source_type=None, source_id=None, action_url=None):
    """Create a notification record in the communication module."""
    from communication.models import Notification
    return Notification.objects.create(
        tenant=tenant,
        user_id=user_id,
        user_type=user_type,
        notification_type=notification_type,
        channel=channel,
        title=title,
        message=message,
        source_type=source_type,
        source_id=source_id,
        action_url=action_url,
    )


# ---------------------------------------------------------------------------
# 30 minutes before class — Teacher notification
# ---------------------------------------------------------------------------
def notify_teacher_pre_class(class_instance):
    """Send notification to teacher 30 min before class."""
    teacher = class_instance.teacher
    if not teacher:
        return

    subject_name = class_instance.subject or 'your'
    title = f"Your {subject_name} class starts in 30 minutes"
    message = (
        f"Your {subject_name} class '{class_instance.title}' starts in 30 minutes. "
        f"Be ready to go live."
    )

    _create_notification(
        tenant=class_instance.tenant,
        user_id=teacher.id,
        user_type='TEACHER',
        title=title,
        message=message,
        notification_type='ACTION_REQUIRED',
        source_type='ScheduledClass',
        source_id=class_instance.id,
    )
    logger.info(f"[notify] Pre-class notification sent to teacher {teacher.id} for {class_instance.class_code}")


# ---------------------------------------------------------------------------
# 30 minutes before class — Student notifications
# ---------------------------------------------------------------------------
def notify_students_pre_class(class_instance):
    """Send notification to all enrolled students 30 min before class."""
    students = _get_enrolled_students(class_instance)
    teacher = class_instance.teacher
    teacher_name = teacher.full_name if teacher else 'your teacher'
    subject_name = class_instance.subject or 'your'

    for student in students:
        title = f"Your {subject_name} class starts in 30 minutes"
        message = (
            f"Your {subject_name} class with {teacher_name} starts in 30 minutes."
        )
        _create_notification(
            tenant=class_instance.tenant,
            user_id=student.student_id or student.id,
            user_type='STUDENT',
            title=title,
            message=message,
            source_type='ScheduledClass',
            source_id=class_instance.id,
        )

    logger.info(f"[notify] Pre-class notification sent to {len(students)} students for {class_instance.class_code}")


# ---------------------------------------------------------------------------
# Class goes LIVE — Student notifications
# ---------------------------------------------------------------------------
def notify_students_class_live(class_instance):
    """Notify students when a class goes live."""
    students = _get_enrolled_students(class_instance)
    subject_name = class_instance.subject or 'Your'

    for student in students:
        _create_notification(
            tenant=class_instance.tenant,
            user_id=student.student_id or student.id,
            user_type='STUDENT',
            title=f"{subject_name} class is live now",
            message=f"{subject_name} class is live now. Join now.",
            notification_type='ACTION_REQUIRED',
            source_type='ScheduledClass',
            source_id=class_instance.id,
        )

    logger.info(f"[notify] Live notification sent to {len(students)} students for {class_instance.class_code}")


# ---------------------------------------------------------------------------
# Class cancelled — Student notifications
# ---------------------------------------------------------------------------
def notify_students_class_cancelled(class_instance):
    """Notify students when a class is cancelled."""
    students = _get_enrolled_students(class_instance)
    subject_name = class_instance.subject or 'Your'
    time_str = class_instance.start_time.strftime('%I:%M %p') if class_instance.start_time else ''

    for student in students:
        _create_notification(
            tenant=class_instance.tenant,
            user_id=student.student_id or student.id,
            user_type='STUDENT',
            title=f"Class cancelled",
            message=f"Your {subject_name} class at {time_str} has been cancelled.",
            notification_type='WARNING',
            source_type='ScheduledClass',
            source_id=class_instance.id,
        )

    logger.info(f"[notify] Cancellation notification sent to {len(students)} students for {class_instance.class_code}")


# ---------------------------------------------------------------------------
# Teacher No-Show — Admin email + Student notification
# ---------------------------------------------------------------------------
def notify_admin_teacher_noshow(class_instance):
    """Send email to admin when teacher doesn't show up."""
    teacher = class_instance.teacher
    teacher_name = teacher.full_name if teacher else 'Unknown Teacher'
    time_str = class_instance.start_time.strftime('%I:%M %p') if class_instance.start_time else ''

    subject = f"Teacher No-Show: {class_instance.title}"
    body = (
        f"Teacher No-Show Alert\n\n"
        f"Class: {class_instance.title}\n"
        f"Scheduled Time: {class_instance.scheduled_date} at {time_str}\n"
        f"Teacher: {teacher_name}\n\n"
        f"The teacher did not go live within 30 minutes of the scheduled time. "
        f"The class has been automatically cancelled and students have been notified."
    )

    try:
        admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@lmsplatform.com')
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=True,
        )
        logger.info(f"[notify] No-show email sent for {class_instance.class_code}")
    except Exception as e:
        logger.error(f"[notify] Failed to send no-show email: {e}")


# ---------------------------------------------------------------------------
# Schedule Updated — Student notifications
# ---------------------------------------------------------------------------
def notify_students_schedule_updated(old_rule, new_rule, effective_from):
    """Notify students when a recurring schedule is updated."""
    from scheduling.models import Enrollment
    from academics.models import Users

    student_ids = Enrollment.objects.filter(
        recurring_rule=new_rule, is_active=True
    ).values_list('student_id', flat=True)

    students = Users.objects.filter(student_id__in=student_ids, is_active=True)
    subject_name = new_rule.subject.name if new_rule.subject else 'your'

    for student in students:
        _create_notification(
            tenant=new_rule.tenant,
            user_id=student.student_id or student.id,
            user_type='STUDENT',
            title=f"Schedule updated",
            message=(
                f"Your {subject_name} class schedule has been updated "
                f"from {effective_from.strftime('%B %d, %Y')}."
            ),
            source_type='RecurringRule',
            source_id=new_rule.id,
        )

    logger.info(f"[notify] Schedule update notification sent to {len(students)} students for rule {new_rule.id}")
