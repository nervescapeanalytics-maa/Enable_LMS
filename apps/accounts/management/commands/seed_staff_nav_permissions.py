"""
Seed the NavMenuPermission table with the authoritative catalog of
sidebar codes and sensible defaults for each StaffRole level.

Run with:

    python manage.py seed_staff_nav_permissions          # idempotent upsert
    python manage.py seed_staff_nav_permissions --reset  # wipe & re-seed
    python manage.py seed_staff_nav_permissions --print  # just print catalog

The catalog (`NAV_CATALOG`) is the single source of truth and is also
imported by ``accounts.context_processors`` for the "show all" fallback
and section-visibility computation.

Code namespacing:  nav.<section_key>.<item_key>
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


# ---------------------------------------------------------------------------
# Authoritative nav catalog.  Adding a new sidebar entry?  Add it here AND
# in the template, then re-run this command.
# ---------------------------------------------------------------------------
NAV_CATALOG: dict = {
    'overview': {
        'label': 'Overview',
        'items': {
            'nav.overview.dashboard':  'Dashboard',
            'nav.overview.monitoring': 'Monitoring Center',
        },
    },
    'master': {
        'label': 'Master',
        'items': {
            'nav.master.subjects': 'Subject Section',
            'nav.master.batches':  'Batches',
            'nav.master.programs': 'Programs',
            'nav.master.sessions': 'Academic Sessions',
        },
    },
    'exams': {
        'label': 'Exams & Assessments',
        'items': {
            'nav.exams.list':      'Exams',
            'nav.exams.questions': 'Question Bank',
            'nav.exams.import':    'Bulk Import',
            'nav.exams.flags':     'Feature Flags',
        },
    },
    'analytics': {
        'label': 'Analytics & Alerting',
        'items': {
            'nav.analytics.exam_reports':    'Exam Reports',
            'nav.analytics.ai_insights':     'AI Insights',
            'nav.analytics.underperformers': 'Underperformer Alerts',
            'nav.analytics.thresholds':      'Thresholds',
        },
    },
    'school': {
        'label': 'School / Centers',
        'items': {
            'nav.school.schools':            'Schools',
            'nav.school.teachers':           'Teachers',
            'nav.school.teacher_attendance': 'Teacher Attendance',
        },
    },
    'students': {
        'label': 'Students',
        'items': {
            'nav.students.list':       'All Students',
            'nav.students.attendance': 'Student Attendance',
        },
    },
    'study': {
        'label': 'Study Material',
        'items': {
            'nav.study.live_classes': 'Live Classes',
            'nav.study.materials':    'Study Materials',
        },
    },
    'comm': {
        'label': 'Communication',
        'items': {
            'nav.comm.announcements': 'Announcements',
            'nav.comm.tickets':       'Support Tickets',
        },
    },
    'system': {
        'label': 'System',
        'items': {
            'nav.system.staff_roles':      'Staff Roles',
            'nav.system.integrations':     'Integrations',
            'nav.system.reports':          'Reports Center',
            'nav.system.website_settings': 'Website Settings',
            'nav.system.ai_features':      'AI Features',
            'nav.system.compliance':       'Audit & Compliance',
            'nav.system.dashboards':       'Dashboards',
            'nav.system.tenants':          'Tenants / Centers',
        },
    },
}


# ---------------------------------------------------------------------------
# Default code grants per StaffLevel.
# SUPER_ADMIN is intentionally NOT seeded here because the context processor
# treats SUPER_ADMIN as "see everything" without any DB rows.  Seeding it
# anyway makes the audit-log query trivial.
# ---------------------------------------------------------------------------
def _all_codes() -> set[str]:
    out: set[str] = set()
    for section in NAV_CATALOG.values():
        out.update(section['items'].keys())
    return out


DEFAULTS_BY_LEVEL: dict[str, set[str]] = {
    # Total visibility.
    'SUPER_ADMIN': _all_codes(),

    # Day-to-day administrator: everything except platform-level system pages.
    'ADMIN': _all_codes() - {
        'nav.system.tenants',
        'nav.system.staff_roles',
        'nav.system.compliance',
        'nav.system.website_settings',
    },

    # Floor operator: only what a centre operator needs to run the day.
    'OPERATOR': {
        'nav.overview.dashboard',
        'nav.overview.monitoring',
        'nav.master.batches',
        'nav.master.sessions',
        'nav.exams.list',
        'nav.school.teachers',
        'nav.school.teacher_attendance',
        'nav.students.list',
        'nav.students.attendance',
        'nav.study.live_classes',
        'nav.study.materials',
        'nav.comm.announcements',
        'nav.comm.tickets',
    },
}


class Command(BaseCommand):
    help = 'Seed NavMenuPermission rows for every StaffRole using the default catalog.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Wipe existing NavMenuPermission rows before seeding.')
        parser.add_argument('--print', action='store_true', dest='print_only',
                            help='Print the catalog and exit (no DB writes).')

    def handle(self, *args, **opts):
        if opts.get('print_only'):
            self._print_catalog()
            return

        # Local imports so management-command discovery never fails when
        # migrations haven't yet been applied.
        from accounts.models import StaffRole, NavMenuPermission

        with transaction.atomic():
            if opts['reset']:
                deleted, _ = NavMenuPermission.objects.all().delete()
                self.stdout.write(self.style.WARNING(
                    f'Deleted {deleted} existing NavMenuPermission rows.'))

            roles = StaffRole.objects.filter(is_active=True)
            if not roles.exists():
                self.stdout.write(self.style.WARNING(
                    'No active StaffRole rows found — nothing to seed.'))
                return

            created_total = 0
            existing_total = 0
            for role in roles:
                codes = DEFAULTS_BY_LEVEL.get(role.level, set())
                for code in codes:
                    _, created = NavMenuPermission.objects.get_or_create(
                        staff_role=role, code=code,
                    )
                    if created:
                        created_total += 1
                    else:
                        existing_total += 1
                self.stdout.write(
                    f'  {role.level:<12} {role.name:<35} '
                    f'-> {len(codes)} codes')

            self.stdout.write(self.style.SUCCESS(
                f'Done. Created {created_total} new rows, '
                f'{existing_total} already present.'))

    def _print_catalog(self):
        for section_key, section in NAV_CATALOG.items():
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'[{section_key}] {section["label"]}'))
            for code, label in section['items'].items():
                self.stdout.write(f'  {code:<40} {label}')
