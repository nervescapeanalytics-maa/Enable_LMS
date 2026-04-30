"""
Student Schedule Portal — server-rendered Django view.

Replaces the React SPA's /student/dashboard/schedule route which renders
entirely from hardcoded local state (no API calls, no real data).

Routes:
    /student/schedule/           Upcoming classes (default)
    /student/schedule/?view=tests    Upcoming tests
    /student/schedule/?view=all      All classes

Auth: session['user_type'] == 'STUDENT' + session['user_id'] == Student.id
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import Student
from accounts.views.student_views import (
    _get_student,
    _get_student_batch_ids,
    _get_student_classes,
)
from assessments.models import Test
from core.student_exam_views import _require_student, _student_batch_ids

logger = logging.getLogger(__name__)


def _upcoming_tests(student: Student):
    """Return PUBLISHED tests that are open right now, ordered soonest first."""
    now = timezone.now()
    batch_ids = _student_batch_ids(student)
    qs = Test.objects.filter(
        tenant=student.tenant,
        is_deleted=False,
        status__in=['PUBLISHED', 'ACTIVE'],
    ).select_related('subject', 'chapter')

    # Schedule window
    qs = qs.filter(
        Q(start_datetime__isnull=True) | Q(start_datetime__lte=now)
    ).filter(
        Q(end_datetime__isnull=True) | Q(end_datetime__gte=now)
    )

    # Access
    access_q = (
        Q(access_mode='OPEN')
        | Q(access_mode='SCHEDULED')
        | Q(access_mode='PASSWORD')
        | Q(access_mode='BATCH_ONLY', batch_id__in=batch_ids)
        | Q(access_mode='BATCH_ONLY', batch__isnull=True)
    )
    qs = qs.filter(access_q)
    return qs.order_by('start_datetime')[:30]


class StudentScheduleView(View):
    """Server-rendered schedule page for students."""

    def get(self, request):
        if request.session.get('user_type') != 'STUDENT':
            return redirect('/login/?role=student')

        student = _require_student(request)
        if student is None:
            return redirect('/login/?role=student')

        view = request.GET.get('view', 'upcoming')
        today = timezone.localdate()

        # Resolve display name
        user_name = (
            f"{student.first_name} {student.last_name}".strip()
            or student.phone_number
            or 'Student'
        )

        batch_ids = _get_student_batch_ids(student)

        context = {
            'view': view,
            'today': today,
            'user_name': user_name,
            'upcoming_classes': [],
            'all_classes': [],
            'upcoming_tests': [],
        }

        if view in ('upcoming', ''):
            upcoming_qs = _get_student_classes(
                student, batch_ids,
                scheduled_date__gte=today,
                status__in=['SCHEDULED', 'RESCHEDULED', 'LIVE'],
            ).order_by('scheduled_date', 'start_time')[:30]
            context['upcoming_classes'] = [_schedule_class_row(sc, today) for sc in upcoming_qs]

        elif view == 'all':
            all_qs = _get_student_classes(
                student, batch_ids,
            ).order_by('-scheduled_date', '-start_time')[:100]
            context['all_classes'] = [_schedule_class_row(sc, today) for sc in all_qs]

        elif view == 'tests':
            context['upcoming_tests'] = list(_upcoming_tests(student))

        return render(request, 'student/schedule.html', context)


def _schedule_class_row(sc, today):
    """Return a lightweight dict for schedule table rows."""
    return {
        'id': str(sc.id),
        'subject': sc.subject or '—',
        'teacher_name': (
            f"{sc.teacher.first_name} {sc.teacher.last_name}".strip()
            if sc.teacher else '—'
        ),
        'scheduled_date': sc.scheduled_date,
        'start_time': sc.start_time,
        'end_time': sc.end_time,
        'status': sc.status,
        'class_type': getattr(sc, 'class_type', '') or '—',
    }
