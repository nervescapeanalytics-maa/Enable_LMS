"""
Underperformer detection + in-app alert raising.

A student is flagged as an "underperformer" when at least
``exam.underperformer_fail_count`` of their last
``exam.underperformer_window_size`` evaluated attempts scored below
``exam.fail_threshold_percent``.

When a student crosses the line we raise an ``AlertLog`` row against the
existing ``alerts`` app, severity = WARNING. Acknowledgement is handled
by the existing alerts UI.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable

from django.utils import timezone

from .models import TestAttempt
from .permissions import (
    get_exam_setting_int, is_feature_enabled, log_exam_event,
)

logger = logging.getLogger(__name__)

EVALUATED_STATUSES = ('EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED')


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def find_underperformers(*, tenant=None) -> list[dict]:
    """
    Return one entry per student that currently meets the underperformer
    criteria.

    Each entry::

        {
            'student': Student,
            'fails':   int,    # within window
            'window':  int,    # window size used
            'avg':     float,  # avg pct in window
            'last_attempt_at': datetime|None,
            'attempts': [TestAttempt, ...],
        }
    """
    fail_pct = get_exam_setting_int('exam.fail_threshold_percent', tenant=tenant, default=35)
    need = get_exam_setting_int('exam.underperformer_fail_count', tenant=tenant, default=3)
    window = get_exam_setting_int('exam.underperformer_window_size', tenant=tenant, default=5)

    qs = (
        TestAttempt.objects
        .filter(status__in=EVALUATED_STATUSES)
        .select_related('student', 'test')
        .order_by('student_id', '-submitted_at')
    )
    if tenant is not None:
        qs = qs.filter(tenant=tenant)

    grouped: dict = defaultdict(list)
    for a in qs:
        grouped[a.student_id].append(a)

    out: list[dict] = []
    for student_id, attempts in grouped.items():
        recent = attempts[:window]
        if len(recent) < need:
            continue
        fails = sum(1 for a in recent if (a.percentage or 0) < fail_pct)
        if fails < need:
            continue
        avg = sum(float(a.percentage or 0) for a in recent) / len(recent)
        last = recent[0]
        out.append({
            'student': last.student,
            'fails': fails,
            'window': len(recent),
            'avg': round(avg, 2),
            'last_attempt_at': last.submitted_at or last.started_at,
            'attempts': recent,
        })
    out.sort(key=lambda x: (-x['fails'], x['avg']))
    return out


# ---------------------------------------------------------------------------
# Alert raising
# ---------------------------------------------------------------------------
def _get_or_create_rule(tenant):
    from alerts.models import AlertRule
    rule, _ = AlertRule.objects.get_or_create(
        tenant=tenant,
        rule_type=AlertRule.RuleType.LOW_TEST_SCORE,
        name='Exam — consistent underperformer',
        defaults=dict(
            description='Auto-raised by the Exams module when a student '
                        'fails ≥N of last M attempts.',
            category=AlertRule.Category.ASSESSMENTS,
            threshold=0,
            time_window_minutes=60 * 24 * 30,  # 30-day cosmetic window
            severity=AlertRule.Severity.WARNING,
            notify_method=AlertRule.NotifyMethod.ADMIN_PANEL,
            is_active=True,
        ),
    )
    return rule


def raise_alerts_for(items: list[dict], *, tenant, request=None) -> int:
    """Persist AlertLog rows for the given underperformer entries.

    De-duplicates: if an unacknowledged WARNING for the same student already
    exists in the last 24h, no new entry is written.
    """
    if not is_feature_enabled('exam.underperformer_alerts',
                              tenant=tenant, user_type='ADMIN'):
        return 0

    from alerts.models import AlertLog
    rule = _get_or_create_rule(tenant)
    cutoff = timezone.now() - timezone.timedelta(days=1)
    raised = 0
    for it in items:
        student = it['student']
        recent = AlertLog.objects.filter(
            tenant=tenant, rule=rule,
            is_acknowledged=False, triggered_at__gte=cutoff,
            details__student_id=str(student.id),
        ).exists()
        if recent:
            continue
        AlertLog.objects.create(
            tenant=tenant, rule=rule,
            severity=AlertLog.Severity.WARNING,
            message=(
                f'{student.first_name} {student.last_name} '
                f'({student.student_code}) failed {it["fails"]} of last '
                f'{it["window"]} attempts (avg {it["avg"]}%).'
            ),
            details={
                'student_id': str(student.id),
                'student_code': student.student_code,
                'fails': it['fails'],
                'window': it['window'],
                'avg_pct': it['avg'],
            },
        )
        raised += 1
        log_exam_event(
            request=request,
            action='UNDERPERFORMER_ALERT',
            resource_type='Student', resource_id=student.id,
            resource_name=student.student_code,
            description=f'Underperformer alert raised: {it["fails"]}/{it["window"]} fails',
            severity='WARNING', is_security_event=False,
            extra_meta={'fails': it['fails'], 'window': it['window'], 'avg': it['avg']},
        )
    return raised


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------
def scan_and_raise(*, tenant, request=None) -> dict:
    items = find_underperformers(tenant=tenant)
    raised = raise_alerts_for(items, tenant=tenant, request=request)
    return {'found': len(items), 'raised': raised}
