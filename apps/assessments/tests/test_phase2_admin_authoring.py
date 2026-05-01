"""
Phase 2 — Exam authoring tests.

Covers:
 - RBAC enforcement (admin / staff with can_manage_exams / staff without / teacher / student / anonymous)
 - Exam create / edit / publish / unpublish / archive / soft-delete + audit log
 - Question create / edit / delete + total_questions recount
 - Form validation (MCQ_SINGLE answer not in options, MCQ_MULTI subset, TRUE_FALSE)
 - Feature flag toggle endpoint (admin only) with audit
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from django.test import Client
from django.utils import timezone

from accounts.models import Admin, StaffRole
from assessments.models import Test, Question
from assessments.permissions import ensure_exam_feature_flags
from assessments.views.forms import TestForm, QuestionForm
from audit.models import AuditLog
from system_config.models import FeatureFlag
from tenants.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='T_EXAM', name='Test Tenant', subdomain='texam')


@pytest.fixture
def full_admin(db, tenant):
    a = Admin(
        tenant=tenant, email='full@t.local', phone='9999900000',
        first_name='Full', last_name='Admin', admin_type='SUPER_ADMIN',
        status='ACTIVE',
    )
    a.set_password('x')
    a.save()
    return a


@pytest.fixture
def staff_with_exams(db, tenant):
    role = StaffRole.objects.create(
        tenant=tenant, level='ADMIN', name='Exams Operator',
        can_manage_exams=True,
    )
    a = Admin(
        tenant=tenant, email='staff@t.local', phone='9999900001',
        first_name='Staff', last_name='Ops', admin_type='ACADEMIC_ADMIN',
        staff_role=role, status='ACTIVE',
    )
    a.set_password('x')
    a.save()
    return a


@pytest.fixture
def staff_without_exams(db, tenant):
    role = StaffRole.objects.create(
        tenant=tenant, level='OPERATOR', name='Limited Operator',
        can_manage_exams=False,
    )
    a = Admin(
        tenant=tenant, email='nostaff@t.local', phone='9999900002',
        first_name='No', last_name='Exam', admin_type='SUPPORT_ADMIN',
        staff_role=role, status='ACTIVE',
    )
    a.set_password('x')
    a.save()
    return a


def _login(client, user, user_type='ADMIN'):
    s = client.session
    s['user_type'] = user_type
    s['user_id'] = str(user.id) if user else 'fake'
    s['user_name'] = getattr(user, 'first_name', 'Tester')
    s['user_email'] = getattr(user, 'email', '')
    s.save()


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExamRBAC:
    def test_anonymous_redirected(self, client):
        r = client.get('/staff/exams/')
        assert r.status_code in (301, 302)
        assert '/login/' in r['Location']

    def test_teacher_blocked(self, client):
        _login(client, None, user_type='TEACHER')
        r = client.get('/staff/exams/')
        assert r.status_code == 403

    def test_staff_without_exam_perm_blocked(self, client, staff_without_exams):
        _login(client, staff_without_exams)
        r = client.get('/staff/exams/')
        assert r.status_code == 403

    def test_staff_with_exam_perm_allowed(self, client, staff_with_exams):
        _login(client, staff_with_exams)
        r = client.get('/staff/exams/')
        assert r.status_code == 200

    def test_full_admin_allowed(self, client, full_admin):
        _login(client, full_admin)
        r = client.get('/staff/exams/')
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Exam CRUD + lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExamLifecycle:
    def _payload(self, **over):
        base = {
            'test_code': 'EX001', 'title': 'Sample Exam', 'description': '',
            'instructions': '', 'test_type': 'PRACTICE', 'exam_target': 'GENERAL',
            'difficulty_level': 'MEDIUM',
            'subject': '', 'chapter': '', 'batch': '',
            'total_duration_minutes': 60, 'buffer_time_minutes': 0,
            'late_submission_allowed': '', 'late_submission_penalty_percent': 0,
            'show_timer': 'on',
            'total_marks': 10, 'passing_marks': 4, 'passing_percent': 33.0,
            'positive_marks_per_question': 4, 'negative_marks_per_question': -1,
            'partial_marking': '',
            'max_attempts': 1, 'shuffle_questions': '', 'shuffle_options': '',
            'allow_review': 'on', 'allow_backward': 'on',
            'access_mode': 'OPEN', 'access_password': '',
            'result_display_mode': 'IMMEDIATE',
            'show_correct_answers': 'on', 'show_explanations': 'on',
            'show_rank': 'on', 'show_percentile': 'on',
            'enable_proctoring': '', 'prevent_tab_switch': 'on', 'max_tab_switches': 3,
            'prevent_copy_paste': 'on', 'prevent_screenshot': 'on',
            'webcam_required': '', 'full_screen_required': '',
        }
        base.update(over)
        return base

    def test_create_exam_via_post(self, client, full_admin):
        _login(client, full_admin)
        r = client.post('/staff/exams/new/', self._payload())
        assert r.status_code == 302
        t = Test.objects.get(test_code='EX001')
        assert t.tenant_id == full_admin.tenant_id
        assert t.status == 'DRAFT'
        # audit
        assert AuditLog.objects.filter(resource_type='Test', resource_id=t.id, action='CREATE').exists()

    def test_publish_requires_questions(self, client, full_admin):
        _login(client, full_admin)
        t = Test.objects.create(
            tenant=full_admin.tenant, test_code='P1', title='P', total_duration_minutes=30,
        )
        r = client.post(f'/staff/exams/{t.id}/publish/')
        assert r.status_code == 302
        t.refresh_from_db()
        assert t.status == 'DRAFT'  # blocked

    def test_publish_with_questions(self, client, full_admin):
        _login(client, full_admin)
        t = Test.objects.create(
            tenant=full_admin.tenant, test_code='P2', title='P2', total_duration_minutes=30,
        )
        Question.objects.create(
            tenant=full_admin.tenant, test=t, question_text='2+2?',
            question_type='MCQ_SINGLE', correct_answer='A',
            option_a='4', option_b='5', positive_marks=Decimal('1'),
        )
        r = client.post(f'/staff/exams/{t.id}/publish/')
        assert r.status_code == 302
        t.refresh_from_db()
        assert t.status == 'PUBLISHED'
        assert t.published_at is not None
        assert AuditLog.objects.filter(resource_id=t.id, description__icontains='Published').exists()

    def test_staff_cannot_publish(self, client, staff_with_exams):
        _login(client, staff_with_exams)
        t = Test.objects.create(
            tenant=staff_with_exams.tenant, test_code='S1', title='S', total_duration_minutes=30,
        )
        Question.objects.create(
            tenant=staff_with_exams.tenant, test=t, question_text='?',
            question_type='MCQ_SINGLE', correct_answer='A',
            option_a='1', option_b='2',
        )
        r = client.post(f'/staff/exams/{t.id}/publish/')
        assert r.status_code == 403

    def test_unpublish_archive_delete(self, client, full_admin):
        _login(client, full_admin)
        t = Test.objects.create(
            tenant=full_admin.tenant, test_code='U1', title='U',
            total_duration_minutes=30, status='PUBLISHED',
        )
        r = client.post(f'/staff/exams/{t.id}/unpublish/')
        t.refresh_from_db()
        assert t.status == 'DRAFT'

        client.post(f'/staff/exams/{t.id}/archive/')
        t.refresh_from_db()
        assert t.status == 'ARCHIVED'

        client.post(f'/staff/exams/{t.id}/delete/')
        t.refresh_from_db()
        assert t.is_deleted is True


# ---------------------------------------------------------------------------
# Question CRUD + recount
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestQuestionFlow:
    def test_create_increments_total_questions(self, client, full_admin):
        _login(client, full_admin)
        t = Test.objects.create(
            tenant=full_admin.tenant, test_code='QC1', title='QC1',
            total_duration_minutes=30, total_questions=0,
        )
        payload = {
            'question_code': '', 'question_text': 'Capital of India?',
            'question_image': '',
            'question_type': 'MCQ_SINGLE', 'difficulty': 'EASY',
            'option_a': 'Mumbai', 'option_b': 'Delhi', 'option_c': '', 'option_d': '', 'option_e': '',
            'correct_answer': 'B', 'correct_answer_value': '',
            'numerical_tolerance': '', 'answer_explanation': '',
            'positive_marks': 1, 'negative_marks': 0, 'partial_marks': '',
            'subject': '', 'chapter': '', 'topic': '', 'tags': '',
            'test': str(t.id), 'section': '', 'question_order': 1,
        }
        r = client.post('/staff/exams/questions/new/', payload)
        assert r.status_code == 302
        t.refresh_from_db()
        assert t.total_questions == 1

    def test_delete_decrements_total_questions(self, client, full_admin):
        _login(client, full_admin)
        t = Test.objects.create(
            tenant=full_admin.tenant, test_code='QC2', title='QC2',
            total_duration_minutes=30, total_questions=2,
        )
        q1 = Question.objects.create(
            tenant=full_admin.tenant, test=t, question_text='Q1',
            question_type='MCQ_SINGLE', correct_answer='A', option_a='1', option_b='2',
        )
        Question.objects.create(
            tenant=full_admin.tenant, test=t, question_text='Q2',
            question_type='MCQ_SINGLE', correct_answer='A', option_a='1', option_b='2',
        )
        r = client.post(f'/staff/exams/questions/{q1.id}/delete/')
        assert r.status_code == 302
        t.refresh_from_db()
        assert t.total_questions == 1


# ---------------------------------------------------------------------------
# Form validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFormValidation:
    def test_mcq_single_correct_must_be_in_options(self, tenant):
        f = QuestionForm(data={
            'question_text': 'Q', 'question_type': 'MCQ_SINGLE',
            'difficulty': 'EASY',
            'option_a': 'one', 'option_b': 'two',
            'correct_answer': 'C',  # invalid
            'positive_marks': 1, 'negative_marks': 0, 'question_order': 1,
        }, tenant=tenant)
        assert not f.is_valid()
        assert 'correct_answer' in f.errors

    def test_mcq_multi_subset_validation(self, tenant):
        f = QuestionForm(data={
            'question_text': 'Q', 'question_type': 'MCQ_MULTI', 'difficulty': 'EASY',
            'option_a': 'a', 'option_b': 'b', 'option_c': 'c',
            'correct_answer': 'A,D',  # D not present
            'positive_marks': 2, 'negative_marks': 0, 'question_order': 1,
        }, tenant=tenant)
        assert not f.is_valid()
        assert 'correct_answer' in f.errors

    def test_true_false_must_be_tf(self, tenant):
        f = QuestionForm(data={
            'question_text': 'Q', 'question_type': 'TRUE_FALSE', 'difficulty': 'EASY',
            'correct_answer': 'maybe',
            'positive_marks': 1, 'negative_marks': 0, 'question_order': 1,
        }, tenant=tenant)
        assert not f.is_valid()

    def test_test_form_password_mode_requires_password(self, tenant):
        f = TestForm(data={
            'test_code': 'X', 'title': 'X',
            'test_type': 'PRACTICE', 'exam_target': 'GENERAL', 'difficulty_level': 'MEDIUM',
            'total_duration_minutes': 60, 'buffer_time_minutes': 0,
            'late_submission_penalty_percent': 0,
            'total_marks': 10, 'passing_marks': 4, 'passing_percent': 33.0,
            'positive_marks_per_question': 4, 'negative_marks_per_question': -1,
            'max_attempts': 1, 'access_mode': 'PASSWORD', 'access_password': '',
            'result_display_mode': 'IMMEDIATE', 'max_tab_switches': 3,
        }, tenant=tenant)
        assert not f.is_valid()
        assert 'access_password' in f.errors


# ---------------------------------------------------------------------------
# Feature flag toggle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFeatureFlagsView:
    def test_seed_creates_13_flags(self):
        ensure_exam_feature_flags()
        assert FeatureFlag.objects.filter(flag_key__startswith='exam.').count() == 13

    def test_full_admin_can_toggle(self, client, full_admin):
        ensure_exam_feature_flags()
        _login(client, full_admin)
        r = client.post('/staff/exams/flags/', {
            'flag_key': 'exam.ai_prediction_llm', 'is_enabled': '1',
        })
        assert r.status_code == 200
        assert r.json()['is_enabled'] is True
        f = FeatureFlag.objects.get(flag_key='exam.ai_prediction_llm', tenant__isnull=True)
        assert f.is_enabled is True
        assert AuditLog.objects.filter(resource_type='FeatureFlag', resource_id=f.id).exists()

    def test_staff_cannot_toggle(self, client, staff_with_exams):
        ensure_exam_feature_flags()
        _login(client, staff_with_exams)
        r = client.post('/staff/exams/flags/', {
            'flag_key': 'exam.ai_prediction_llm', 'is_enabled': '1',
        })
        assert r.status_code == 403
