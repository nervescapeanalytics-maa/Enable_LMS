"""Seed comprehensive alert rules covering frontend, backend, database and
domain (attendance/live class/assessment) metrics.

Every rule emails neeraj.vishen@gmail.com by default and posts to the admin
panel. Re-running is idempotent — rules are matched on (tenant, name).

Run:
    python manage.py seed_alert_rules
    python manage.py seed_alert_rules --email someone@example.com
    python manage.py seed_alert_rules --reset   # delete existing alert rules first
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


DEFAULT_EMAIL = 'neeraj.vishen@gmail.com'

# (name, description, category, rule_type, threshold, time_window_minutes, severity)
RULES = [
    # ── SECURITY ──
    ('Brute-force login attack', 'Detects multiple failed logins from the same IP within a short time.',
     'SECURITY', 'BRUTE_FORCE', 10, 15, 'CRITICAL'),
    ('Failed login streak', 'Threshold of total failed login attempts in the time window.',
     'SECURITY', 'FAILED_LOGIN_STREAK', 25, 60, 'WARNING'),
    ('Suspicious login detected', 'Logins flagged as suspicious by the auth subsystem.',
     'SECURITY', 'SUSPICIOUS_LOGIN', 1, 60, 'WARNING'),
    ('New / unknown device login', 'Login from a device not previously seen for the user.',
     'SECURITY', 'NEW_DEVICE_LOGIN', 1, 60, 'INFO'),

    # ── SESSION TRACKING ──
    ('Too many concurrent sessions', 'A user has more than N active concurrent sessions.',
     'SESSION_TRACKING', 'CONCURRENT_SESSIONS', 5, 60, 'WARNING'),
    ('Stale (inactive) sessions', 'Active sessions inactive longer than threshold (minutes).',
     'SESSION_TRACKING', 'INACTIVE_SESSION', 120, 60, 'INFO'),

    # ── ATTENDANCE ──
    ('Daily attendance below threshold', 'Overall attendance percentage drops below threshold.',
     'ATTENDANCE', 'LOW_ATTENDANCE', 75, 1440, 'WARNING'),
    ('Student absent streak', 'A student is absent for N consecutive working days.',
     'ATTENDANCE', 'ABSENT_STREAK', 3, 4320, 'WARNING'),

    # ── LIVE CLASSES ──
    ('Live class attendance low', 'Live class attendance below threshold percentage.',
     'LIVE_CLASSES', 'LOW_CLASS_ATTENDANCE', 60, 1440, 'WARNING'),
    ('Scheduled class did not start', 'A scheduled class did not start within grace window.',
     'LIVE_CLASSES', 'CLASS_NOT_STARTED', 5, 60, 'CRITICAL'),

    # ── ASSESSMENTS ──
    ('Average test score low', 'Average test score below threshold.',
     'ASSESSMENTS', 'LOW_TEST_SCORE', 40, 1440, 'WARNING'),
    ('Test not submitted by deadline', 'Tests with no submission past the deadline.',
     'ASSESSMENTS', 'TEST_NOT_SUBMITTED', 0, 60, 'WARNING'),

    # ── SYSTEM ──
    ('High backend error rate', 'Backend 5xx error rate exceeds threshold.',
     'SYSTEM', 'HIGH_ERROR_RATE', 25, 15, 'CRITICAL'),
    ('Slow database queries', 'Number of queries exceeding the slow-query threshold.',
     'SYSTEM', 'DB_SLOW_QUERIES', 5, 15, 'WARNING'),

    # ── REAL-TIME STUDENT / TEACHER ACTIVITY ──
    ('Student inactive 7+ days', 'Student has not logged in for 7 or more consecutive days.',
     'SESSION_TRACKING', 'STUDENT_NO_LOGIN_7D', 7, 10080, 'WARNING'),
    ('Student frequent lates', 'Student marked LATE 3 or more times in the last 5 working days.',
     'ATTENDANCE', 'STUDENT_MULTIPLE_LATES', 3, 7200, 'WARNING'),
    ('Teacher absent (no leave)', 'Teacher absent from work without an approved leave on a working day.',
     'ATTENDANCE', 'TEACHER_NO_SHOW', 1, 1440, 'CRITICAL'),
    ('Teacher late to class', 'Teacher started a scheduled class more than N minutes late.',
     'LIVE_CLASSES', 'TEACHER_LATE_TO_CLASS', 10, 60, 'WARNING'),
    ('Parent portal never used', 'Parent account exists but has never logged into the portal.',
     'SESSION_TRACKING', 'PARENT_PORTAL_INACTIVE', 1, 43200, 'INFO'),

    # ── REAL-TIME ATTENDANCE (student + teacher) ──
    ('Student attendance % low', 'Student monthly attendance percentage is below threshold (default 75%).',
     'ATTENDANCE', 'STUDENT_LOW_ATTEND_PCT', 75, 43200, 'WARNING'),
    ('Teacher attendance % low', 'Teacher monthly attendance percentage is below threshold (default 90%).',
     'ATTENDANCE', 'TEACHER_LOW_ATTEND_PCT', 90, 43200, 'WARNING'),
    ('Batch average attendance low', 'Batch-wide average attendance percentage is below threshold (default 70%).',
     'ATTENDANCE', 'BATCH_LOW_AVG_ATTEND', 70, 43200, 'CRITICAL'),
]


class Command(BaseCommand):
    help = 'Seed comprehensive Alert Rules across all categories with email notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--email', default=DEFAULT_EMAIL,
                            help='Email address to notify (default: %(default)s)')
        parser.add_argument('--tenant', default=None,
                            help='Tenant code (default: every active tenant)')
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing alert rules first')

    def handle(self, *args, **opts):
        from alerts.models import AlertRule
        from tenants.models import Tenant

        if opts['tenant']:
            tenants = list(Tenant.objects.filter(code=opts['tenant']))
        else:
            tenants = list(Tenant.objects.filter(status='ACTIVE')) or list(Tenant.objects.all())
        if not tenants:
            self.stderr.write('No tenants found — create one first.')
            return

        if opts['reset']:
            n = AlertRule.objects.filter(tenant__in=tenants).delete()[0]
            self.stdout.write(self.style.WARNING(f'Reset: deleted {n} existing alert rules'))

        created = 0
        updated = 0
        for tenant in tenants:
            for name, desc, cat, rtype, thresh, win, sev in RULES:
                obj, was_created = AlertRule.objects.update_or_create(
                    tenant=tenant,
                    name=name,
                    defaults=dict(
                        description=desc,
                        category=cat,
                        rule_type=rtype,
                        threshold=thresh,
                        time_window_minutes=win,
                        severity=sev,
                        notify_method='BOTH',
                        notify_emails=opts['email'],
                        is_active=True,
                    ),
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            self.stdout.write(f'  Tenant {tenant.code}: {len(RULES)} rules ensured')

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {len(RULES)} rules across {len(tenants)} tenant(s): '
            f'created={created}  updated={updated}  email={opts["email"]}'
        ))
