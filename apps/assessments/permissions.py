"""
Exams & Assessments — RBAC, Feature Flags, and Audit Helpers (Phase 1 foundation).

Roles
-----
* ADMIN: full control. `accounts.Admin` records WITHOUT a `staff_role` FK,
         OR with `staff_role.level == 'SUPER_ADMIN'`.
* STAFF: scoped operator. `accounts.Admin` records WITH a `staff_role` FK
         that has `can_manage_exams = True` (or other relevant flag).
* STUDENT: take exams, view results.
* TEACHER: NO access to this module (revoked everywhere; FK kept for history only).

Feature flags
-------------
A short list of exam-specific flags lives in `EXAM_FEATURE_FLAGS`. They
are seeded via `ensure_exam_feature_flags()` (idempotent) and toggled
through Django admin → Feature Flags. UI surfaces the toggle for admin only.

Audit
-----
Every write/state-change in the exam module MUST go through `log_exam_event(...)`
which writes an immutable record in `audit.AuditLog`.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Optional, Any
from uuid import UUID

from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Feature flags catalogue
# =============================================================================

EXAM_FEATURE_FLAGS = [
    # key,                            display name,                                 default
    ('exam.identity_verification',    'Identity verification (webcam + ID match)',  False),
    ('exam.proctoring_snapshots',     'Proctoring webcam snapshots (Standard)',     True),
    ('exam.tab_switch_detection',     'Tab-switch detection (Basic)',               True),
    ('exam.copy_paste_block',         'Block copy / paste during exam (Basic)',     True),
    ('exam.fullscreen_lockdown',      'Fullscreen lockdown (Standard)',             True),
    ('exam.devtools_detection',       'DevTools open detection (Basic)',            True),
    ('exam.ai_prediction_rule',       'AI predicted score (rule-based)',            True),
    ('exam.ai_prediction_llm',        'AI narrative insights (LLM)',                False),
    ('exam.percentile_ranking',       'Percentile rank vs cohort',                  True),
    ('exam.leaderboard',              'Anonymized class leaderboard',               True),
    ('exam.dispute_flow',              'Mark disputes',                              True),
    ('exam.pdf_record_card',          'Downloadable PDF student record card',       True),
    ('exam.topic_heatmap',            'Topic-wise strength/weakness heatmap',       True),
    ('exam.underperformer_alerts',    'Alert on consistent underperformers',        True),
    ('exam.question_import',          'Bulk question import (CSV/XLSX)',            True),
    ('exam.test_versioning',          'Test version control (snapshot + revert)',   True),
]


def ensure_exam_feature_flags() -> int:
    """Seed missing feature flags. Idempotent. Returns number created."""
    from system_config.models import FeatureFlag

    created = 0
    for key, name, default in EXAM_FEATURE_FLAGS:
        obj, was_created = FeatureFlag.objects.get_or_create(
            tenant=None,  # GLOBAL by default; admin can override per-tenant later
            flag_key=key,
            defaults={
                'flag_name': name,
                'is_enabled': default,
                'description': f'Auto-seeded by exams module. {name}',
                'allowed_user_types': ['STUDENT', 'ADMIN', 'STAFF'],
            },
        )
        if was_created:
            created += 1
    return created


# =============================================================================
# Numeric thresholds (admin-configurable via SystemSetting)
# =============================================================================

EXAM_SETTINGS = [
    # (key,                              default,  type,       description)
    ('exam.fail_threshold_percent',      '35',     'INTEGER',  'Score below this % is flagged as a fail.'),
    ('exam.underperformer_fail_count',   '3',      'INTEGER',  'Number of fails…'),
    ('exam.underperformer_window_size',  '5',      'INTEGER',  '…within this many most-recent attempts.'),
    ('exam.alert_red_zone_percent',      '35',     'INTEGER',  'Red-zone score threshold for in-app alerts.'),
    ('exam.alert_amber_zone_percent',    '50',     'INTEGER',  'Amber-zone threshold for in-app alerts.'),
]


def ensure_exam_settings() -> int:
    """Seed default numeric thresholds. Idempotent. Returns number created."""
    from system_config.models import SystemSetting
    created = 0
    for key, value, vtype, desc in EXAM_SETTINGS:
        _, was = SystemSetting.objects.get_or_create(
            tenant=None, setting_key=key,
            defaults=dict(setting_value=value, value_type=vtype,
                          category='exams', description=desc, is_editable=True),
        )
        if was:
            created += 1
    return created


def get_exam_setting_int(key: str, tenant=None, default: int = 0) -> int:
    """Resolve an integer SystemSetting (tenant-scoped, falls back to global)."""
    from system_config.models import SystemSetting
    qs = SystemSetting.objects.filter(setting_key=key)
    row = (qs.filter(tenant=tenant).first() if tenant is not None else None) \
          or qs.filter(tenant__isnull=True).first()
    if not row or not row.setting_value:
        return default
    try:
        return int(row.setting_value)
    except (ValueError, TypeError):
        return default


def is_feature_enabled(flag_key: str, tenant=None, user_type: Optional[str] = None) -> bool:
    """
    Resolve a feature flag.

    Resolution order:
        1. tenant-scoped flag if tenant given
        2. global flag (tenant=NULL)
        3. False (unknown flag)
    """
    from system_config.models import FeatureFlag

    qs = FeatureFlag.objects.filter(flag_key=flag_key)
    flag = None
    if tenant is not None:
        flag = qs.filter(tenant=tenant).first()
    if flag is None:
        flag = qs.filter(tenant__isnull=True).first()
    if flag is None:
        return False
    if not flag.is_enabled:
        return False
    if user_type and flag.allowed_user_types:
        if user_type not in flag.allowed_user_types:
            return False
    now = timezone.now()
    if flag.start_date and now < flag.start_date:
        return False
    if flag.end_date and now > flag.end_date:
        return False
    return True


# =============================================================================
# RBAC
# =============================================================================

def get_logged_in_admin(request):
    """Return accounts.Admin row if request.session has an ADMIN user, else None."""
    from accounts.models import Admin

    if request.session.get('user_type') != 'ADMIN':
        return None
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Admin.objects.select_related('staff_role', 'tenant').get(id=user_id)
    except (Admin.DoesNotExist, ValueError):
        return None


def is_admin_full(admin_user) -> bool:
    """True if this Admin has unrestricted exam access."""
    if admin_user is None:
        return False
    sr = admin_user.staff_role
    if sr is None:
        return True  # legacy admin without staff role => full admin
    return sr.level == 'SUPER_ADMIN'


def is_staff_member(admin_user) -> bool:
    """True if this Admin is a Staff (operator-tier) account."""
    if admin_user is None:
        return False
    sr = admin_user.staff_role
    return sr is not None and sr.level in ('ADMIN', 'OPERATOR')


def can_manage_exams(admin_user) -> bool:
    """True if this Admin/Staff can manage exams in any capacity."""
    if admin_user is None:
        return False
    if is_admin_full(admin_user):
        return True
    sr = admin_user.staff_role
    return bool(sr and sr.is_active and sr.can_manage_exams)


# ----- decorators -----

def admin_required(view_func):
    """Only full admins (no staff role, or SUPER_ADMIN level)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        admin_user = get_logged_in_admin(request)
        if admin_user is None:
            return _redirect_to_login(request, role='admin')
        if not is_admin_full(admin_user):
            return _forbid(request, 'Admin role required')
        request.admin_user = admin_user
        return view_func(request, *args, **kwargs)
    return _wrapped


def staff_or_admin_required(view_func):
    """Either full admin OR staff with can_manage_exams."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        admin_user = get_logged_in_admin(request)
        if admin_user is None:
            return _redirect_to_login(request, role='admin')
        if not can_manage_exams(admin_user):
            return _forbid(request, 'Insufficient permissions')
        request.admin_user = admin_user
        return view_func(request, *args, **kwargs)
    return _wrapped


def block_teachers(view_func):
    """Defense-in-depth: explicitly reject teacher session for any exam admin route."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') == 'TEACHER':
            return _forbid(request, 'Teachers do not have access to the exams module')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _redirect_to_login(request, role: str = 'admin'):
    nxt = request.get_full_path()
    return redirect(f'/login/?role={role}&next={nxt}')


def _forbid(request, reason: str):
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'error': reason}, status=403)
    return HttpResponseForbidden(f'<h1>403 Forbidden</h1><p>{reason}</p>')


# =============================================================================
# Audit
# =============================================================================

def log_exam_event(
    *,
    request=None,
    actor=None,
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    resource_name: str = '',
    description: str = '',
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    severity: str = 'INFO',
    is_security_event: bool = False,
    extra_meta: Optional[dict] = None,
) -> Optional[Any]:
    """
    Write an immutable audit-log entry for an exam-module event. Best-effort:
    failures are swallowed and logged so they never block business flow.

    Args:
        request: The HTTP request (used to extract IP/user-agent if available).
        actor: Any Admin/Student/Teacher user object (or None for system events).
        action: One of audit.AuditLog.ActionType values, or a custom verb.
        resource_type: e.g. 'Test', 'TestAttempt', 'OfflineTestMarks'.
        resource_id: UUID of the affected row.
        resource_name: Human-readable label (e.g. test code).
        description: Free-text summary.
        old_values / new_values: Snapshots for change tracking.
        severity: AuditLog.Severity value.
        is_security_event: True for proctoring violations, role changes, etc.
        extra_meta: Anything else worth keeping (dict).
    """
    try:
        from audit.models import AuditLog

        ip = None
        ua = ''
        if request is not None:
            xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')[:1000]

        actor_id = getattr(actor, 'id', None)
        actor_type = (
            'ADMIN'   if actor and actor.__class__.__name__ == 'Admin'   else
            'STAFF'   if actor and getattr(actor, 'staff_role_id', None) else
            'STUDENT' if actor and actor.__class__.__name__ == 'Student' else
            'TEACHER' if actor and actor.__class__.__name__ == 'Teacher' else
            'SYSTEM'
        )
        if actor and getattr(actor, 'staff_role_id', None) and actor_type == 'ADMIN':
            actor_type = 'STAFF'

        username = ''
        if actor:
            fn = getattr(actor, 'first_name', '') or ''
            ln = getattr(actor, 'last_name', '') or ''
            username = (fn + ' ' + ln).strip() or getattr(actor, 'email', '') or str(actor_id)

        tenant = getattr(actor, 'tenant', None)

        rid = None
        if resource_id is not None:
            try:
                rid = UUID(str(resource_id))
            except (TypeError, ValueError):
                rid = None

        return AuditLog.objects.create(
            tenant=tenant,
            user_id=actor_id,
            user_type=actor_type,
            username=username[:200],
            ip_address=ip,
            user_agent=ua,
            action=action[:20],
            action_description=description[:1000] or None,
            resource_type=resource_type[:100] or None,
            resource_id=rid,
            resource_name=resource_name[:500] or None,
            http_method=(getattr(request, 'method', None) or '')[:10] or None,
            request_path=(getattr(request, 'get_full_path', lambda: '')() or '')[:1000] or None,
            old_values=old_values,
            new_values=new_values,
            severity=severity,
            is_security_event=is_security_event,
            audit_meta=extra_meta,
        )
    except Exception:
        logger.exception('exam audit log failed for action=%s resource=%s', action, resource_type)
        return None
