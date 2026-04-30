"""Seed the default Role catalogue used by the LMS.

Creates SYSTEM roles for Students, Teachers, Parents and every tier of staff.
Idempotent — safe to run multiple times; existing rows are updated, never
duplicated.

Usage::

    python manage.py seed_default_roles              # global (tenant=NULL)
    python manage.py seed_default_roles --tenant ABC # scoped to one tenant
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role


# ── Role catalogue ─────────────────────────────────────────────────────
# (code, name, applies_to, level, description)
DEFAULT_ROLES = [
    # ── Students ──
    ('STUDENT_ACTIVE',     'Student',                  'STUDENT', 10,
     'Enrolled student — can view own profile, class materials, attendance, tests.'),
    ('STUDENT_ALUMNI',     'Alumni Student',           'STUDENT', 8,
     'Graduated / passed-out student with read-only access to their historic records.'),

    # ── Parents ──
    ('PARENT_PRIMARY',     'Parent — Primary',         'PARENT', 12,
     'Primary parent/guardian — receives notices, sees child progress and fees.'),
    ('PARENT_SECONDARY',   'Parent — Secondary',       'PARENT', 10,
     'Secondary parent/guardian with read-only visibility into their child.'),

    # ── Teachers ──
    ('TEACHER_PRIMARY',    'Teacher',                  'TEACHER', 40,
     'Class teacher — can manage own class attendance, marks, materials, and notes.'),
    ('TEACHER_ASSISTANT',  'Teaching Assistant',       'TEACHING_ASSISTANT', 30,
     'Supports a primary teacher; can draft materials and mark attendance only.'),
    ('TEACHER_SUBJECT_HEAD','Subject Head',            'TEACHER', 50,
     'Leads a subject department — oversees syllabus, assessments, and reporting.'),

    # ── Staff (non-admin operations) ──
    ('STAFF_ACADEMIC',     'Academic Operator',        'ADMIN', 55,
     'Daily academic operations — admissions, batch assignment, class schedules.'),
    ('STAFF_ATTENDANCE',   'Attendance Officer',       'ADMIN', 55,
     'Can view and correct attendance records, run reports, export data.'),
    ('STAFF_EXAM',         'Exam Coordinator',         'ADMIN', 60,
     'Creates and schedules tests/exams, publishes results. No finance access.'),
    ('STAFF_FINANCE',      'Finance Officer',          'ADMIN', 60,
     'Manages fees, invoices, refunds, scholarships. Read-only on academic data.'),
    ('STAFF_CONTENT',      'Content Curator',          'ADMIN', 55,
     'Uploads and organises study materials, notes, recorded lectures.'),
    ('STAFF_FRONTDESK',    'Front Desk / Reception',   'ADMIN', 50,
     'Enquiries, walk-ins, student id cards — limited edit on student profile.'),
    ('STAFF_COUNSELLOR',   'Counsellor',               'ADMIN', 55,
     'Academic + career counselling, reads student history, writes case notes.'),
    ('STAFF_REPORTS',      'Reports & Analytics',      'ADMIN', 55,
     'Read-only + export across students / teachers / batches for MIS reporting.'),

    # ── Admin tiers ──
    ('ADMIN_BRANCH',       'Branch Administrator',     'ADMIN', 75,
     'Full admin rights scoped to one branch / school.'),
    ('ADMIN_TENANT',       'Tenant Administrator',     'ADMIN', 85,
     'Full admin rights for the whole tenant (all branches).'),
    ('ADMIN_SUPER',        'Super Administrator',      'ADMIN', 100,
     'Platform-level super admin — cross-tenant access. Reserved for vendors.'),
]


class Command(BaseCommand):
    help = 'Seed the default Role rows used by the LMS (students/teachers/staff/admin).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant', dest='tenant_code', default=None,
            help='Optional tenant code — roles are scoped to that tenant. '
                 'Omit to create global SYSTEM roles with tenant=NULL.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would change without writing to the database.'
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        tenant = None
        if opts['tenant_code']:
            from tenants.models import Tenant
            tenant = Tenant.objects.get(code=opts['tenant_code'])
            self.stdout.write(f'Seeding roles for tenant {tenant.code} ({tenant.name})')
        else:
            self.stdout.write('Seeding GLOBAL (tenant=NULL) SYSTEM roles')

        created, updated = 0, 0
        for code, name, applies_to, level, description in DEFAULT_ROLES:
            defaults = {
                'name': name,
                'applies_to': applies_to,
                'level': level,
                'description': description,
                'role_type': 'SYSTEM' if tenant is None else 'TENANT_DEFAULT',
                'is_active': True,
            }
            if opts['dry_run']:
                exists = Role.objects.filter(tenant=tenant, code=code).exists()
                self.stdout.write(('  [upd] ' if exists else '  [new] ') + code)
                continue
            obj, was_created = Role.objects.update_or_create(
                tenant=tenant, code=code, defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. created={created} updated={updated} '
            f'(total catalogue={len(DEFAULT_ROLES)})'
        ))
