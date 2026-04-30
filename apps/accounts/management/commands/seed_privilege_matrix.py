"""
Management command: Seed the Privilege Matrix

Creates Permission records for every feature in the LMS, then builds
standard Roles with the appropriate permission sets.

Usage:
    python manage.py seed_privilege_matrix
    python manage.py seed_privilege_matrix --reset   # delete & recreate
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role, RolePermission


# ═══════════════════════════════════════════════════════════════════
# FULL LMS FEATURE → PERMISSION MAP
# ═══════════════════════════════════════════════════════════════════
# Each entry: (module, category, resource, actions, scope)
#   actions = list of Action enum values
#   scope   = default scope for the permission

FEATURE_PERMISSIONS = [
    # ── Academics ──────────────────────────────────────────────────
    ('academics', 'sessions',         'academic_session',  ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'groups',           'group',             ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'categories',       'category',          ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'subjects',         'subject',           ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'chapters',         'chapter',           ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'topics',           'topic',             ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('academics', 'batches',          'batch',             ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'TENANT'),
    ('academics', 'enrollment',       'users',             ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'BATCH'),
    ('academics', 'assignment',       'batch_teacher',     ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'BATCH'),
    ('academics', 'reference',        'language',          ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('academics', 'reference',        'state',             ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('academics', 'reference',        'city',              ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('academics', 'reference',        'school',            ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),

    # ── Assessments ────────────────────────────────────────────────
    ('assessments', 'tests',          'test',              ['CREATE', 'READ', 'UPDATE', 'DELETE', 'APPROVE', 'EXPORT'], 'TENANT'),
    ('assessments', 'sections',       'test_section',      ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('assessments', 'questions',      'question',          ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'TENANT'),
    ('assessments', 'attempts',       'test_attempt',      ['READ', 'EXPORT'],                       'BATCH'),
    ('assessments', 'answers',        'test_attempt_answer', ['READ'],                               'BATCH'),
    ('assessments', 'feedback',       'test_feedback',     ['CREATE', 'READ'],                       'BATCH'),
    ('assessments', 'offline',        'offline_test_marks', ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'BATCH'),

    # ── Attendance ─────────────────────────────────────────────────
    ('attendance', 'records',         'attendance',        ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'BATCH'),
    ('attendance', 'corrections',     'correction_request', ['CREATE', 'READ', 'APPROVE'],           'BATCH'),
    ('attendance', 'summaries',       'attendance_summary', ['READ', 'EXPORT'],                      'TENANT'),

    # ── Classes ────────────────────────────────────────────────────
    ('classes', 'youtube',            'youtube_channel',   ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('classes', 'scheduling',         'scheduled_class',   ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE'], 'BATCH'),
    ('classes', 'access',             'class_access_token', ['CREATE', 'READ'],                     'BATCH'),
    ('classes', 'watchtime',          'class_watch_time',  ['READ', 'EXPORT'],                      'BATCH'),

    # ── Communication ──────────────────────────────────────────────
    ('communication', 'tickets',      'support_ticket',    ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('communication', 'tickets',      'ticket_message',    ['CREATE', 'READ'],                      'OWN'),
    ('communication', 'announcements', 'announcement',     ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('communication', 'messaging',    'direct_message',    ['CREATE', 'READ', 'DELETE'],             'OWN'),
    ('communication', 'notifications', 'notification',     ['CREATE', 'READ', 'UPDATE'],             'TENANT'),

    # ── Materials ──────────────────────────────────────────────────
    ('materials', 'content',          'study_material',    ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'TENANT'),
    ('materials', 'access',           'material_access',   ['READ', 'EXPORT'],                      'TENANT'),
    ('materials', 'gallery',          'photo_gallery',     ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('materials', 'scholarship',      'scholarship',       ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('materials', 'toppers',          'topper_student',    ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),

    # ── Sessions ───────────────────────────────────────────────────
    ('sessions', 'devices',           'user_device',       ['READ', 'DELETE'],                       'TENANT'),
    ('sessions', 'sessions',          'user_session',      ['READ', 'DELETE'],                       'TENANT'),
    ('sessions', 'login_history',     'login_history',     ['READ', 'EXPORT'],                       'TENANT'),
    ('sessions', 'activity',          'user_activity',     ['READ', 'EXPORT'],                       'TENANT'),

    # ── User Management ───────────────────────────────────────────
    ('user_account', 'students',      'student',           ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'TENANT'),
    ('user_account', 'teachers',      'teacher',           ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'TENANT'),
    ('user_account', 'admins',        'admin',             ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('user_account', 'parents',       'parent',            ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('user_account', 'roles',         'role',              ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('user_account', 'permissions',   'permission',        ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('user_account', 'groups',        'user_group',        ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('user_account', 'assignment',    'role_assignment',   ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'TENANT'),
    ('user_account', 'security',      'security_policy',   ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('user_account', 'security',      'trusted_device',    ['READ', 'DELETE'],                       'TENANT'),

    # ── Access Control ─────────────────────────────────────────────
    ('access_control', 'abac',        'abac_policy',       ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('access_control', 'evaluation',  'access_log',        ['READ', 'EXPORT'],                      'TENANT'),
    ('access_control', 'evaluation',  'access_evaluation', ['EXECUTE'],                              'GLOBAL'),

    # ── Audit ──────────────────────────────────────────────────────
    ('audit', 'logs',                 'audit_log',         ['READ', 'EXPORT'],                      'TENANT'),
    ('audit', 'retention',            'retention_policy',  ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('audit', 'backup',              'backup_policy',      ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('audit', 'backup',              'backup_record',      ['READ', 'EXPORT'],                      'GLOBAL'),

    # ── Analytics & Behavior ───────────────────────────────────────
    ('analytics', 'behavior',         'behavior_event',    ['READ', 'EXPORT'],                      'TENANT'),
    ('analytics', 'anomaly',          'anomaly_rule',      ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('analytics', 'anomaly',          'anomaly_alert',     ['READ', 'UPDATE', 'EXPORT'],             'TENANT'),

    # ── Compliance ─────────────────────────────────────────────────
    ('compliance', 'rules',           'compliance_rule',   ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('compliance', 'consent',         'consent_record',    ['CREATE', 'READ', 'EXPORT'],             'TENANT'),
    ('compliance', 'dsar',            'data_access_request', ['CREATE', 'READ', 'UPDATE', 'EXPORT'], 'TENANT'),

    # ── System Config ──────────────────────────────────────────────
    ('system', 'settings',            'system_setting',    ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('system', 'features',            'feature_flag',      ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('system', 'mfa',                 'mfa_policy',        ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('system', 'maintenance',         'maintenance_window', ['CREATE', 'READ', 'UPDATE', 'DELETE'], 'GLOBAL'),
    ('system', 'website',             'website_setting',   ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
    ('system', 'integrations',        'integration_config', ['CREATE', 'READ', 'UPDATE', 'DELETE'], 'GLOBAL'),
    ('system', 'reports',             'report_template',   ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT'], 'GLOBAL'),
    ('system', 'ai',                  'ai_feature_config', ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),

    # ── Tenants ────────────────────────────────────────────────────
    ('tenants', 'management',         'tenant',            ['CREATE', 'READ', 'UPDATE', 'DELETE'],  'GLOBAL'),
]


# ═══════════════════════════════════════════════════════════════════
# STANDARD ROLE DEFINITIONS (level defines hierarchy)
# ═══════════════════════════════════════════════════════════════════

ROLE_DEFINITIONS = [
    {
        'code': 'SUPER_ADMIN',
        'name': 'Super Administrator',
        'description': 'Full unrestricted access to every feature and resource across the platform.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 100,
        'permissions': '__ALL__',  # special: gets every permission
    },
    {
        'code': 'TENANT_ADMIN',
        'name': 'Tenant Administrator',
        'description': 'Full access within a single tenant — manages users, academics, assessments, communication.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 90,
        'parent': 'SUPER_ADMIN',
        'permissions': [
            'academics', 'assessments', 'attendance', 'classes',
            'communication', 'materials', 'sessions', 'user_account',
        ],
    },
    {
        'code': 'ACADEMIC_ADMIN',
        'name': 'Academic Administrator',
        'description': 'Manages academic structure, batches, subjects, tests, attendance.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 80,
        'parent': 'TENANT_ADMIN',
        'permissions': [
            'academics', 'assessments', 'attendance', 'classes', 'materials',
        ],
    },
    {
        'code': 'DEPARTMENT_ADMIN',
        'name': 'Department Administrator',
        'description': 'Manages a department — subjects, teachers, attendance within scope.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 70,
        'parent': 'ACADEMIC_ADMIN',
        'permissions': ['academics', 'attendance', 'classes'],
    },
    {
        'code': 'TEACHER_FULL',
        'name': 'Teacher (Full)',
        'description': 'Full teaching capabilities — create classes, tests, grade, attendance.',
        'role_type': 'SYSTEM',
        'applies_to': 'TEACHER',
        'level': 50,
        'permissions': '__TEACHER__',
    },
    {
        'code': 'TEACHING_ASSISTANT',
        'name': 'Teaching Assistant',
        'description': 'Assists teachers — view classes, take attendance, view results.',
        'role_type': 'SYSTEM',
        'applies_to': 'TEACHING_ASSISTANT',
        'level': 40,
        'parent': 'TEACHER_FULL',
        'permissions': '__TA__',
    },
    {
        'code': 'STUDENT_STANDARD',
        'name': 'Student (Standard)',
        'description': 'Standard student access — view classes, take tests, view materials, own profile.',
        'role_type': 'SYSTEM',
        'applies_to': 'STUDENT',
        'level': 10,
        'permissions': '__STUDENT__',
    },
    {
        'code': 'PARENT_VIEWER',
        'name': 'Parent / Guardian',
        'description': 'View child attendance, results, communicate with teachers.',
        'role_type': 'SYSTEM',
        'applies_to': 'PARENT',
        'level': 5,
        'permissions': '__PARENT__',
    },
    {
        'code': 'AUDITOR',
        'name': 'Auditor',
        'description': 'Read-only access to audit logs, compliance rules, behavior analytics, and access evaluations.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 60,
        'permissions': ['audit', 'compliance', 'analytics', 'access_control'],
    },
    {
        'code': 'SECURITY_OFFICER',
        'name': 'Security Officer',
        'description': 'Manages security policies, reviews anomaly alerts, evaluates access decisions.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 65,
        'permissions': [
            'audit', 'analytics', 'access_control',
            'user_account:security', 'sessions',
        ],
    },
    {
        'code': 'COMPLIANCE_OFFICER',
        'name': 'Compliance & Data Governance Officer',
        'description': 'Manages compliance rules, consent records, data access requests, retention policies.',
        'role_type': 'SYSTEM',
        'applies_to': 'ADMIN',
        'level': 60,
        'permissions': ['compliance', 'audit:retention', 'audit:backup'],
    },
]


# ═══════════════════════════════════════════════════════════════════
# TEACHER / TA / STUDENT / PARENT permission filters
# ═══════════════════════════════════════════════════════════════════

TEACHER_PERMISSION_FILTERS = [
    ('assessments', 'tests',     ['CREATE', 'READ', 'UPDATE']),
    ('assessments', 'sections',  ['CREATE', 'READ', 'UPDATE']),
    ('assessments', 'questions', ['CREATE', 'READ', 'UPDATE']),
    ('assessments', 'attempts',  ['READ']),
    ('assessments', 'feedback',  ['CREATE', 'READ']),
    ('assessments', 'offline',   ['CREATE', 'READ', 'UPDATE']),
    ('attendance',  'records',   ['CREATE', 'READ', 'UPDATE']),
    ('attendance',  'corrections', ['READ', 'APPROVE']),
    ('attendance',  'summaries', ['READ']),
    ('classes',     'scheduling', ['CREATE', 'READ', 'UPDATE']),
    ('classes',     'access',    ['CREATE', 'READ']),
    ('classes',     'watchtime', ['READ']),
    ('communication', 'announcements', ['CREATE', 'READ']),
    ('communication', 'messaging', ['CREATE', 'READ']),
    ('communication', 'notifications', ['READ']),
    ('materials',   'content',   ['CREATE', 'READ', 'UPDATE']),
]

TA_PERMISSION_FILTERS = [
    ('assessments', 'attempts',  ['READ']),
    ('assessments', 'feedback',  ['READ']),
    ('attendance',  'records',   ['CREATE', 'READ']),
    ('attendance',  'summaries', ['READ']),
    ('classes',     'scheduling', ['READ']),
    ('classes',     'watchtime', ['READ']),
    ('communication', 'announcements', ['READ']),
    ('communication', 'notifications', ['READ']),
    ('materials',   'content',   ['READ']),
]

STUDENT_PERMISSION_FILTERS = [
    ('assessments', 'attempts',  ['READ']),
    ('attendance',  'summaries', ['READ']),
    ('classes',     'scheduling', ['READ']),
    ('classes',     'watchtime', ['READ']),
    ('communication', 'messaging', ['CREATE', 'READ']),
    ('communication', 'notifications', ['READ']),
    ('materials',   'content',   ['READ']),
    ('materials',   'access',    ['READ']),
]

PARENT_PERMISSION_FILTERS = [
    ('attendance',  'summaries', ['READ']),
    ('assessments', 'attempts',  ['READ']),
    ('communication', 'messaging', ['CREATE', 'READ']),
    ('communication', 'notifications', ['READ']),
]


class Command(BaseCommand):
    help = 'Seed the privilege matrix with all LMS feature permissions and standard roles.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete existing system permissions and roles before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting system permissions and roles...'))
            RolePermission.objects.filter(role__role_type='SYSTEM').delete()
            Role.objects.filter(role_type='SYSTEM').delete()
            Permission.objects.filter(code__startswith='lms:').delete()
            self.stdout.write(self.style.SUCCESS('  Cleared.'))

        # ── Step 1: Create Permissions ─────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n1. Creating Feature Permissions...'))
        perm_map = {}  # code → Permission instance
        created_count = 0
        skipped_count = 0

        for module, category, resource, actions, scope in FEATURE_PERMISSIONS:
            for action in actions:
                code = f"lms:{module}:{category}:{resource}:{action.lower()}"
                name = f"{module.replace('_', ' ').title()} — {category.title()} — {resource.replace('_', ' ').title()} — {action}"

                perm, created = Permission.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'description': f'Permission to {action} {resource} in {module}/{category}',
                        'module': module,
                        'category': category,
                        'resource': resource,
                        'action': action,
                        'scope': scope,
                        'is_active': True,
                    },
                )
                perm_map[code] = perm
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(
            f'   Created: {created_count}  |  Already existed: {skipped_count}  |  '
            f'Total: {Permission.objects.count()}'
        )

        # ── Step 2: Create Roles ───────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n2. Creating Standard Roles...'))
        role_map = {}

        for rdef in ROLE_DEFINITIONS:
            parent = None
            if 'parent' in rdef:
                parent = role_map.get(rdef['parent'])

            role, created = Role.objects.get_or_create(
                code=rdef['code'],
                tenant=None,
                defaults={
                    'name': rdef['name'],
                    'description': rdef['description'],
                    'role_type': rdef['role_type'],
                    'applies_to': rdef['applies_to'],
                    'level': rdef['level'],
                    'parent_role': parent,
                    'is_active': True,
                },
            )
            if not created and parent:
                role.parent_role = parent
                role.save(update_fields=['parent_role'])

            role_map[rdef['code']] = role
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'   [{status}] L{rdef["level"]:>3d}  {rdef["code"]} — {rdef["name"]}')

        # ── Step 3: Assign permissions to roles ────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n3. Assigning Permissions to Roles...'))
        all_perms = list(perm_map.values())

        for rdef in ROLE_DEFINITIONS:
            role = role_map[rdef['code']]
            perm_spec = rdef['permissions']
            perms_to_assign = []

            if perm_spec == '__ALL__':
                perms_to_assign = all_perms
            elif perm_spec == '__TEACHER__':
                perms_to_assign = self._filter_perms(perm_map, TEACHER_PERMISSION_FILTERS)
            elif perm_spec == '__TA__':
                perms_to_assign = self._filter_perms(perm_map, TA_PERMISSION_FILTERS)
            elif perm_spec == '__STUDENT__':
                perms_to_assign = self._filter_perms(perm_map, STUDENT_PERMISSION_FILTERS)
            elif perm_spec == '__PARENT__':
                perms_to_assign = self._filter_perms(perm_map, PARENT_PERMISSION_FILTERS)
            elif isinstance(perm_spec, list):
                for spec in perm_spec:
                    if ':' in spec:
                        # module:category filter
                        module, category = spec.split(':', 1)
                        perms_to_assign.extend(
                            p for code, p in perm_map.items()
                            if code.startswith(f'lms:{module}:{category}:')
                        )
                    else:
                        # module-level filter
                        perms_to_assign.extend(
                            p for code, p in perm_map.items()
                            if code.startswith(f'lms:{spec}:')
                        )

            assigned = 0
            for perm in perms_to_assign:
                _, created = RolePermission.objects.get_or_create(
                    role=role, permission=perm,
                )
                if created:
                    assigned += 1

            self.stdout.write(
                f'   {rdef["code"]}: {assigned} new assignments '
                f'(total: {role.role_permissions.count()})'
            )

        # ── Summary ────────────────────────────────────────────────
        total_perms = Permission.objects.filter(code__startswith='lms:').count()
        total_roles = Role.objects.filter(role_type='SYSTEM').count()
        total_assignments = RolePermission.objects.filter(role__role_type='SYSTEM').count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Privilege Matrix seeded successfully!\n'
            f'  Permissions : {total_perms}\n'
            f'  Roles       : {total_roles}\n'
            f'  Assignments : {total_assignments}\n'
        ))

    @staticmethod
    def _filter_perms(perm_map, filters):
        """Filter permissions by (module, category, [actions]) tuples."""
        result = []
        for module, category, actions in filters:
            for action in actions:
                code = None
                # Find matching permission codes
                for c, p in perm_map.items():
                    if (c.startswith(f'lms:{module}:{category}:')
                            and c.endswith(f':{action.lower()}')):
                        result.append(p)
        return result
