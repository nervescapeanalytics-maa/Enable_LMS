"""
Phase 5 — Feature 3: Student post-submit feedback API.

Covers:
  - Anonymous → 401
  - Empty payload → 400
  - First submit → 200, FeedbackTest row created
  - Re-submit (same student/test/attempt) → updates row in place (idempotent)
  - Audit log entry written
"""
from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import Student
from assessments.models import Test, TestAttempt, TestFeedback
from audit.models import AuditLog
from tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='FB_T1', name='FBT', subdomain='fbt')


@pytest.fixture
def student(db, tenant):
    s = Student(
        tenant=tenant, email='fbstu@t.local', phone='9090909090',
        first_name='FB', last_name='Stu', student_code='FBSTU1',
        student_class='12', exam_target='JEE', city='X', state='Y',
        status='ACTIVE',
    )
    s.set_password('x')
    s.save()
    return s


@pytest.fixture
def test_obj(db, tenant):
    return Test.objects.create(
        tenant=tenant, test_code='FBT01', title='FB test',
        test_type='PRACTICE', access_mode='OPEN', status='PUBLISHED',
        total_questions=1, total_marks=1, total_duration_minutes=10,
    )


@pytest.fixture
def attempt(db, tenant, test_obj, student):
    return TestAttempt.objects.create(
        tenant=tenant, test=test_obj, student=student,
        attempt_number=1,
        started_at=timezone.now() - timedelta(minutes=15),
        submitted_at=timezone.now(),
        total_questions=1, status='SUBMITTED',
    )


def _login(client, student):
    s = client.session
    s['user_type'] = 'STUDENT'
    s['user_id'] = str(student.id)
    s.save()


@pytest.mark.django_db
class TestFeedbackAPI:
    def test_anonymous_rejected(self, client, test_obj):
        url = f'/student/exams/{test_obj.id}/api/feedback/'
        r = client.post(url, data='{}', content_type='application/json')
        assert r.status_code == 401

    def test_empty_payload_rejected(self, client, test_obj, student):
        _login(client, student)
        url = f'/student/exams/{test_obj.id}/api/feedback/'
        r = client.post(url, data=json.dumps({}), content_type='application/json')
        assert r.status_code == 400

    def test_first_submit_creates_row(self, client, test_obj, student, attempt):
        _login(client, student)
        url = f'/student/exams/{test_obj.id}/api/feedback/'
        payload = {
            'overall_rating': 5, 'difficulty_rating': 3, 'clarity_rating': 4,
            'comments': 'Great test!', 'attempt_id': str(attempt.id),
        }
        r = client.post(url, data=json.dumps(payload), content_type='application/json')
        assert r.status_code == 200
        body = r.json()
        assert body['ok'] is True
        assert body['created'] is True
        fb = TestFeedback.objects.get(test=test_obj, student=student, attempt=attempt)
        assert fb.overall_rating == 5
        assert fb.comments == 'Great test!'

    def test_resubmit_updates_in_place(self, client, test_obj, student, attempt):
        _login(client, student)
        url = f'/student/exams/{test_obj.id}/api/feedback/'
        payload1 = {'overall_rating': 2, 'comments': 'meh', 'attempt_id': str(attempt.id)}
        payload2 = {'overall_rating': 4, 'comments': 'better!', 'attempt_id': str(attempt.id)}
        r1 = client.post(url, data=json.dumps(payload1), content_type='application/json')
        r2 = client.post(url, data=json.dumps(payload2), content_type='application/json')
        assert r1.status_code == 200 and r2.status_code == 200
        assert r2.json()['created'] is False
        assert TestFeedback.objects.filter(
            test=test_obj, student=student, attempt=attempt
        ).count() == 1
        fb = TestFeedback.objects.get(test=test_obj, student=student, attempt=attempt)
        assert fb.overall_rating == 4
        assert fb.comments == 'better!'

    def test_audit_log_written(self, client, test_obj, student, attempt):
        _login(client, student)
        url = f'/student/exams/{test_obj.id}/api/feedback/'
        client.post(url, data=json.dumps({'overall_rating': 5}),
                    content_type='application/json')
        assert AuditLog.objects.filter(
            resource_type='Test', resource_id=str(test_obj.id),
        ).exists()
