"""
Phase 5 — Feature 5: Teacher Offline Test Marks (Tests & Marks dashboard).

Covers:
  - Auth gate (non-teacher → redirect)
  - GET renders selectors when no batch/test chosen
  - GET with batch+test renders subject roster grid
  - POST creates one OfflineTestMarks row per (student, subject, test)
  - POST upserts (idempotent)
  - POST rejects out-of-range marks
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from accounts.models import Teacher, Student
from academics.models import AcademicSession, Batch, BatchTeacher, Subject
from assessments.models import OfflineTestMarks, Test, TestSection
from tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='OM_T', name='OM', subdomain='omt')


@pytest.fixture
def teacher(db, tenant):
    t = Teacher(
        tenant=tenant, email='om-tch@t.local', phone='9000000001',
        first_name='Om', last_name='Teacher',
        teacher_code='OMTCH1', status='ACTIVE',
    )
    t.set_password('x')
    t.save()
    return t


@pytest.fixture
def session_obj(db, tenant):
    from datetime import date
    return AcademicSession.objects.create(
        tenant=tenant, session_name='2025-26',
        start_date=date(2025, 6, 1), end_date=date(2026, 5, 31),
    )


@pytest.fixture
def batch(db, tenant, session_obj, teacher):
    b = Batch.objects.create(
        tenant=tenant, code='OM-B1', name='OM Batch',
        session=session_obj, status='ACTIVE',
    )
    BatchTeacher.objects.create(tenant=tenant, batch=b, teacher=teacher, is_primary=True)
    return b


@pytest.fixture
def students(db, tenant, batch):
    out = []
    for i in range(2):
        s = Student(
            tenant=tenant, email=f'om-stu{i}@t.local', phone=f'90909090{i:02d}',
            first_name=f'Stu{i}', last_name='X',
            student_code=f'OMSTU{i}', student_class='12', exam_target='JEE',
            city='X', state='Y', status='ACTIVE',
            batch=batch,
        )
        s.set_password('x')
        s.save()
        out.append(s)
    return out


@pytest.fixture
def subjects(db, tenant):
    phy = Subject.objects.create(tenant=tenant, code='PHY', name='Physics')
    chem = Subject.objects.create(tenant=tenant, code='CHEM', name='Chemistry')
    return [phy, chem]


@pytest.fixture
def test_obj(db, tenant, batch, subjects):
    t = Test.objects.create(
        tenant=tenant, test_code='OM-T1', title='Term I',
        test_type='OFFLINE', access_mode='BATCH_ONLY', status='PUBLISHED',
        total_questions=0, total_marks=Decimal('100'), total_duration_minutes=180,
        batch=batch,
    )
    TestSection.objects.create(
        tenant=tenant, test=t, subject=subjects[0], section_name='Phy',
        section_order=1, total_questions=0, max_marks=Decimal('50'),
    )
    TestSection.objects.create(
        tenant=tenant, test=t, subject=subjects[1], section_name='Chem',
        section_order=2, total_questions=0, max_marks=Decimal('50'),
    )
    return t


def _login_teacher(client, teacher):
    s = client.session
    s['user_type'] = 'TEACHER'
    s['user_id'] = str(teacher.id)
    s.save()


@pytest.mark.django_db
class TestTeacherOfflineMarks:
    URL = '/teacher/offline-marks/'

    def test_anonymous_redirect(self, client):
        r = client.get(self.URL)
        assert r.status_code in (301, 302)
        assert '/login/' in r['Location']

    def test_get_without_selection_renders_selectors(self, client, teacher, batch):
        _login_teacher(client, teacher)
        r = client.get(self.URL)
        assert r.status_code == 200
        assert b'OM Batch' in r.content

    def test_get_with_selection_renders_roster(self, client, teacher, batch,
                                                test_obj, students, subjects):
        _login_teacher(client, teacher)
        r = client.get(f'{self.URL}?batch={batch.id}&test={test_obj.id}')
        assert r.status_code == 200
        for s in students:
            assert s.first_name.encode() in r.content
        # Both subjects should appear in the header
        assert b'Physics' in r.content
        assert b'Chemistry' in r.content

    def test_post_creates_marks_per_subject(self, client, teacher, batch,
                                              test_obj, students, subjects):
        _login_teacher(client, teacher)
        # Per-subject max = 100/2 = 50
        data = {
            'batch': str(batch.id), 'test': str(test_obj.id),
            f'm_{students[0].id}_{subjects[0].id}': '45',
            f'm_{students[0].id}_{subjects[1].id}': '38',
            f'm_{students[1].id}_{subjects[0].id}': '20',
        }
        r = client.post(self.URL, data=data)
        assert r.status_code in (302, 200)
        rows = OfflineTestMarks.objects.filter(test=test_obj)
        assert rows.count() == 3
        rec = rows.get(student=students[0], subject=subjects[0])
        assert rec.marks_obtained == Decimal('45')
        assert rec.batch_id == batch.id

    def test_post_is_idempotent(self, client, teacher, batch,
                                  test_obj, students, subjects):
        _login_teacher(client, teacher)
        data1 = {'batch': str(batch.id), 'test': str(test_obj.id),
                 f'm_{students[0].id}_{subjects[0].id}': '30'}
        data2 = {'batch': str(batch.id), 'test': str(test_obj.id),
                 f'm_{students[0].id}_{subjects[0].id}': '42'}
        client.post(self.URL, data=data1)
        client.post(self.URL, data=data2)
        rows = OfflineTestMarks.objects.filter(
            test=test_obj, student=students[0], subject=subjects[0]
        )
        assert rows.count() == 1
        assert rows.first().marks_obtained == Decimal('42')

    def test_post_rejects_out_of_range(self, client, teacher, batch,
                                         test_obj, students, subjects):
        _login_teacher(client, teacher)
        # Per-subject max = 50, so 99 should be rejected
        data = {'batch': str(batch.id), 'test': str(test_obj.id),
                f'm_{students[0].id}_{subjects[0].id}': '99'}
        client.post(self.URL, data=data)
        assert not OfflineTestMarks.objects.filter(
            test=test_obj, student=students[0], subject=subjects[0]
        ).exists()
