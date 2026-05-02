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

        qs = (
            Test.objects
            .filter(
                tenant=teacher.tenant,
                is_deleted=False,
                status__in=['PUBLISHED', 'ACTIVE', 'COMPLETED'],
            )
            .select_related('subject', 'batch', 'chapter', 'teacher')
            .annotate(attempts_count=Count('attempts', distinct=True))
            .order_by('-published_at', '-created_at')
        )

        batch_id = request.GET.get('batch') or ''
        subject_id = request.GET.get('subject') or ''

        if batch_id:
            qs = qs.filter(Q(batch_id=batch_id) | Q(batch__isnull=True))
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        return render(request, self.template_name, {
            'teacher': teacher,
            'user_name': f'{teacher.first_name} {teacher.last_name}',
            'tests': list(qs[:300]),
            'batches': Batch.objects.filter(
                tenant=teacher.tenant,
                batch_teachers__teacher=teacher,
            ).distinct().order_by('name'),
            'subjects': Subject.objects.filter(tenant=teacher.tenant).order_by('name'),
            'selected_batch_id': batch_id,
            'selected_subject_id': subject_id,
        })
