"""
Student Exam REST API — Phase 3.

Endpoints (all CSRF-protected, session-auth as STUDENT):

    POST /student/exams/<test_id>/api/answer/         Auto-save one answer
    POST /student/exams/<test_id>/api/proctor-event/  Log a proctoring violation
    POST /student/exams/<test_id>/api/snapshot/       Upload a webcam snapshot
    POST /student/exams/<test_id>/api/submit/         Final submit & grade

Every state-changing call uses the existing audit log helper
``assessments.permissions.log_exam_event`` so the activity is auditable.

Proctoring features are gated by feature flags (admin-managed):

    exam.tab_switch_detection
    exam.copy_paste_block
    exam.fullscreen_lockdown
    exam.devtools_detection
    exam.proctoring_snapshots

Auto-submit thresholds:

    TAB_SWITCH_LIMIT      — auto-submit after this many tab switches
    COPY_PASTE_LIMIT      — auto-submit after this many copy/paste violations
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import Student
from assessments.models import (
    Question,
    Test,
    TestAttempt,
    TestAttemptAnswer,
)
from assessments.permissions import is_feature_enabled, log_exam_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TAB_SWITCH_LIMIT = 5
COPY_PASTE_LIMIT = 10
SNAPSHOT_MAX_BYTES = 1024 * 1024  # 1 MB
SNAPSHOT_ALLOWED_MIME = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_student(request):
    if request.session.get('user_type') != 'STUDENT':
        return None
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Student.objects.select_related('tenant').get(id=user_id)
    except (Student.DoesNotExist, ValueError):
        return None


def _get_test_and_attempt(student, test_id):
    """Return (test, in_progress_attempt) or (None, None)."""
    try:
        test = Test.objects.get(id=test_id, tenant=student.tenant, is_deleted=False)
    except (Test.DoesNotExist, ValueError):
        return None, None
    attempt = (
        TestAttempt.objects
        .filter(test=test, student=student, status='IN_PROGRESS')
        .order_by('-started_at')
        .first()
    )
    return test, attempt


def _json_body(request):
    try:
        return json.loads((request.body or b'').decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


def _err(msg, code=400):
    return JsonResponse({'ok': False, 'error': msg}, status=code)


def _grade_now(request, test, attempt, *, auto: bool):
    """Delegate to the existing synchronous grader in core.student_exam_views."""
    from core.student_exam_views import ExamTakeView

    questions = list(
        Question.objects.filter(test=test, is_deleted=False)
        .order_by('question_order', 'question_code')
    )
    prior = {
        str(a.question_id): (a.student_answer or '').upper()
        for a in TestAttemptAnswer.objects.filter(attempt=attempt)
    }
    posted = {f'q_{qid}': ans for qid, ans in prior.items()}
    ExamTakeView()._grade_and_submit(
        request, attempt, test, questions, posted, auto=auto,
    )


# ===========================================================================
# Auto-save
# ===========================================================================
class AnswerAutoSaveView(View):
    """POST { question_id, answer } — upsert a single TestAttemptAnswer."""

    def post(self, request, test_id):
        student = _require_student(request)
        if not student:
            return _err('Not authenticated', 401)

        test, attempt = _get_test_and_attempt(student, test_id)
        if not attempt:
            return _err('No active attempt', 404)

        body = _json_body(request)
        qid = body.get('question_id')
        ans = (body.get('answer') or '').strip().upper()[:50]

        if not qid:
            return _err('question_id required')

        try:
            question = Question.objects.get(id=qid, test=test, is_deleted=False)
        except (Question.DoesNotExist, ValueError):
            return _err('Question not found', 404)

        now = timezone.now()
        with transaction.atomic():
            answer, created = (
                TestAttemptAnswer.objects
                .select_for_update()
                .get_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={
                        'tenant': attempt.tenant,
                        'student_answer': ans or None,
                        'status': 'ANSWERED' if ans else 'SKIPPED',
                        'first_answered_at': now if ans else None,
                        'last_answered_at': now if ans else None,
                        'visit_count': 1,
                    },
                )
            )
            if not created:
                changed = (answer.student_answer or '') != ans
                answer.student_answer = ans or None
                answer.status = 'ANSWERED' if ans else 'SKIPPED'
                if changed and ans:
                    answer.answer_change_count = (answer.answer_change_count or 0) + 1
                if ans and not answer.first_answered_at:
                    answer.first_answered_at = now
                if ans:
                    answer.last_answered_at = now
                answer.visit_count = (answer.visit_count or 0) + 1
                answer.save(update_fields=[
                    'student_answer',
                    'status',
                    'answer_change_count',
                    'first_answered_at',
                    'last_answered_at',
                    'visit_count',
                ])

        return JsonResponse({
            'ok': True,
            'saved_at': now.isoformat(),
            'question_id': str(question.id),
            'answer': ans,
        })


# ===========================================================================
# Proctoring violations
# ===========================================================================
class ProctorEventView(View):
    """POST { event_type, meta } — record a proctoring violation."""

    EVENT_FLAGS = {
        'TAB_SWITCH':      'exam.tab_switch_detection',
        'WINDOW_BLUR':     'exam.tab_switch_detection',
        'COPY':            'exam.copy_paste_block',
        'PASTE':           'exam.copy_paste_block',
        'CUT':             'exam.copy_paste_block',
        'CONTEXT_MENU':    'exam.copy_paste_block',
        'FULLSCREEN_EXIT': 'exam.fullscreen_lockdown',
        'DEVTOOLS':        'exam.devtools_detection',
    }

    def post(self, request, test_id):
        student = _require_student(request)
        if not student:
            return _err('Not authenticated', 401)

        test, attempt = _get_test_and_attempt(student, test_id)
        if not attempt:
            return _err('No active attempt', 404)

        body = _json_body(request)
        event_type = (body.get('event_type') or '').upper()
        meta = body.get('meta') or {}
        if not isinstance(meta, dict):
            meta = {}

        flag_key = self.EVENT_FLAGS.get(event_type)
        if not flag_key:
            return _err('Unknown event_type')

        if not is_feature_enabled(flag_key, tenant=student.tenant, user_type='STUDENT'):
            return JsonResponse({'ok': True, 'ignored': True})

        now = timezone.now()
        auto_submit = False

        with transaction.atomic():
            attempt = TestAttempt.objects.select_for_update().get(id=attempt.id)
            violations = list(attempt.proctoring_violations or [])
            violations.append({
                'event_type': event_type,
                'meta': meta,
                'at': now.isoformat(),
            })
            # cap to prevent unbounded JSON growth
            attempt.proctoring_violations = violations[-200:]

            if event_type in ('TAB_SWITCH', 'WINDOW_BLUR'):
                attempt.tab_switch_count = (attempt.tab_switch_count or 0) + 1
                if attempt.tab_switch_count >= TAB_SWITCH_LIMIT:
                    auto_submit = True
            elif event_type in ('COPY', 'PASTE', 'CUT'):
                attempt.copy_paste_attempts = (attempt.copy_paste_attempts or 0) + 1
                if attempt.copy_paste_attempts >= COPY_PASTE_LIMIT:
                    auto_submit = True

            update_fields = [
                'proctoring_violations',
                'tab_switch_count',
                'copy_paste_attempts',
            ]
            if auto_submit:
                attempt.auto_terminated = True
                attempt.termination_reason = (
                    f'Proctoring threshold exceeded ({event_type})'
                )[:500]
                update_fields += ['auto_terminated', 'termination_reason']
            attempt.save(update_fields=update_fields)

        log_exam_event(
            request=request,
            actor=student,
            action='PROCTOR_VIOLATION',
            resource_type='TestAttempt',
            resource_id=attempt.id,
            resource_name=test.test_code,
            description=f'{event_type} during {test.test_code}',
            severity='WARNING',
            is_security_event=True,
            extra_meta={
                'event_type': event_type,
                'tab_switch_count': attempt.tab_switch_count,
                'copy_paste_attempts': attempt.copy_paste_attempts,
                **meta,
            },
        )

        resp = {
            'ok': True,
            'tab_switch_count': attempt.tab_switch_count,
            'copy_paste_attempts': attempt.copy_paste_attempts,
        }

        if auto_submit:
            try:
                _grade_now(request, test, attempt, auto=True)
            except Exception:
                logger.exception('proctor auto-submit grading failed')
            resp['auto_submitted'] = True
            resp['redirect'] = reverse(
                'student-exam-result',
                kwargs={'test_id': test.id, 'attempt_id': attempt.id},
            )

        return JsonResponse(resp)


# ===========================================================================
# Webcam snapshots
# ===========================================================================
class ProctorSnapshotView(View):
    """POST multipart 'snapshot' — store under MEDIA_ROOT/proctoring/<tenant>/<attempt>/."""

    def post(self, request, test_id):
        student = _require_student(request)
        if not student:
            return _err('Not authenticated', 401)

        if not is_feature_enabled(
            'exam.proctoring_snapshots', tenant=student.tenant, user_type='STUDENT',
        ):
            return JsonResponse({'ok': True, 'ignored': True})

        test, attempt = _get_test_and_attempt(student, test_id)
        if not attempt:
            return _err('No active attempt', 404)

        f = request.FILES.get('snapshot')
        if not f:
            return _err('snapshot file required')
        if f.size > SNAPSHOT_MAX_BYTES:
            return _err('Snapshot too large', 413)

        ext = SNAPSHOT_ALLOWED_MIME.get(f.content_type)
        if not ext:
            return _err('Unsupported content type', 415)

        ts = timezone.now().strftime('%Y%m%dT%H%M%S%f')
        rel_dir = Path('proctoring') / str(student.tenant_id) / str(attempt.id)
        abs_dir = Path(settings.MEDIA_ROOT) / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        rel_path = rel_dir / f'snap_{ts}.{ext}'
        abs_path = Path(settings.MEDIA_ROOT) / rel_path

        try:
            with open(abs_path, 'wb') as out:
                for chunk in f.chunks():
                    out.write(chunk)
        except OSError:
            logger.exception('failed writing proctor snapshot')
            return _err('Storage error', 500)

        log_exam_event(
            request=request,
            actor=student,
            action='PROCTOR_SNAPSHOT',
            resource_type='TestAttempt',
            resource_id=attempt.id,
            resource_name=test.test_code,
            description='webcam snapshot stored',
            severity='INFO',
            is_security_event=True,
            extra_meta={'path': str(rel_path), 'bytes': f.size},
        )

        return JsonResponse({'ok': True, 'path': str(rel_path)})


# ===========================================================================
# Submit
# ===========================================================================
class ExamSubmitView(View):
    """POST — finalise the attempt using the auto-saved answers."""

    def post(self, request, test_id):
        student = _require_student(request)
        if not student:
            return _err('Not authenticated', 401)

        test, attempt = _get_test_and_attempt(student, test_id)
        if not attempt:
            return _err('No active attempt', 404)

        try:
            _grade_now(request, test, attempt, auto=False)
        except Exception:
            logger.exception('exam submit grading failed')
            return _err('Grading failed', 500)

        log_exam_event(
            request=request,
            actor=student,
            action='EXAM_SUBMIT',
            resource_type='TestAttempt',
            resource_id=attempt.id,
            resource_name=test.test_code,
            description=f'student submitted {test.test_code}',
        )

        return JsonResponse({
            'ok': True,
            'redirect': reverse(
                'student-exam-result',
                kwargs={'test_id': test.id, 'attempt_id': attempt.id},
            ),
        })
