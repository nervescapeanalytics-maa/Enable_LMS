"""
Phase 5 — Feature 6: Published-test visibility.

Covers:
  - Student: BATCH_ONLY tests are visible only to students in the batch
  - Student: OPEN tests are visible to any student in tenant
  - Teacher: TeacherPublishedTestsView returns ALL published tests in tenant
"""
from __future__ import annotations

import pytest

from accounts.models import Student, Teacher
from academics.models import AcademicSession, Batch, BatchTeacher, Subject
from assessments.models import Test
from core.student_exam_views import _visible_tests_qs
from tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='V_T', name='Visi', subdomain='visit')


@pytest.fixture
def session_obj(db, tenant):
    from datetime import date
    return AcademicSession.objects.create(
        tenant=tenant, session_name='2025-26',
        start_date=date(2025, 6, 1), end_date=date(2026, 5, 31),
    )


@pytest.fixture
def batches(db, tenant, session_obj):
    b1 = Batch.objects.create(tenant=tenant, code='V-B1', name='Vis B1',
                              session=session_obj, status='ACTIVE')
    b2 = Batch.objects.create(tenant=tenant, code='V-B2', name='Vis B2',
                              session=session_obj, status='ACTIVE')
    return b1, b2


@pytest.fixture
def students(db, tenant, batches):
    b1, b2 = batches
    s1 = Student(tenant=tenant, email='vs1@t.local', phone='9111111111',
                 first_name='S1', last_name='X', student_code='VS1',
                 student_class='12', exam_target='JEE', city='X', state='Y',
                 status='ACTIVE', batch=b1)
    s1.set_password('x'); s1.save()
    s2 = Student(tenant=tenant, email='vs2@t.local', phone='9222222222',
                 first_name='S2', last_name='X', student_code='VS2',
                 student_class='12', exam_target='JEE', city='X', state='Y',
                 status='ACTIVE', batch=b2)
    s2.set_password('x'); s2.save()
    return s1, s2


@pytest.fixture
def teacher(db, tenant, batches):
    t = Teacher(tenant=tenant, email='vis-tch@t.local', phone='9000000099',
                first_name='Vis', last_name='Tch', teacher_code='VTCH1',
                status='ACTIVE')
    t.set_password('x'); t.save()
    BatchTeacher.objects.create(tenant=tenant, batch=batches[0], teacher=t,
                                is_primary=True)
    return t


@pytest.fixture
def tests_setup(db, tenant, batches):
    b1, b2 = batches
    open_test = Test.objects.create(
        tenant=tenant, test_code='V-OPN', title='OpenTest',
        test_type='PRACTICE', access_mode='OPEN', status='PUBLISHED',
        total_questions=1, total_marks=1, total_duration_minutes=10,
    )
    b1_test = Test.objects.create(
        tenant=tenant, test_code='V-B1T', title='Batch1Test',
        test_type='PRACTICE', access_mode='BATCH_ONLY', status='PUBLISHED',
        total_questions=1, total_marks=1, total_duration_minutes=10,
        batch=b1,
    )
    b2_test = Test.objects.create(
        tenant=tenant, test_code='V-B2T', title='Batch2Test',
        test_type='PRACTICE', access_mode='BATCH_ONLY', status='PUBLISHED',
        total_questions=1, total_marks=1, total_duration_minutes=10,
        batch=b2,
    )
    return open_test, b1_test, b2_test


@pytest.mark.django_db
class TestStudentVisibility:
    def test_open_test_visible_to_all(self, students, tests_setup):
        s1, s2 = students
        open_test, b1_test, b2_test = tests_setup
        ids1 = set(_visible_tests_qs(s1).values_list('id', flat=True))
        ids2 = set(_visible_tests_qs(s2).values_list('id', flat=True))
        assert open_test.id in ids1
        assert open_test.id in ids2

    def test_batch_only_test_visible_to_batch_member(self, students, tests_setup):
        s1, s2 = students
        _, b1_test, b2_test = tests_setup
        ids1 = set(_visible_tests_qs(s1).values_list('id', flat=True))
        ids2 = set(_visible_tests_qs(s2).values_list('id', flat=True))
        assert b1_test.id in ids1
        assert b1_test.id not in ids2
        assert b2_test.id in ids2
        assert b2_test.id not in ids1


@pytest.mark.django_db
class TestTeacherVisibility:
    def test_teacher_sees_all_published(self, client, teacher, tests_setup):
        open_test, b1_test, b2_test = tests_setup
        s = client.session
        s['user_type'] = 'TEACHER'
        s['user_id'] = str(teacher.id)
        s.save()
        r = client.get('/teacher/published-tests/')
        assert r.status_code == 200
        body = r.content
        assert open_test.test_code.encode() in body
        assert b1_test.test_code.encode() in body
        # Even tests for batches the teacher doesn't teach must be listed
        assert b2_test.test_code.encode() in body
