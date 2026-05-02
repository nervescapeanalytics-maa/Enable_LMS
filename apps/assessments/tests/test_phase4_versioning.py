"""
Phase 4 — versioning unit + integration tests.

Covers:
  - take_snapshot: version_number increments, summary correct, snapshot shape
  - take_snapshot: twice → v1, v2 with distinct numbers
  - restore_version: test fields rolled back, sections reconciled, extra
    questions soft-deleted (not hard-deleted)
  - diff_versions: identical snapshots → empty diffs; changed title → detected
  - audit log written on snapshot and restore
"""
from __future__ import annotations

import pytest

from accounts.models import Admin
from assessments.models import Question, Test, TestSection, TestVersion
from assessments.versioning import diff_versions, restore_version, take_snapshot
from audit.models import AuditLog
from tenants.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='TV_T1', name='Version Tenant', subdomain='tv1')


@pytest.fixture
def admin_user(db, tenant):
    a = Admin(
        tenant=tenant, email='adm@tv.local', phone='9000000001',
        first_name='Admin', last_name='V', admin_type='SUPER_ADMIN', status='ACTIVE',
    )
    a.set_password('x')
    a.save()
    return a


@pytest.fixture
def test_obj(db, tenant):
    t = Test.objects.create(
        tenant=tenant, test_code='VT1', title='Version Test 1',
        test_type='PRACTICE', access_mode='OPEN', status='DRAFT',
        total_questions=2, total_marks=10, total_duration_minutes=30,
        passing_percent=40,
    )
    s = TestSection.objects.create(
        tenant=tenant, test=t, section_name='Physics', section_order=1,
        total_questions=2, max_marks=10,
    )
    Question.objects.create(
        tenant=tenant, test=t, section=s,
        question_code='VQ1', question_text='Q1?', question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', positive_marks=5, negative_marks=0,
        question_order=1, is_active=True,
    )
    Question.objects.create(
        tenant=tenant, test=t, section=s,
        question_code='VQ2', question_text='Q2?', question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='B', positive_marks=5, negative_marks=0,
        question_order=2, is_active=True,
    )
    return t


# ---------------------------------------------------------------------------
# take_snapshot
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_take_snapshot_creates_version(test_obj, admin_user):
    v = take_snapshot(test_obj, actor=admin_user, label='initial')
    assert v.version_number == 1
    assert v.label == 'initial'
    assert v.tenant == test_obj.tenant
    assert v.test == test_obj
    assert 'test' in v.snapshot
    assert 'sections' in v.snapshot
    assert 'questions' in v.snapshot
    assert len(v.snapshot['questions']) == 2


@pytest.mark.django_db
def test_take_snapshot_summary_fields(test_obj, admin_user):
    v = take_snapshot(test_obj, actor=admin_user)
    assert v.summary['sections'] == 1
    assert v.summary['questions'] == 2
    assert '10' in v.summary['total_marks']


@pytest.mark.django_db
def test_take_snapshot_increments(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user, label='v1')
    v2 = take_snapshot(test_obj, actor=admin_user, label='v2')
    assert v2.version_number == v1.version_number + 1


@pytest.mark.django_db
def test_take_snapshot_writes_audit(test_obj, admin_user):
    take_snapshot(test_obj, actor=admin_user)
    assert AuditLog.objects.filter(
        action='VERSION_SNAPSHOT',
        resource_id=str(test_obj.id),
    ).exists()


@pytest.mark.django_db
def test_take_snapshot_actor_name_stored(test_obj, admin_user):
    v = take_snapshot(test_obj, actor=admin_user)
    assert 'Admin' in v.created_by_name


# ---------------------------------------------------------------------------
# restore_version
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_restore_rolls_back_title(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user, label='original')

    # Mutate live test
    test_obj.title = 'MUTATED TITLE'
    test_obj.save()

    restore_version(v1, actor=admin_user)
    test_obj.refresh_from_db()
    assert test_obj.title == 'Version Test 1'


@pytest.mark.django_db
def test_restore_recreates_deleted_section(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)

    # Delete section after snapshot
    TestSection.objects.filter(test=test_obj).delete()
    assert TestSection.objects.filter(test=test_obj).count() == 0

    restore_version(v1, actor=admin_user)
    assert TestSection.objects.filter(test=test_obj).count() == 1


@pytest.mark.django_db
def test_restore_soft_deletes_extra_questions(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)

    # Add a new question after snapshot (not in v1)
    section = TestSection.objects.filter(test=test_obj).first()
    extra = Question.objects.create(
        tenant=test_obj.tenant, test=test_obj, section=section,
        question_code='VQ_EXTRA', question_text='Extra?',
        question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', positive_marks=2, negative_marks=0,
        question_order=3, is_active=True,
    )

    restore_version(v1, actor=admin_user)

    extra.refresh_from_db()
    assert extra.is_deleted is True  # soft-deleted, not hard-deleted
    assert Question.objects.filter(test=test_obj, is_deleted=False).count() == 2


@pytest.mark.django_db
def test_restore_writes_audit(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)
    restore_version(v1, actor=admin_user)
    assert AuditLog.objects.filter(
        action='VERSION_RESTORE',
        resource_id=str(test_obj.id),
    ).exists()


# ---------------------------------------------------------------------------
# diff_versions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_diff_identical_versions_empty(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)
    v2 = take_snapshot(test_obj, actor=admin_user)
    d = diff_versions(v1, v2)
    assert d['test'] == {}
    assert d['sections']['added'] == []
    assert d['sections']['removed'] == []
    assert d['sections']['changed'] == []
    assert d['questions']['added'] == []
    assert d['questions']['removed'] == []


@pytest.mark.django_db
def test_diff_detects_title_change(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)
    test_obj.title = 'Changed Title'
    test_obj.save()
    v2 = take_snapshot(test_obj, actor=admin_user)
    d = diff_versions(v1, v2)
    assert 'title' in d['test']
    assert d['test']['title'][0] == 'Version Test 1'
    assert d['test']['title'][1] == 'Changed Title'


@pytest.mark.django_db
def test_diff_detects_new_question(test_obj, admin_user):
    v1 = take_snapshot(test_obj, actor=admin_user)

    section = TestSection.objects.filter(test=test_obj).first()
    Question.objects.create(
        tenant=test_obj.tenant, test=test_obj, section=section,
        question_code='VQ_NEW', question_text='New Q?',
        question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', positive_marks=2, negative_marks=0,
        question_order=3, is_active=True,
    )
    v2 = take_snapshot(test_obj, actor=admin_user)
    d = diff_versions(v1, v2)
    assert len(d['questions']['added']) == 1
