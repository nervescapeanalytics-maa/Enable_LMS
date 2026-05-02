"""
Teacher dashboard — Offline Test Marks ("Tests & Marks") page.

Workflow:
    GET  /teacher/offline-marks/                  → class + test selectors
    GET  /teacher/offline-marks/?batch=...&test=  → roster grid (student × subject)
    POST /teacher/offline-marks/                  → upsert OfflineTestMarks rows

Rules:
    * Auth: session['user_type'] == 'TEACHER' and session['user_id'] is a Teacher.id
    * Class list: Batches the teacher is assigned to via BatchTeacher.
    * Test list: Tests in the same tenant + same batch (or batch-agnostic OPEN tests).
    * Subjects: derived from TestSection.subject; falls back to Test.subject if no sections.
    * Total marks: auto-populated from Test.total_marks; teachers cannot exceed it per subject.
    * Each (student, test, subject) is upserted (idempotent per save).
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import Teacher, Student
from academics.models import Batch, BatchTeacher, Subject, Users
from assessments.models import OfflineTestMarks, Test, TestSection
from assessments.permissions import log_exam_event

logger = logging.getLogger(__name__)


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


def _teacher_batches(teacher: Teacher):
    return (
        Batch.objects
        .filter(
            tenant=teacher.tenant,
            batch_teachers__teacher=teacher,
        )
        .distinct()
        .order_by('name')
    )


def _tests_for_batch(teacher: Teacher, batch: Optional[Batch]):
    qs = Test.objects.filter(tenant=teacher.tenant, is_deleted=False,
                             status__in=['PUBLISHED', 'ACTIVE', 'COMPLETED'])
    if batch:
        qs = qs.filter(Q(batch=batch) | Q(batch__isnull=True))
    return qs.order_by('-created_at')


def _test_subjects(test: Test):
    """Return list of Subject objects expected for this test (multi-subject aware).

    If the Test has TestSections with subjects → use those (deduped, ordered by section_order).
    Else fall back to the Test.subject (single-subject test).
    """
    sections = list(
        TestSection.objects
        .filter(test=test, subject__isnull=False)
        .select_related('subject')
        .order_by('section_order')
    )
    if sections:
        seen = []
        for s in sections:
            if s.subject_id and s.subject not in seen:
                seen.append(s.subject)
        return seen
    return [test.subject] if test.subject_id else []


def _batch_students(batch: Batch):
    """All active students enrolled in the batch (via Student.batch FK + academics.Users)."""
    primary_ids = list(
        Student.objects
        .filter(batch=batch, deleted_at__isnull=True)
        .values_list('id', flat=True)
    )
    enrolled_ids = list(
        Users.objects
        .filter(batch=batch, is_active=True)
        .values_list('student_id', flat=True)
    )
    ids = {sid for sid in primary_ids + enrolled_ids if sid}
    return list(
        Student.objects
        .filter(id__in=ids, deleted_at__isnull=True)
        .order_by('first_name', 'last_name')
    )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class TeacherOfflineMarksView(View):
    """GET = render selector + (optional) roster; POST = save marks."""

    template_name = 'teacher/offline_marks.html'

    def get(self, request):
        teacher = _require_teacher(request)
        if not teacher:
            return redirect('/login/?role=teacher')

        batches = list(_teacher_batches(teacher))
        batch_id = request.GET.get('batch') or ''
        test_id = request.GET.get('test') or ''

        selected_batch = None
        if batch_id:
            try:
                selected_batch = Batch.objects.get(
                    id=batch_id, tenant=teacher.tenant,
                    batch_teachers__teacher=teacher,
                )
            except (Batch.DoesNotExist, ValueError):
                selected_batch = None

        tests = list(_tests_for_batch(teacher, selected_batch))

        selected_test = None
        if test_id and selected_batch is not None:
            try:
                selected_test = Test.objects.get(
                    id=test_id, tenant=teacher.tenant, is_deleted=False,
                )
            except (Test.DoesNotExist, ValueError):
                selected_test = None

        roster_rows = []
        subjects = []
        per_subject_total = Decimal('0')
        if selected_batch and selected_test:
            subjects = _test_subjects(selected_test)
            students = _batch_students(selected_batch)
            n_subj = max(1, len(subjects))
            try:
                per_subject_total = (selected_test.total_marks or Decimal('0')) / n_subj
            except (TypeError, InvalidOperation, ZeroDivisionError):
                per_subject_total = Decimal('0')

            # Index existing marks for prefill
            existing = {
                (m.student_id, m.subject_id): m
                for m in OfflineTestMarks.objects.filter(
                    tenant=teacher.tenant,
                    test=selected_test,
                    student__in=students,
                )
            }

            for s in students:
                row = {
                    'student': s,
                    'subjects': [],
                    'total_obtained': Decimal('0'),
                }
                for subj in subjects:
                    rec = existing.get((s.id, subj.id if subj else None))
                    obt = rec.marks_obtained if rec else None
                    row['subjects'].append({
                        'subject': subj,
                        'value': obt,
                    })
                    if obt is not None:
                        row['total_obtained'] += obt
                roster_rows.append(row)

        return render(request, self.template_name, {
            'teacher': teacher,
            'user_name': f'{teacher.first_name} {teacher.last_name}',
            'batches': batches,
            'tests': tests,
            'selected_batch': selected_batch,
            'selected_test': selected_test,
            'subjects': subjects,
            'roster_rows': roster_rows,
            'per_subject_total': per_subject_total,
            'total_marks': (selected_test.total_marks if selected_test else 0) or 0,
        })

    @transaction.atomic
    def post(self, request):
        teacher = _require_teacher(request)
        if not teacher:
            return redirect('/login/?role=teacher')

        batch_id = request.POST.get('batch')
        test_id = request.POST.get('test')
        if not batch_id or not test_id:
            messages.error(request, 'Pick a class and a test first.')
            return redirect(reverse('teacher-offline-marks'))

        try:
            batch = Batch.objects.get(
                id=batch_id, tenant=teacher.tenant,
                batch_teachers__teacher=teacher,
            )
        except (Batch.DoesNotExist, ValueError):
            return HttpResponse('Forbidden', status=403)

        try:
            test = Test.objects.get(id=test_id, tenant=teacher.tenant, is_deleted=False)
        except (Test.DoesNotExist, ValueError):
            messages.error(request, 'Selected test no longer exists.')
            return redirect(reverse('teacher-offline-marks'))

        subjects = _test_subjects(test)
        if not subjects:
            messages.error(request, 'Cannot record marks: this test has no subjects configured.')
            return redirect(reverse('teacher-offline-marks') + f'?batch={batch.id}&test={test.id}')

        n_subj = len(subjects)
        per_subj_max = (test.total_marks or Decimal('0')) / Decimal(n_subj)
        students = _batch_students(batch)
        saved = errors = 0

        for student in students:
            for subj in subjects:
                key = f'm_{student.id}_{subj.id if subj else "none"}'
                raw = (request.POST.get(key) or '').strip()
                if raw == '':
                    continue
                try:
                    obt = Decimal(raw)
                except (InvalidOperation, TypeError):
                    errors += 1
                    continue
                if obt < 0 or obt > per_subj_max:
                    errors += 1
                    continue

                pct = (obt / per_subj_max * Decimal('100')) if per_subj_max else Decimal('0')

                OfflineTestMarks.objects.update_or_create(
                    tenant=teacher.tenant,
                    student=student,
                    subject=subj,
                    test=test,
                    defaults={
                        'batch': batch,
                        'test_name': test.title or test.test_code,
                        'test_date': (test.start_datetime.date()
                                      if test.start_datetime else timezone.now().date()),
                        'total_marks': per_subj_max,
                        'marks_obtained': obt,
                        'percentage': pct.quantize(Decimal('0.01')),
                        'entered_by': teacher.id,
                        'entered_at': timezone.now(),
                    },
                )
                saved += 1

        log_exam_event(
            request=request, actor=teacher,
            action='OFFLINE_MARKS_SAVE',
            resource_type='Test', resource_id=test.id, resource_name=test.test_code,
            description=f'teacher saved {saved} offline mark rows ({errors} errors) for {batch.name}',
            extra_meta={'batch_id': str(batch.id), 'saved': saved, 'errors': errors},
        )

        if errors:
            messages.warning(request, f'Saved {saved} entries; {errors} skipped (out of range or invalid).')
        else:
            messages.success(request, f'Saved {saved} mark entries.')
        return redirect(reverse('teacher-offline-marks') + f'?batch={batch.id}&test={test.id}')


class TeacherTestApiView(View):
    """GET /teacher/api/tests/?batch=<uuid>  → JSON list (for dynamic select)."""
    def get(self, request):
        teacher = _require_teacher(request)
        if not teacher:
            return JsonResponse({'ok': False}, status=401)
        batch_id = request.GET.get('batch')
        batch = None
        if batch_id:
            try:
                batch = Batch.objects.get(
                    id=batch_id, tenant=teacher.tenant,
                    batch_teachers__teacher=teacher,
                )
            except (Batch.DoesNotExist, ValueError):
                return JsonResponse({'ok': False}, status=404)
        tests = _tests_for_batch(teacher, batch)
        return JsonResponse({
            'ok': True,
            'tests': [
                {
                    'id': str(t.id), 'code': t.test_code, 'title': t.title,
                    'total_marks': str(t.total_marks or 0),
                    'duration': t.total_duration_minutes,
                }
                for t in tests
            ],
        })
