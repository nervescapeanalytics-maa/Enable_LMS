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
    """Batches the teacher is assigned to via BatchTeacher.

    Fallback: if no BatchTeacher rows exist for this teacher (typical for
    fresh tenants where the M2M hasn't been seeded yet), surface all
    batches in the same tenant so the teacher can still pick a class.
    Admin can later restrict via BatchTeacher rows.
    """
    explicit = (
        Batch.objects
        .filter(tenant=teacher.tenant, batch_teachers__teacher=teacher)
        .distinct()
        .order_by('name')
    )
    if explicit.exists():
        return explicit
    return Batch.objects.filter(tenant=teacher.tenant).order_by('name')


def _resolve_teacher_batch(teacher: Teacher, batch_id: str) -> Optional[Batch]:
    """Look up a Batch the teacher is allowed to act on.

    Strict path: BatchTeacher row exists. Lenient fallback: same tenant
    when the teacher has no BatchTeacher rows at all.
    """
    if not batch_id:
        return None
    try:
        # Strict: explicit M2M row
        return Batch.objects.get(
            id=batch_id, tenant=teacher.tenant,
            batch_teachers__teacher=teacher,
        )
    except (Batch.DoesNotExist, ValueError):
        pass
    # Lenient: only if teacher has NO explicit assignments in this tenant
    has_any = BatchTeacher.objects.filter(
        tenant=teacher.tenant, teacher=teacher,
    ).exists()
    if has_any:
        return None
    try:
        return Batch.objects.get(id=batch_id, tenant=teacher.tenant)
    except (Batch.DoesNotExist, ValueError):
        return None


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

        selected_batch = _resolve_teacher_batch(teacher, batch_id)

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

        batch = _resolve_teacher_batch(teacher, batch_id)
        if batch is None:
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
            batch = _resolve_teacher_batch(teacher, batch_id)
            if batch is None:
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


# ---------------------------------------------------------------------------
# Test Report tab — ranked roster + summary stats + Excel export
# ---------------------------------------------------------------------------
class TeacherTestReportView(View):
    """Renders ranked results for a (batch, test) pair with average / highest /
    lowest / pass-rate stat cards. Pulls totals from OfflineTestMarks; if
    online attempts exist they are also folded in (best score per student)."""

    template_name = 'teacher/test_report.html'

    def get(self, request):
        teacher = _require_teacher(request)
        if not teacher:
            return redirect('/login/?role=teacher')

        batches = list(_teacher_batches(teacher))
        batch_id = request.GET.get('batch') or ''
        test_id = request.GET.get('test') or ''
        export = request.GET.get('export') == 'excel'

        selected_batch = _resolve_teacher_batch(teacher, batch_id)

        tests = list(_tests_for_batch(teacher, selected_batch))
        selected_test = None
        if test_id and selected_batch is not None:
            try:
                selected_test = Test.objects.get(
                    id=test_id, tenant=teacher.tenant, is_deleted=False,
                )
            except (Test.DoesNotExist, ValueError):
                selected_test = None

        rows = []
        stats = None
        total_max = Decimal('0')
        passing_pct = Decimal('33')

        if selected_batch and selected_test:
            students = _batch_students(selected_batch)
            total_max = selected_test.total_marks or Decimal('0')
            passing_pct = selected_test.passing_percent or Decimal('33')

            # Aggregate offline marks by student (sum across subjects/sections).
            offline_totals: dict = {}
            for m in OfflineTestMarks.objects.filter(
                tenant=teacher.tenant, test=selected_test, student__in=students,
            ):
                offline_totals.setdefault(m.student_id, Decimal('0'))
                offline_totals[m.student_id] += (m.marks_obtained or Decimal('0'))

            # Online attempts — pick best (highest score) submitted attempt per student.
            online_best: dict = {}
            try:
                from assessments.models import TestAttempt
                for a in TestAttempt.objects.filter(
                    tenant=teacher.tenant, test=selected_test,
                    student__in=students, status__in=['SUBMITTED', 'GRADED', 'COMPLETED'],
                ):
                    cur = online_best.get(a.student_id)
                    sc = a.total_score or Decimal('0')
                    if cur is None or sc > cur:
                        online_best[a.student_id] = sc
            except Exception:  # noqa: BLE001 — model fields may differ across envs
                pass

            tmp = []
            for s in students:
                obt = offline_totals.get(s.id)
                onl = online_best.get(s.id)
                # Prefer the higher of the two if both exist
                if obt is None and onl is None:
                    continue
                final = max([v for v in (obt, onl) if v is not None])
                pct = (final / total_max * Decimal('100')) if total_max else Decimal('0')
                tmp.append({
                    'student': s,
                    'obtained': final,
                    'percentage': pct.quantize(Decimal('0.1')),
                    'is_pass': pct >= passing_pct,
                    'source': 'online' if (onl is not None and (obt is None or onl >= obt)) else 'offline',
                })
            tmp.sort(key=lambda r: (-float(r['obtained']), r['student'].first_name or ''))
            for i, r in enumerate(tmp, start=1):
                r['rank'] = i
                rows.append(r)

            if rows:
                marks = [float(r['obtained']) for r in rows]
                pass_count = sum(1 for r in rows if r['is_pass'])
                stats = {
                    'average': round(sum(marks) / len(marks), 1),
                    'highest': max(marks),
                    'lowest': min(marks),
                    'pass_count': pass_count,
                    'total_count': len(rows),
                    'pass_rate': round(pass_count / len(rows) * 100),
                    'total_max': float(total_max),
                }

        if export and rows and selected_test:
            import csv as _csv
            import io as _io
            sio = _io.StringIO()
            sio.write('\ufeff')  # UTF-8 BOM for Excel
            w = _csv.writer(sio)
            w.writerow(['Rank', 'Student', 'Marks', 'Total', 'Percentage', 'Status', 'Source'])
            for r in rows:
                full = f"{r['student'].first_name or ''} {r['student'].last_name or ''}".strip()
                w.writerow([
                    r['rank'], full, r['obtained'], total_max,
                    f"{r['percentage']}%", 'Pass' if r['is_pass'] else 'Fail', r['source'],
                ])
            safe = (selected_test.test_code or 'test').replace('/', '_').replace(' ', '_')
            resp = HttpResponse(sio.getvalue().encode('utf-8'),
                                content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="{safe}_report.csv"'
            return resp

        return render(request, self.template_name, {
            'teacher': teacher,
            'user_name': f'{teacher.first_name} {teacher.last_name}',
            'batches': batches,
            'tests': tests,
            'selected_batch': selected_batch,
            'selected_test': selected_test,
            'rows': rows,
            'stats': stats,
            'total_marks': total_max,
            'passing_pct': passing_pct,
        })

