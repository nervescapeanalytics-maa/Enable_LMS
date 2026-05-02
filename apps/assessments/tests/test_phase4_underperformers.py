"""
Phase 4 — underperformer detection + alert-raising tests.

Covers:
  - find_underperformers: no attempts → empty list
  - find_underperformers: student with < need fails → not flagged
  - find_underperformers: student with exactly need fails → flagged
  - find_underperformers: only last window attempts counted (older ones ignored)
  - find_underperformers: tenant isolation (other tenant's student not returned)
  - raise_alerts_for: creates AlertLog row per underperformer
  - raise_alerts_for: deduplication — second call within 24h raises 0 new rows
  - raise_alerts_for: flag off → raises nothing
  - scan_and_raise: returns {'found': n, 'raised': m}
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from accounts.models import Student
from alerts.models import AlertLog, AlertRule
from assessments.models import Test, TestAttempt
from assessments.permissions import ensure_exam_feature_flags
from assessments.underperformers import find_underperformers, raise_alerts_for, scan_and_raise
from system_config.models import FeatureFlag
from tenants.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='UP_T1', name='Under Tenant', subdomain='up1')


@pytest.fixture
def flags(db, tenant):
    ensure_exam_feature_flags()


@pytest.fixture
def test_obj(db, tenant):
    return Test.objects.create(
        tenant=tenant, test_code='UP-TST', title='Under Test',
        test_type='PRACTICE', access_mode='OPEN', status='PUBLISHED',
        total_questions=5, total_marks=20, total_duration_minutes=30,
    )


def _make_student(tenant, code):
    s = Student(
        tenant=tenant, email=f'{code.lower()}@up.local',
        phone=f'90000{abs(hash(code)) % 100000:05d}',
        first_name=code, last_name='Test',
        student_code=code, student_class='11',
        exam_target='JEE', city='X', state='Y', status='ACTIVE',
    )
    s.set_password('x')
    s.save()
    return s


def _add_attempt(tenant, test, student, pct, submitted_at=None):
    a = TestAttempt.objects.create(
        tenant=tenant, test=test, student=student,
        status='EVALUATED', attempt_number=TestAttempt.objects.filter(
            test=test, student=student).count() + 1,
        started_at=submitted_at or timezone.now(),
        submitted_at=submitted_at or timezone.now(),
        percentage=pct,
    )
    return a


def _enable_flag(key, val):
    FeatureFlag.objects.filter(flag_key=key, tenant__isnull=True).update(is_enabled=val)


# ---------------------------------------------------------------------------
# find_underperformers
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_find_no_attempts_returns_empty(tenant, flags):
    assert find_underperformers(tenant=tenant) == []


@pytest.mark.django_db
def test_find_below_need_not_flagged(tenant, flags, test_obj):
    """2 fails out of 5 attempts is not enough (need=3 by default)."""
    s = _make_student(tenant, 'STU_LOW')
    for pct in [20, 25, 60, 70, 80]:
        _add_attempt(tenant, test_obj, s, pct)
    result = find_underperformers(tenant=tenant)
    assert all(it['student'].student_code != 'STU_LOW' for it in result)


@pytest.mark.django_db
def test_find_exactly_need_flagged(tenant, flags, test_obj):
    """3 fails in last 5 → flagged."""
    s = _make_student(tenant, 'STU_EXACT')
    for pct in [20, 25, 30, 70, 80]:   # 3 below 35 threshold
        _add_attempt(tenant, test_obj, s, pct)
    result = find_underperformers(tenant=tenant)
    codes = [it['student'].student_code for it in result]
    assert 'STU_EXACT' in codes


@pytest.mark.django_db
def test_find_uses_only_window_size(tenant, flags, test_obj):
    """
    7 old attempts all below threshold, but last 5 (window) have only 2 fails.
    Student should NOT be flagged.
    """
    s = _make_student(tenant, 'STU_WIN')
    base = timezone.now()
    # 7 old fails (outside window)
    for i in range(7, 0, -1):
        _add_attempt(tenant, test_obj, s, 20,
                     submitted_at=base - timezone.timedelta(days=i))
    # 5 recent: only 2 fails
    for pct in [20, 25, 60, 70, 75]:
        _add_attempt(tenant, test_obj, s, pct)

    result = find_underperformers(tenant=tenant)
    codes = [it['student'].student_code for it in result]
    assert 'STU_WIN' not in codes


@pytest.mark.django_db
def test_find_tenant_isolation(tenant, flags, test_obj, db):
    """Students from another tenant must not appear."""
    other_tenant = Tenant.objects.create(code='UP_OT', name='Other', subdomain='ot')
    other_test = Test.objects.create(
        tenant=other_tenant, test_code='OT-TST', title='Other',
        test_type='PRACTICE', access_mode='OPEN', status='PUBLISHED',
        total_questions=5, total_marks=20, total_duration_minutes=30,
    )
    other_s = _make_student(other_tenant, 'STU_OTH')
    for pct in [20, 20, 20, 20, 20]:
        _add_attempt(other_tenant, other_test, other_s, pct)

    result = find_underperformers(tenant=tenant)
    codes = [it['student'].student_code for it in result]
    assert 'STU_OTH' not in codes


# ---------------------------------------------------------------------------
# raise_alerts_for
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_raise_creates_alert_log(tenant, flags, test_obj):
    _enable_flag('exam.underperformer_alerts', True)
    s = _make_student(tenant, 'STU_RAI')
    items = [{
        'student': s, 'fails': 3, 'window': 5, 'avg': 28.0,
        'last_attempt_at': timezone.now(), 'attempts': [],
    }]
    count_before = AlertLog.objects.count()
    raised = raise_alerts_for(items, tenant=tenant)
    assert raised == 1
    assert AlertLog.objects.count() == count_before + 1


@pytest.mark.django_db
def test_raise_deduplicates_within_24h(tenant, flags, test_obj):
    _enable_flag('exam.underperformer_alerts', True)
    s = _make_student(tenant, 'STU_DED')
    rule, _ = AlertRule.objects.get_or_create(
        tenant=tenant,
        rule_type=AlertRule.RuleType.LOW_TEST_SCORE,
        name='Exam — consistent underperformer',
        defaults=dict(
            description='test', category=AlertRule.Category.ASSESSMENTS,
            threshold=0, time_window_minutes=1440,
            severity=AlertRule.Severity.WARNING,
            notify_method=AlertRule.NotifyMethod.ADMIN_PANEL,
            is_active=True,
        ),
    )
    AlertLog.objects.create(
        tenant=tenant, rule=rule,
        severity=AlertLog.Severity.WARNING,
        message='existing',
        details={'student_id': str(s.id)},
        is_acknowledged=False,
    )
    items = [{
        'student': s, 'fails': 4, 'window': 5, 'avg': 22.0,
        'last_attempt_at': timezone.now(), 'attempts': [],
    }]
    raised = raise_alerts_for(items, tenant=tenant)
    assert raised == 0   # deduplicated


@pytest.mark.django_db
def test_raise_flag_off_raises_nothing(tenant, flags, test_obj):
    _enable_flag('exam.underperformer_alerts', False)
    s = _make_student(tenant, 'STU_OFF')
    items = [{
        'student': s, 'fails': 4, 'window': 5, 'avg': 22.0,
        'last_attempt_at': timezone.now(), 'attempts': [],
    }]
    raised = raise_alerts_for(items, tenant=tenant)
    assert raised == 0
    # restore
    _enable_flag('exam.underperformer_alerts', True)


# ---------------------------------------------------------------------------
# scan_and_raise
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_scan_and_raise_returns_counts(tenant, flags, test_obj):
    _enable_flag('exam.underperformer_alerts', True)
    result = scan_and_raise(tenant=tenant)
    assert 'found' in result
    assert 'raised' in result
    assert isinstance(result['found'], int)
    assert isinstance(result['raised'], int)
