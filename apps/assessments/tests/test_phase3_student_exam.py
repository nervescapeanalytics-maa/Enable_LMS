"""
Phase 3 — Student exam REST API tests.

Covers:
  - Auth (anonymous / non-student rejected)
  - Auto-save: create + update + change-count increment
  - Proctor event: feature-flag gating + threshold-triggered auto-submit
  - Snapshot upload: feature-flag gating + size/type enforcement
  - Submit: grades using auto-saved answers and creates audit log
"""
from __future__ import annotations

import io
import json
import uuid
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from accounts.models import Admin, Student, StaffRole  # noqa: F401
from assessments.models import Test, Question, TestAttempt, TestAttemptAnswer
from assessments.permissions import ensure_exam_feature_flags
from audit.models import AuditLog
from system_config.models import FeatureFlag
from tenants.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='T_P3', name='Phase3 Tenant', subdomain='tp3')


@pytest.fixture
def flags(db, tenant):
    ensure_exam_feature_flags()
    return list(FeatureFlag.objects.filter(flag_key__startswith='exam.'))


@pytest.fixture
def student(db, tenant):
    s = Student(
        tenant=tenant, email='stu@t.local', phone='9999911111',
        first_name='Stu', last_name='Dent',
        student_code='STU001', student_class='12', exam_target='JEE',
        city='X', state='Y', status='ACTIVE',
    )
    s.set_password('x')
    s.save()
    return s


@pytest.fixture
def published_test(db, tenant):
    t = Test.objects.create(
        tenant=tenant,
        test_code='P3T1', title='Phase 3 test',
        test_type='PRACTICE', access_mode='OPEN',
        status='PUBLISHED', total_questions=2, total_marks=2,
        total_duration_minutes=30,
        passing_percent=33,
    )
    Question.objects.create(
        tenant=tenant, test=t, question_code='Q1',
        question_text='2+2?', question_type='MCQ_SINGLE',
        option_a='3', option_b='4', option_c='5', option_d='6',
        correct_answer='B', positive_marks=1, negative_marks=0,
        question_order=1,
    )
    Question.objects.create(
        tenant=tenant, test=t, question_code='Q2',
        question_text='Capital of FR?', question_type='MCQ_SINGLE',
        option_a='Berlin', option_b='Madrid', option_c='Paris', option_d='Rome',
        correct_answer='C', positive_marks=1, negative_marks=0,
        question_order=2,
    )
    return t


@pytest.fixture
def attempt(db, tenant, student, published_test):
    return TestAttempt.objects.create(
        tenant=tenant, test=published_test, student=student,
        attempt_number=1, started_at=timezone.now(),
        total_questions=2, status='IN_PROGRESS',
    )


def _login_student(client, student):
    s = client.session
    s['user_type'] = 'STUDENT'
    s['user_id'] = str(student.id)
    s['user_name'] = student.first_name
    s.save()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuth:
    def test_anonymous_rejected(self, client, published_test):
        url = f'/student/exams/{published_test.id}/api/answer/'
        r = client.post(url, data='{}', content_type='application/json')
        assert r.status_code == 401

    def test_admin_rejected(self, client, published_test):
        s = client.session
        s['user_type'] = 'ADMIN'; s['user_id'] = str(uuid.uuid4()); s.save()
        url = f'/student/exams/{published_test.id}/api/submit/'
        r = client.post(url, data='{}', content_type='application/json')
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auto-save
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutoSave:
    def test_create_then_update(self, client, student, published_test, attempt):
        _login_student(client, student)
        q = Question.objects.filter(test=published_test, question_order=1).first()
        url = f'/student/exams/{published_test.id}/api/answer/'

        r1 = client.post(url, data=json.dumps({'question_id': str(q.id), 'answer': 'A'}),
                         content_type='application/json')
        assert r1.status_code == 200 and r1.json()['ok']
        a = TestAttemptAnswer.objects.get(attempt=attempt, question=q)
        assert a.student_answer == 'A'
        assert a.status == 'ANSWERED'
        assert a.first_answered_at is not None

        r2 = client.post(url, data=json.dumps({'question_id': str(q.id), 'answer': 'B'}),
                         content_type='application/json')
        assert r2.status_code == 200
        a.refresh_from_db()
        assert a.student_answer == 'B'
        assert a.answer_change_count == 1

    def test_unknown_question(self, client, student, published_test, attempt):
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/answer/'
        r = client.post(url, data=json.dumps({'question_id': str(uuid.uuid4()), 'answer': 'A'}),
                        content_type='application/json')
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Proctor events
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProctorEvent:
    def test_unknown_event(self, client, student, published_test, attempt, flags):
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/proctor-event/'
        r = client.post(url, data=json.dumps({'event_type': 'BOGUS'}),
                        content_type='application/json')
        assert r.status_code == 400

    def test_tab_switch_increments_and_audits(self, client, student, published_test, attempt, flags):
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/proctor-event/'
        r = client.post(url, data=json.dumps({'event_type': 'TAB_SWITCH'}),
                        content_type='application/json')
        assert r.status_code == 200
        attempt.refresh_from_db()
        assert attempt.tab_switch_count == 1
        assert AuditLog.objects.filter(
            resource_type='TestAttempt', resource_id=str(attempt.id),
            is_security_event=True,
        ).exists()

    def test_threshold_triggers_auto_submit(self, client, student, published_test, attempt, flags):
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/proctor-event/'
        last = None
        for _ in range(5):  # TAB_SWITCH_LIMIT
            last = client.post(url, data=json.dumps({'event_type': 'TAB_SWITCH'}),
                               content_type='application/json')
        assert last.json().get('auto_submitted') is True
        attempt.refresh_from_db()
        assert attempt.auto_terminated is True
        assert attempt.status == 'AUTO_SUBMITTED'

    def test_disabled_flag_ignored(self, client, student, published_test, attempt, flags):
        FeatureFlag.objects.filter(flag_key='exam.copy_paste_block').update(is_enabled=False)
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/proctor-event/'
        r = client.post(url, data=json.dumps({'event_type': 'COPY'}),
                        content_type='application/json')
        assert r.status_code == 200
        assert r.json().get('ignored') is True
        attempt.refresh_from_db()
        assert attempt.copy_paste_attempts == 0


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSnapshot:
    def _jpeg(self, n=64):
        # Minimal binary blob; backend doesn't decode it.
        return io.BytesIO(b'\xff\xd8\xff\xe0' + b'\x00' * n + b'\xff\xd9')

    def test_upload_ok(self, client, student, published_test, attempt, flags, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/snapshot/'
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('snap.jpg', self._jpeg().getvalue(), content_type='image/jpeg')
        r = client.post(url, data={'snapshot': f})
        assert r.status_code == 200, r.content
        assert r.json()['ok'] is True
        rel = r.json()['path']
        assert (tmp_path / rel).exists()

    def test_upload_disabled_flag_silent(self, client, student, published_test, attempt, flags):
        FeatureFlag.objects.filter(flag_key='exam.proctoring_snapshots').update(is_enabled=False)
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/snapshot/'
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('snap.jpg', b'x', content_type='image/jpeg')
        r = client.post(url, data={'snapshot': f})
        assert r.status_code == 200
        assert r.json().get('ignored') is True

    def test_unsupported_type(self, client, student, published_test, attempt, flags):
        _login_student(client, student)
        url = f'/student/exams/{published_test.id}/api/snapshot/'
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('x.gif', b'GIF89a', content_type='image/gif')
        r = client.post(url, data={'snapshot': f})
        assert r.status_code == 415


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubmit:
    def test_submit_grades_from_autosaved_answers(self, client, student, published_test, attempt):
        _login_student(client, student)
        # Auto-save two answers (one correct, one wrong)
        ans_url = f'/student/exams/{published_test.id}/api/answer/'
        q1 = Question.objects.get(test=published_test, question_order=1)
        q2 = Question.objects.get(test=published_test, question_order=2)
        client.post(ans_url, data=json.dumps({'question_id': str(q1.id), 'answer': 'B'}),
                    content_type='application/json')   # correct
        client.post(ans_url, data=json.dumps({'question_id': str(q2.id), 'answer': 'A'}),
                    content_type='application/json')   # wrong

        sub_url = f'/student/exams/{published_test.id}/api/submit/'
        r = client.post(sub_url, data='{}', content_type='application/json')
        assert r.status_code == 200, r.content
        body = r.json()
        assert body['ok'] is True
        assert body['redirect'].startswith(f'/student/exams/{published_test.id}/result/')

        attempt.refresh_from_db()
        assert attempt.status == 'EVALUATED'
        assert attempt.correct == 1
        assert attempt.incorrect == 1
        assert attempt.percentage == Decimal('50.00')
        assert attempt.result == 'PASS'  # passing_percent is 33

        assert AuditLog.objects.filter(
            resource_type='TestAttempt', resource_id=str(attempt.id),
            action='EXAM_SUBMIT',
        ).exists()
