"""
Teacher dashboard — Published Tests page.

Lists every published/active/completed Test in the teacher's tenant
(read-only — teachers cannot edit online exam authoring per platform policy).
Supports a basic filter by Batch & Subject.
"""
from __future__ import annotations

from typing import Optional

from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import Teacher
from academics.models import Batch, Subject
from assessments.models import Test, TestAttempt


def _require_teacher(request) -> Optional[Teacher]:
    if request.session.get('user_type') != 'TEACHER':
        return None
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Teacher.objects.select_related('tenant').get(id=user_id)
    except (Teacher.DoesNotExist, ValueError):
        return None


class TeacherPublishedTestsView(View):
    template_name = 'teacher/published_tests.html'

    def get(self, request):
        teacher = _require_teacher(request)
        if not teacher:
            return redirect('/login/?role=teacher')

        # Include PUBLISHED/ACTIVE/COMPLETED tests in the tenant, PLUS DRAFT
        # tests that this teacher owns (so they can dry-run-preview their own
        # work before submitting for admin publish).
        qs = (
            Test.objects
            .filter(
                tenant=teacher.tenant,
                is_deleted=False,
            )
            .filter(
                Q(status__in=['PUBLISHED', 'ACTIVE', 'COMPLETED'])
                | Q(status='DRAFT', teacher=teacher)
                | Q(status='DRAFT', created_by=teacher.id)
            )
            .select_related('subject', 'batch', 'chapter', 'teacher')
            .annotate(
                attempts_count=Count(
                    'attempts',
                    filter=Q(attempts__is_preview=False),
                    distinct=True,
                ),
            )
            .distinct()
            .order_by('-published_at', '-created_at')
        )

        batch_id = request.GET.get('batch') or ''
        subject_id = request.GET.get('subject') or ''

        if batch_id:
            qs = qs.filter(Q(batch_id=batch_id) | Q(batch__isnull=True))
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        tests_list = list(qs[:300])
        # Mark tests this teacher owns (for showing Preview action in template)
        teacher_id = teacher.id
        for t in tests_list:
            t.is_owner = (
                (t.teacher_id and str(t.teacher_id) == str(teacher_id))
                or (getattr(t, 'created_by', None) and str(t.created_by) == str(teacher_id))
            )

        return render(request, self.template_name, {
            'teacher': teacher,
            'user_name': f'{teacher.first_name} {teacher.last_name}',
            'tests': tests_list,
            'batches': Batch.objects.filter(
                tenant=teacher.tenant,
                batch_teachers__teacher=teacher,
            ).distinct().order_by('name'),
            'subjects': Subject.objects.filter(tenant=teacher.tenant).order_by('name'),
            'selected_batch_id': batch_id,
            'selected_subject_id': subject_id,
        })
