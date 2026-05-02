"""
Student Exam Portal — server-rendered Django views.

Provides a clean, robust test-taking workflow for students:

    /student/exams/                         List of available tests
    /student/exams/<test_id>/               Test intro page (rules, instructions)
    /student/exams/<test_id>/take/          Render question form  (GET)
                                             Submit + auto-grade   (POST)
    /student/exams/<test_id>/result/<aid>/  Result page with breakdown

Auth: requires session['user_type'] == 'STUDENT' and session['user_id']
      to be a valid Student.id (set by frontend_views.LoginView).

Data flow (admin → student):
    Teacher/Admin creates a Test in /admin/assessments/test/  →
    sets status=PUBLISHED, start_datetime, end_datetime  →
    student dashboard pulls Test.objects.filter(
        tenant=student.tenant,
        status='PUBLISHED',
        is_deleted=False,
        start_datetime__lte=now,
        end_datetime__gte=now,
    ) — visible immediately, no caching.

Auto-grading:
    On POST submit, iterate each Question in the Test, compare student_answer
    (case-insensitive single letter A/B/C/D/E for MCQ_SINGLE) with
    Question.correct_answer.  Apply Question.positive_marks if correct,
    Question.negative_marks if incorrect, 0 if skipped.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction, models
from django.db.models import Avg, Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import Student
from academics.models import Users
from assessments.models import (
    OfflineTestMarks,
    Question,
    Test,
    TestAttempt,
    TestAttemptAnswer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
def _require_student(request) -> Optional[Student]:
    """Return the logged-in Student or None."""
    if request.session.get('user_type') != 'STUDENT':
        return None
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Student.objects.select_related('tenant', 'batch').get(id=user_id)
    except (Student.DoesNotExist, ValueError):
        return None


def _student_batch_ids(student: Student) -> list:
    """All Batch UUIDs the student belongs to (primary + Users enrolments)."""
    ids = set()
    if student.batch_id:
        ids.add(student.batch_id)
    enrolled = Users.objects.filter(
        student_id=student.id, is_active=True
    ).values_list('batch_id', flat=True)
    ids.update(b for b in enrolled if b)
    return list(ids)


# ---------------------------------------------------------------------------
# Querysets
# ---------------------------------------------------------------------------
def _visible_tests_qs(student: Student):
    """
    Tests the student is permitted to see.

    Visibility rules:
      - tenant match (mandatory)
      - status = PUBLISHED or ACTIVE
      - not soft-deleted
      - now ∈ [start_datetime, end_datetime]  (or no schedule set → always open)
      - access_mode = OPEN  →  visible to all in tenant
        access_mode = BATCH_ONLY → batch_id in student's batches OR no batch (legacy)
        access_mode = SCHEDULED  → same as OPEN, scheduling already enforced
        access_mode = PASSWORD   → visible (password validated at start)
      - chapter.class_level matches student's student_class (if both set)
    """
    now = timezone.now()
    batch_ids = _student_batch_ids(student)

    qs = Test.objects.filter(
        tenant=student.tenant,
        is_deleted=False,
        status__in=['PUBLISHED', 'ACTIVE'],
    ).select_related('subject', 'chapter', 'teacher')

    # Schedule window: open if no schedule, else now must be inside window
    qs = qs.filter(
        Q(start_datetime__isnull=True) | Q(start_datetime__lte=now)
    ).filter(
        Q(end_datetime__isnull=True) | Q(end_datetime__gte=now)
    )

    # Access mode
    access_q = (
        Q(access_mode='OPEN')
        | Q(access_mode='SCHEDULED')
        | Q(access_mode='PASSWORD')
        | Q(access_mode='BATCH_ONLY', batch_id__in=batch_ids)
        | Q(access_mode='BATCH_ONLY', batch__isnull=True)
    )
    qs = qs.filter(access_q)

    # Class level match (only if student has class set AND chapter has class_level set)
    if student.student_class:
        qs = qs.filter(
            Q(chapter__isnull=True)
            | Q(chapter__class_level__isnull=True)
            | Q(chapter__class_level='')
            | Q(chapter__class_level=str(student.student_class))
        )

    return qs.order_by('-start_datetime', '-published_at', '-created_at')


def _student_attempts(student: Student, test: Test):
    return TestAttempt.objects.filter(test=test, student=student).order_by('-attempt_number')


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class ExamListView(View):
    """List published tests + the student's own attempts."""

    template_name = 'student/exam_list.html'

    def get(self, request):
        student = _require_student(request)
        if not student:
            return redirect('/login/?role=student')

        tests = list(_visible_tests_qs(student))

        # Annotate each test with student's most-recent attempt status
        attempts_by_test = {
            a.test_id: a
            for a in TestAttempt.objects.filter(
                student=student, test__in=tests
            ).order_by('-started_at')
        }

        rows = []
        for t in tests:
            attempt = attempts_by_test.get(t.id)
            attempts_used = TestAttempt.objects.filter(
                student=student, test=t
            ).count()
            rows.append({
                'test': t,
                'attempt': attempt,
                'attempts_used': attempts_used,
                'attempts_remaining': max(t.max_attempts - attempts_used, 0),
                'subject_name': t.subject.name if t.subject else '—',
                'chapter_name': t.chapter.name if t.chapter else '—',
                'class_level': t.chapter.class_level if t.chapter else '',
                'can_start': attempts_used < t.max_attempts,
            })

        # Past results (any evaluated attempts)
        past_qs = (
            TestAttempt.objects
            .filter(student=student, status__in=['EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'])
            .select_related('test', 'test__subject')
            .order_by('-submitted_at')
        )
        past = list(past_qs[:20])
        pass_count = past_qs.filter(result='PASS').count()
        avg = past_qs.aggregate(a=Avg('percentage'))['a'] or 0
        avg_pct = round(float(avg), 1) if avg else 0
        # Best score % across all evaluated attempts
        best_pct = past_qs.aggregate(b=models.Max('percentage'))['b'] if past_qs.exists() else None
        try:
            best_pct = round(float(best_pct), 1) if best_pct is not None else 0
        except (TypeError, ValueError):
            best_pct = 0
        # Upcoming = visible tests that haven't started yet OR not attempted yet
        upcoming_count = sum(1 for r in rows if r['attempts_used'] == 0)

        # Split rows into "Upcoming" (not yet attempted) vs "Exams Taken"
        upcoming_rows = [r for r in rows if r['attempts_used'] == 0]
        # Sort by start_datetime ascending so soonest is first
        upcoming_rows.sort(
            key=lambda r: (r['test'].start_datetime is None,
                           r['test'].start_datetime or timezone.now())
        )
        # Reminder banner: tests starting within next 48 hours
        soon_cutoff = timezone.now() + __import__('datetime').timedelta(hours=48)
        upcoming_soon = [
            r for r in upcoming_rows
            if r['test'].start_datetime and r['test'].start_datetime <= soon_cutoff
        ]

        return render(request, self.template_name, {
            'rows': rows,
            'upcoming_rows': upcoming_rows,
            'upcoming_soon': upcoming_soon,
            'past': past,
            'pass_count': pass_count,
            'avg_pct': avg_pct,
            'best_pct': best_pct,
            'upcoming_count': len(upcoming_rows),
            'tests_taken': past_qs.count(),
            'student': student,
            'user_name': f"{student.first_name} {student.last_name}",
            'now': timezone.now(),
        })


class ExamTakeView(View):
    """
    GET  → starts (or resumes) an attempt and renders the question form.
    POST → grades the submission and redirects to the result page.
    """

    template_name = 'student/exam_take.html'

    def get(self, request, test_id):
        student = _require_student(request)
        if not student:
            return redirect('/login/?role=student')

        test = get_object_or_404(
            Test.objects.select_related('subject', 'chapter'),
            id=test_id, tenant=student.tenant, is_deleted=False,
        )

        # Eligibility check
        if test not in _visible_tests_qs(student):
            return render(request, 'student/exam_blocked.html', {
                'student': student,
                'test': test,
                'reason': 'This test is not currently available for you.',
            }, status=403)

        # Resume any IN_PROGRESS attempt, else start a fresh one
        attempt = TestAttempt.objects.filter(
            test=test, student=student, status='IN_PROGRESS',
        ).order_by('-started_at').first()

        if not attempt:
            used = TestAttempt.objects.filter(test=test, student=student).count()
            if used >= test.max_attempts:
                return render(request, 'student/exam_blocked.html', {
                    'student': student,
                    'test': test,
                    'reason': f'You have used all {test.max_attempts} attempt(s) for this test.',
                }, status=403)

            with transaction.atomic():
                attempt = TestAttempt.objects.create(
                    tenant=student.tenant,
                    test=test,
                    student=student,
                    attempt_number=used + 1,
                    started_at=timezone.now(),
                    total_questions=test.total_questions,
                    status='IN_PROGRESS',
                    ip_address=_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )

        questions = list(
            Question.objects.filter(test=test, is_deleted=False)
            .order_by('question_order', 'question_code')
        )

        # Existing answers for resume
        prior = {
            str(a.question_id): (a.student_answer or '').upper()
            for a in TestAttemptAnswer.objects.filter(attempt=attempt)
        }

        # Build template-friendly question rows with pre-resolved options + selection
        q_rows = []
        for idx, q in enumerate(questions, start=1):
            opts = []
            for letter in ('A', 'B', 'C', 'D', 'E'):
                text = getattr(q, f'option_{letter.lower()}', None)
                if text:
                    opts.append({
                        'letter': letter,
                        'text': text,
                        'checked': prior.get(str(q.id)) == letter,
                    })
            q_rows.append({
                'q': q,
                'index': idx,
                'options': opts,
            })

        # Time remaining (seconds)
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        remaining = max(int(test.total_duration_minutes * 60 - elapsed), 0)

        # If time is up, auto-submit
        if remaining == 0 and attempt.status == 'IN_PROGRESS':
            return self._auto_submit(request, attempt, test, questions, prior)

        # Phase 3 — proctoring / online-exam feature flags (per-tenant).
        # Keys are bare identifiers so Django templates can resolve them
        # via dotted lookup (`feature_flags.tab_switch`).
        from assessments.permissions import is_feature_enabled
        _ff = lambda k: is_feature_enabled(k, tenant=student.tenant, user_type='STUDENT')
        feature_flags = {
            'tab_switch': _ff('exam.tab_switch_detection'),
            'copy_paste': _ff('exam.copy_paste_block'),
            'fullscreen': _ff('exam.fullscreen_lockdown'),
            'devtools':   _ff('exam.devtools_detection'),
            'snapshot':   _ff('exam.proctoring_snapshots'),
            'identity':   _ff('exam.identity_verification'),
        }

        return render(request, self.template_name, {
            'student': student,
            'user_name': f"{student.first_name} {student.last_name}",
            'test': test,
            'attempt': attempt,
            'questions': questions,
            'q_rows': q_rows,
            'remaining_seconds': remaining,
            'feature_flags': feature_flags,
        })

    def post(self, request, test_id):
        student = _require_student(request)
        if not student:
            return redirect('/login/?role=student')

        test = get_object_or_404(
            Test.objects.select_related('subject', 'chapter'),
            id=test_id, tenant=student.tenant, is_deleted=False,
        )

        attempt = TestAttempt.objects.filter(
            test=test, student=student, status='IN_PROGRESS',
        ).order_by('-started_at').first()
        if not attempt:
            return redirect('student-exam-list')

        questions = list(
            Question.objects.filter(test=test, is_deleted=False)
            .order_by('question_order', 'question_code')
        )

        return self._grade_and_submit(request, attempt, test, questions, request.POST)

    # ------------------------------------------------------------------
    def _auto_submit(self, request, attempt, test, questions, prior):
        """Time-up auto-submit: save existing answers, mark AUTO_SUBMITTED."""
        post_like = {f'q_{qid}': ans for qid, ans in prior.items()}
        return self._grade_and_submit(
            request, attempt, test, questions, post_like, auto=True,
        )

    def _grade_and_submit(self, request, attempt, test, questions, posted, auto=False):
        now = timezone.now()
        correct = 0
        incorrect = 0
        skipped = 0
        raw_score = Decimal('0.00')

        with transaction.atomic():
            for q in questions:
                key = f'q_{q.id}'
                # posted may be a QueryDict (POST) or plain dict (auto-submit replay)
                if hasattr(posted, 'get'):
                    raw_ans = posted.get(key, '')
                else:
                    raw_ans = posted.get(key, '')
                ans = (raw_ans or '').strip().upper()[:50]

                if not ans:
                    status_val = 'SKIPPED'
                    is_correct = False
                    marks = Decimal('0.00')
                    skipped += 1
                else:
                    expected = (q.correct_answer or '').strip().upper()
                    is_correct = ans == expected
                    if is_correct:
                        marks = Decimal(q.positive_marks or 0)
                        correct += 1
                    else:
                        marks = Decimal(q.negative_marks or 0)
                        incorrect += 1
                    status_val = 'ANSWERED'

                raw_score += marks

                TestAttemptAnswer.objects.update_or_create(
                    attempt=attempt, question=q,
                    defaults={
                        'tenant': attempt.tenant,
                        'student_answer': ans or None,
                        'status': status_val,
                        'is_correct': is_correct if ans else None,
                        'marks_awarded': marks,
                        'last_answered_at': now if ans else None,
                    },
                )

            attempted = correct + incorrect
            total_marks = Decimal(test.total_marks or 0) or Decimal(
                sum((q.positive_marks or 0) for q in questions)
            )
            percentage = (
                (raw_score / total_marks * 100) if total_marks > 0 else Decimal('0')
            )
            percentage = max(percentage, Decimal('0'))  # never negative
            passing = Decimal(test.passing_percent or 33)
            result = 'PASS' if percentage >= passing else 'FAIL'

            attempt.submitted_at = now
            attempt.time_taken_seconds = int(
                (now - attempt.started_at).total_seconds()
            )
            attempt.attempted = attempted
            attempt.correct = correct
            attempt.incorrect = incorrect
            attempt.skipped = skipped
            attempt.raw_score = raw_score
            attempt.total_marks = total_marks
            attempt.percentage = round(percentage, 2)
            attempt.result = result
            attempt.status = 'AUTO_SUBMITTED' if auto else 'EVALUATED'
            attempt.save()

        return redirect(
            reverse('student-exam-result',
                    kwargs={'test_id': test.id, 'attempt_id': attempt.id})
            + '?submitted=1'
        )


class ExamResultView(View):
    template_name = 'student/exam_result.html'

    def get(self, request, test_id, attempt_id):
        student = _require_student(request)
        if not student:
            return redirect('/login/?role=student')

        attempt = get_object_or_404(
            TestAttempt.objects.select_related('test', 'test__subject', 'test__chapter'),
            id=attempt_id, student=student, test_id=test_id,
        )
        test = attempt.test

        answers = (
            TestAttemptAnswer.objects
            .filter(attempt=attempt)
            .select_related('question', 'question__subject', 'question__topic', 'question__section')
            .order_by('question__question_order')
        )

        rows = []
        for a in answers:
            rows.append({
                'question': a.question,
                'student_answer': a.student_answer or '—',
                'correct_answer': a.question.correct_answer,
                'is_correct': a.is_correct,
                'marks_awarded': a.marks_awarded,
                'status': a.status,
            })

        # ── Percentile + rank computation across the cohort ──
        cohort = (
            TestAttempt.objects
            .filter(test=test, status__in=['EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'])
            .exclude(percentage__isnull=True)
        )
        cohort_size = cohort.count()
        percentile = None
        rank = attempt.rank
        if cohort_size > 1 and attempt.percentage is not None:
            below = cohort.filter(percentage__lt=attempt.percentage).count()
            percentile = round((below / cohort_size) * 100, 1)
            if rank is None:
                rank = cohort.filter(percentage__gt=attempt.percentage).count() + 1

        # ── AI-style performance insights (heuristic, no LLM) ──
        ai_insights = _compute_ai_insights(attempt, rows, test, percentile)

        # Feedback popup logic — auto-show on first visit if nothing submitted yet
        existing_feedback = self._existing_feedback(test, student, attempt)
        show_feedback_popup = (
            request.GET.get('submitted') == '1'
            and existing_feedback is None
        )

        return render(request, self.template_name, {
            'student': student,
            'user_name': f"{student.first_name} {student.last_name}",
            'test': test,
            'attempt': attempt,
            'rows': rows,
            'show_solutions': bool(test.show_correct_answers),
            'existing_feedback': existing_feedback,
            'feedback_just_saved': request.GET.get('feedback') == 'ok',
            'show_feedback_popup': show_feedback_popup,
            'cohort_size': cohort_size,
            'percentile': percentile,
            'rank': rank,
            'ai_insights': ai_insights,
        })

    @staticmethod
    def _existing_feedback(test, student, attempt):
        from assessments.models import TestFeedback
        return (
            TestFeedback.objects
            .filter(test=test, student=student, attempt=attempt)
            .first()
            or TestFeedback.objects
            .filter(test=test, student=student, attempt__isnull=True)
            .first()
        )


# ---------------------------------------------------------------------------
# AI-style performance insights — heuristic, deterministic, no LLM call.
# Returns a dict with: tone, headline, message, subject_breakdown, weak_topics,
# strong_topics, roadmap (list of action items), accuracy, time_pressure.
# ---------------------------------------------------------------------------
def _compute_ai_insights(attempt, rows, test, percentile):
    pct = float(attempt.percentage or 0)
    passed = (attempt.result == 'PASS')

    # Per-subject + per-topic accuracy buckets
    subj = {}
    topic = {}
    for r in rows:
        q = r['question']
        s_name = q.subject.name if q.subject else 'General'
        t_name = q.topic.name if q.topic else (q.chapter.name if q.chapter else 'General')
        subj.setdefault(s_name, {'total': 0, 'correct': 0})
        topic.setdefault(t_name, {'total': 0, 'correct': 0})
        subj[s_name]['total'] += 1
        topic[t_name]['total'] += 1
        if r['is_correct']:
            subj[s_name]['correct'] += 1
            topic[t_name]['correct'] += 1

    def _pct(d):
        return round((d['correct'] / d['total']) * 100, 1) if d['total'] else 0

    subject_breakdown = sorted(
        ({'name': k, 'total': v['total'], 'correct': v['correct'], 'pct': _pct(v)}
         for k, v in subj.items()),
        key=lambda x: x['pct'], reverse=True,
    )
    topic_list = [
        {'name': k, 'total': v['total'], 'correct': v['correct'], 'pct': _pct(v)}
        for k, v in topic.items() if v['total'] >= 1
    ]
    weak_topics = sorted([t for t in topic_list if t['pct'] < 50],
                         key=lambda x: x['pct'])[:5]
    strong_topics = sorted([t for t in topic_list if t['pct'] >= 75],
                           key=lambda x: x['pct'], reverse=True)[:5]

    # Time pressure: did the student rush or spend extra?
    duration_s = (test.total_duration_minutes or 0) * 60
    taken_s = attempt.time_taken_seconds or 0
    time_pressure = None
    if duration_s and taken_s:
        ratio = taken_s / duration_s
        if ratio < 0.5:
            time_pressure = 'You finished in less than half the time — re-read questions before answering.'
        elif ratio > 0.95:
            time_pressure = 'You used nearly the full time — practice timed mocks to improve speed.'

    # Tone + headline (psychology-driven messaging)
    if passed and pct >= 85:
        tone = 'celebrate'
        headline = '🌟 Outstanding! You’ve mastered these concepts.'
        message = ('Top-tier performance. Keep this momentum — '
                   'tackle harder mocks and aim for full-length papers next.')
    elif passed:
        tone = 'positive'
        headline = '✅ Great job! You cleared the test.'
        message = ('Solid pass. Polish your weak topics below and you’ll '
                   'jump into the high-percentile band soon.')
    elif pct >= 50:
        tone = 'supportive'
        headline = '💪 You’re almost there!'
        message = ('You’re close to the cut-off. Focus on the topics flagged '
                   'below — small targeted practice will tip you over.')
    elif pct >= 25:
        tone = 'supportive'
        headline = '📚 Keep going — every attempt counts.'
        message = ('Build foundations first. Spend a focused week on the '
                   'weak topics below before retaking this test.')
    else:
        tone = 'encourage'
        headline = '🌱 Start with the basics — you’ve got this.'
        message = ('Review concept videos for the weak topics, then attempt '
                   'an easier practice test to build confidence.')

    # Roadmap (deterministic action plan)
    roadmap = []
    for w in weak_topics[:3]:
        roadmap.append({
            'icon': 'fa-bullseye',
            'title': f'Practice 10 questions on "{w["name"]}"',
            'detail': f'Current accuracy {w["pct"]}% — target 75%+',
        })
    if attempt.skipped and attempt.skipped > 0:
        roadmap.append({
            'icon': 'fa-clock',
            'title': f'Reduce skipped questions ({attempt.skipped} left blank)',
            'detail': 'Even a guess on MCQs improves expected score.',
        })
    if percentile is not None and percentile < 50:
        roadmap.append({
            'icon': 'fa-chart-line',
            'title': 'Take 3 timed practice tests this week',
            'detail': f'You are at {percentile} percentile — sustained practice moves you up fast.',
        })
    if not roadmap:
        roadmap.append({
            'icon': 'fa-trophy',
            'title': 'Attempt a harder mock to push your ceiling',
            'detail': 'Your fundamentals are solid — challenge yourself.',
        })

    return {
        'tone': tone,
        'headline': headline,
        'message': message,
        'percentage': pct,
        'subject_breakdown': subject_breakdown,
        'weak_topics': weak_topics,
        'strong_topics': strong_topics,
        'roadmap': roadmap,
        'time_pressure': time_pressure,
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
