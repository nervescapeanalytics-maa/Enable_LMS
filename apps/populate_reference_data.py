#!/usr/bin/env python
"""
Populate comprehensive reference data: Roles, Permissions, StaffRoles,
UserGroups, SecurityPolicies, ComplianceRules, FeatureFlags, SystemSettings
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings.production')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from accounts.models import (
    Role, Permission, RolePermission, StaffRole, UserGroup,
    SecurityPolicy, ComplianceRule, ABACPolicy,
)
from system_config.models import FeatureFlag, SystemSetting
from tenants.models import Tenant

now = timezone.now()
tenant = Tenant.objects.get(id='f883ed57-6f3a-40fa-b7f8-f0eebcd7e04c')

print("=" * 60)
print("POPULATING REFERENCE DATA")
print("=" * 60)

# ════════════════════════════════════════════════════════════
# 1. ROLES
# ════════════════════════════════════════════════════════════
roles_data = [
    # System-level roles (tenant=None)
    {'code': 'SYS_SUPER_ADMIN',      'name': 'System Super Administrator',    'role_type': 'SYSTEM',         'applies_to': 'ADMIN',    'level': 100, 'description': 'Full system access across all tenants. Can manage platform configuration, tenants, and all data.', 'tenant': None},
    {'code': 'SYS_PLATFORM_ADMIN',   'name': 'Platform Administrator',        'role_type': 'SYSTEM',         'applies_to': 'ADMIN',    'level': 90,  'description': 'Manages platform-wide settings, monitoring, and tenant provisioning.', 'tenant': None},
    # Tenant-level admin roles
    {'code': 'TENANT_ADMIN',         'name': 'Tenant Administrator',          'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 80,  'description': 'Full administrative access within a single tenant/institute.'},
    {'code': 'ACADEMIC_ADMIN',       'name': 'Academic Administrator',        'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 70,  'description': 'Manages academic configuration — sessions, subjects, chapters, batches, and exam settings.'},
    {'code': 'FINANCE_ADMIN',        'name': 'Finance Administrator',         'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 70,  'description': 'Manages fee structures, payment tracking, financial reports, and invoicing.'},
    {'code': 'HR_ADMIN',             'name': 'HR & Staff Administrator',      'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 65,  'description': 'Manages teacher and staff profiles, attendance, leave, and payroll.'},
    {'code': 'CONTENT_ADMIN',        'name': 'Content Administrator',         'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 60,  'description': 'Manages study materials, video content, photo galleries, and library resources.'},
    {'code': 'SUPPORT_ADMIN',        'name': 'Support Administrator',         'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 50,  'description': 'Handles support tickets, student enquiries, and communication.'},
    {'code': 'EXAM_COORDINATOR',     'name': 'Exam Coordinator',              'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 55,  'description': 'Creates and manages tests, exam schedules, question papers, and result publishing.'},
    {'code': 'BRANCH_ADMIN',         'name': 'Branch Administrator',          'role_type': 'TENANT_DEFAULT', 'applies_to': 'ADMIN',    'level': 60,  'description': 'Manages operations for a specific branch or center of the institute.'},
    {'code': 'REPORT_VIEWER',        'name': 'Report Viewer',                 'role_type': 'CUSTOM',         'applies_to': 'ADMIN',    'level': 30,  'description': 'Read-only access to reports, analytics, and dashboards.'},
    {'code': 'DATA_ENTRY_OPERATOR',  'name': 'Data Entry Operator',           'role_type': 'CUSTOM',         'applies_to': 'ADMIN',    'level': 20,  'description': 'Can enter and update student/teacher data, attendance, and marks.'},
    # Teacher roles
    {'code': 'HEAD_TEACHER',         'name': 'Head Teacher',                  'role_type': 'TENANT_DEFAULT', 'applies_to': 'TEACHER',  'level': 75,  'description': 'Senior teacher with oversight of all academic activities, teacher assignments, and content review.'},
    {'code': 'SENIOR_TEACHER',       'name': 'Senior Teacher',                'role_type': 'TENANT_DEFAULT', 'applies_to': 'TEACHER',  'level': 60,  'description': 'Experienced teacher who can manage batches, create tests, and review other teachers\' content.'},
    {'code': 'TEACHER',              'name': 'Teacher',                       'role_type': 'TENANT_DEFAULT', 'applies_to': 'TEACHER',  'level': 50,  'description': 'Regular teacher — conducts classes, creates tests, marks attendance, manages study materials.'},
    {'code': 'TEACHING_ASSISTANT',   'name': 'Teaching Assistant',            'role_type': 'TENANT_DEFAULT', 'applies_to': 'TEACHING_ASSISTANT', 'level': 30, 'description': 'Assists teachers with attendance, doubt clearing, and administrative tasks.'},
    {'code': 'GUEST_LECTURER',       'name': 'Guest Lecturer',                'role_type': 'CUSTOM',         'applies_to': 'TEACHER',  'level': 25,  'description': 'Temporary teacher with limited access — can only conduct assigned classes.'},
    {'code': 'CONTENT_CREATOR',      'name': 'Content Creator',               'role_type': 'CUSTOM',         'applies_to': 'TEACHER',  'level': 40,  'description': 'Creates study materials, videos, and question banks but doesn\'t take classes.'},
    # Student roles
    {'code': 'STUDENT',              'name': 'Student',                       'role_type': 'TENANT_DEFAULT', 'applies_to': 'STUDENT',  'level': 10,  'description': 'Regular student — can access classes, materials, tests, and view own performance.'},
    {'code': 'STUDENT_LEADER',       'name': 'Class Monitor / Student Leader','role_type': 'CUSTOM',         'applies_to': 'STUDENT',  'level': 15,  'description': 'Student with additional privileges like viewing batch attendance and posting announcements.'},
    {'code': 'TRIAL_STUDENT',        'name': 'Trial Student',                 'role_type': 'CUSTOM',         'applies_to': 'STUDENT',  'level': 5,   'description': 'Limited-time trial access — can view demo classes and materials only.'},
    # Parent roles
    {'code': 'PARENT',               'name': 'Parent / Guardian',             'role_type': 'TENANT_DEFAULT', 'applies_to': 'PARENT',   'level': 10,  'description': 'Can view child\'s attendance, test results, fee status, and communicate with teachers.'},
    {'code': 'PARENT_COMMITTEE',     'name': 'Parent Committee Member',       'role_type': 'CUSTOM',         'applies_to': 'PARENT',   'level': 20,  'description': 'Parent with additional access to batch-level reports and announcement posting.'},
]

created_roles = {}
for rd in roles_data:
    t = rd.pop('tenant', tenant)
    role, created = Role.objects.update_or_create(
        code=rd['code'], tenant=t if t else None,
        defaults={**rd, 'tenant': t if t else None, 'is_active': True}
    )
    created_roles[rd['code']] = role
    print(f"  {'✓ Created' if created else '→ Updated'} Role: {rd['code']} — {rd['name']}")

print(f"\n  Total roles: {Role.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 2. PERMISSIONS
# ════════════════════════════════════════════════════════════
permissions_data = [
    # ── STUDENT MODULE ──
    {'code': 'student:profile:read',       'name': 'View Student Profile',         'module': 'student',     'category': 'profile',     'resource': 'student',      'action': 'READ',    'scope': 'OWN'},
    {'code': 'student:profile:update',     'name': 'Edit Student Profile',         'module': 'student',     'category': 'profile',     'resource': 'student',      'action': 'UPDATE',  'scope': 'OWN'},
    {'code': 'student:profile:create',     'name': 'Create Student',               'module': 'student',     'category': 'profile',     'resource': 'student',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'student:profile:delete',     'name': 'Delete Student',               'module': 'student',     'category': 'profile',     'resource': 'student',      'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'student:list:read',          'name': 'View Student List',            'module': 'student',     'category': 'list',        'resource': 'student',      'action': 'READ',    'scope': 'TENANT'},
    {'code': 'student:export:execute',     'name': 'Export Student Data',          'module': 'student',     'category': 'export',      'resource': 'student',      'action': 'EXPORT',  'scope': 'TENANT'},
    {'code': 'student:import:execute',     'name': 'Import Student Data',          'module': 'student',     'category': 'import',      'resource': 'student',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'student:fee:read',           'name': 'View Student Fee Status',      'module': 'student',     'category': 'fee',         'resource': 'fee',          'action': 'READ',    'scope': 'BATCH'},
    {'code': 'student:fee:update',         'name': 'Update Student Fee Status',    'module': 'student',     'category': 'fee',         'resource': 'fee',          'action': 'UPDATE',  'scope': 'TENANT'},
    # ── TEACHER MODULE ──
    {'code': 'teacher:profile:read',       'name': 'View Teacher Profile',         'module': 'teacher',     'category': 'profile',     'resource': 'teacher',      'action': 'READ',    'scope': 'OWN'},
    {'code': 'teacher:profile:update',     'name': 'Edit Teacher Profile',         'module': 'teacher',     'category': 'profile',     'resource': 'teacher',      'action': 'UPDATE',  'scope': 'OWN'},
    {'code': 'teacher:profile:create',     'name': 'Create Teacher',               'module': 'teacher',     'category': 'profile',     'resource': 'teacher',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'teacher:profile:delete',     'name': 'Delete Teacher',               'module': 'teacher',     'category': 'profile',     'resource': 'teacher',      'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'teacher:list:read',          'name': 'View Teacher List',            'module': 'teacher',     'category': 'list',        'resource': 'teacher',      'action': 'READ',    'scope': 'TENANT'},
    {'code': 'teacher:export:execute',     'name': 'Export Teacher Data',          'module': 'teacher',     'category': 'export',      'resource': 'teacher',      'action': 'EXPORT',  'scope': 'TENANT'},
    # ── CLASS / SCHEDULING MODULE ──
    {'code': 'class:schedule:create',      'name': 'Create Scheduled Class',       'module': 'class',       'category': 'schedule',    'resource': 'class',        'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'class:schedule:read',        'name': 'View Class Schedule',          'module': 'class',       'category': 'schedule',    'resource': 'class',        'action': 'READ',    'scope': 'BATCH'},
    {'code': 'class:schedule:update',      'name': 'Update Class Schedule',        'module': 'class',       'category': 'schedule',    'resource': 'class',        'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'class:schedule:delete',      'name': 'Delete Scheduled Class',       'module': 'class',       'category': 'schedule',    'resource': 'class',        'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'class:live:execute',         'name': 'Conduct Live Class',           'module': 'class',       'category': 'live',        'resource': 'class',        'action': 'EXECUTE', 'scope': 'BATCH'},
    {'code': 'class:recording:read',       'name': 'View Class Recordings',        'module': 'class',       'category': 'recording',   'resource': 'recording',    'action': 'READ',    'scope': 'BATCH'},
    # ── ASSESSMENT / EXAM MODULE ──
    {'code': 'exam:test:create',           'name': 'Create Test / Exam',           'module': 'exam',        'category': 'test',        'resource': 'test',         'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'exam:test:read',             'name': 'View Test Details',            'module': 'exam',        'category': 'test',        'resource': 'test',         'action': 'READ',    'scope': 'BATCH'},
    {'code': 'exam:test:update',           'name': 'Edit Test / Exam',             'module': 'exam',        'category': 'test',        'resource': 'test',         'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'exam:test:delete',           'name': 'Delete Test / Exam',           'module': 'exam',        'category': 'test',        'resource': 'test',         'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'exam:question:create',       'name': 'Create Question',              'module': 'exam',        'category': 'question',    'resource': 'question',     'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'exam:question:read',         'name': 'View Question Bank',           'module': 'exam',        'category': 'question',    'resource': 'question',     'action': 'READ',    'scope': 'TENANT'},
    {'code': 'exam:attempt:read',          'name': 'View Test Attempts',           'module': 'exam',        'category': 'attempt',     'resource': 'attempt',      'action': 'READ',    'scope': 'BATCH'},
    {'code': 'exam:result:read',           'name': 'View Test Results',            'module': 'exam',        'category': 'result',      'resource': 'result',       'action': 'READ',    'scope': 'OWN'},
    {'code': 'exam:result:approve',        'name': 'Approve / Publish Results',    'module': 'exam',        'category': 'result',      'resource': 'result',       'action': 'APPROVE', 'scope': 'TENANT'},
    {'code': 'exam:marks:update',          'name': 'Enter Offline Test Marks',     'module': 'exam',        'category': 'marks',       'resource': 'marks',        'action': 'UPDATE',  'scope': 'BATCH'},
    {'code': 'exam:export:execute',        'name': 'Export Exam Data',             'module': 'exam',        'category': 'export',      'resource': 'exam',         'action': 'EXPORT',  'scope': 'TENANT'},
    # ── ATTENDANCE MODULE ──
    {'code': 'attendance:mark:create',     'name': 'Mark Attendance',              'module': 'attendance',  'category': 'mark',        'resource': 'attendance',   'action': 'CREATE',  'scope': 'BATCH'},
    {'code': 'attendance:mark:update',     'name': 'Update Attendance',            'module': 'attendance',  'category': 'mark',        'resource': 'attendance',   'action': 'UPDATE',  'scope': 'BATCH'},
    {'code': 'attendance:view:read',       'name': 'View Attendance Records',      'module': 'attendance',  'category': 'view',        'resource': 'attendance',   'action': 'READ',    'scope': 'OWN'},
    {'code': 'attendance:report:read',     'name': 'View Attendance Reports',      'module': 'attendance',  'category': 'report',      'resource': 'attendance',   'action': 'READ',    'scope': 'TENANT'},
    {'code': 'attendance:correction:create','name': 'Request Attendance Correction','module': 'attendance', 'category': 'correction',  'resource': 'correction',   'action': 'CREATE',  'scope': 'OWN'},
    {'code': 'attendance:correction:approve','name': 'Approve Attendance Correction','module': 'attendance','category': 'correction',  'resource': 'correction',   'action': 'APPROVE', 'scope': 'TENANT'},
    {'code': 'attendance:export:execute',  'name': 'Export Attendance Data',       'module': 'attendance',  'category': 'export',      'resource': 'attendance',   'action': 'EXPORT',  'scope': 'TENANT'},
    # ── MATERIAL / CONTENT MODULE ──
    {'code': 'material:content:create',    'name': 'Upload Study Material',        'module': 'material',    'category': 'content',     'resource': 'material',     'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'material:content:read',      'name': 'View Study Materials',         'module': 'material',    'category': 'content',     'resource': 'material',     'action': 'READ',    'scope': 'BATCH'},
    {'code': 'material:content:update',    'name': 'Edit Study Material',          'module': 'material',    'category': 'content',     'resource': 'material',     'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'material:content:delete',    'name': 'Delete Study Material',        'module': 'material',    'category': 'content',     'resource': 'material',     'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'material:gallery:create',    'name': 'Upload to Photo Gallery',      'module': 'material',    'category': 'gallery',     'resource': 'gallery',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'material:gallery:read',      'name': 'View Photo Gallery',           'module': 'material',    'category': 'gallery',     'resource': 'gallery',      'action': 'READ',    'scope': 'TENANT'},
    # ── COMMUNICATION MODULE ──
    {'code': 'comm:announcement:create',   'name': 'Create Announcement',          'module': 'communication','category': 'announcement','resource': 'announcement','action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'comm:announcement:read',     'name': 'View Announcements',           'module': 'communication','category': 'announcement','resource': 'announcement','action': 'READ',    'scope': 'TENANT'},
    {'code': 'comm:notification:create',   'name': 'Send Notification',            'module': 'communication','category': 'notification','resource': 'notification','action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'comm:message:create',        'name': 'Send Direct Message',          'module': 'communication','category': 'message',    'resource': 'message',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'comm:message:read',          'name': 'Read Messages',                'module': 'communication','category': 'message',    'resource': 'message',      'action': 'READ',    'scope': 'OWN'},
    {'code': 'comm:ticket:create',         'name': 'Create Support Ticket',        'module': 'communication','category': 'ticket',     'resource': 'ticket',       'action': 'CREATE',  'scope': 'OWN'},
    {'code': 'comm:ticket:read',           'name': 'View Support Tickets',         'module': 'communication','category': 'ticket',     'resource': 'ticket',       'action': 'READ',    'scope': 'TENANT'},
    {'code': 'comm:ticket:update',         'name': 'Manage Support Tickets',       'module': 'communication','category': 'ticket',     'resource': 'ticket',       'action': 'UPDATE',  'scope': 'TENANT'},
    # ── ACADEMIC CONFIG MODULE ──
    {'code': 'academic:session:create',    'name': 'Create Academic Session',      'module': 'academic',    'category': 'session',     'resource': 'session',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'academic:session:update',    'name': 'Update Academic Session',      'module': 'academic',    'category': 'session',     'resource': 'session',      'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'academic:subject:create',    'name': 'Create Subject',               'module': 'academic',    'category': 'subject',     'resource': 'subject',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'academic:subject:update',    'name': 'Update Subject',               'module': 'academic',    'category': 'subject',     'resource': 'subject',      'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'academic:chapter:create',    'name': 'Create Chapter',               'module': 'academic',    'category': 'chapter',     'resource': 'chapter',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'academic:chapter:update',    'name': 'Update Chapter',               'module': 'academic',    'category': 'chapter',     'resource': 'chapter',      'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'academic:batch:create',      'name': 'Create Batch',                 'module': 'academic',    'category': 'batch',       'resource': 'batch',        'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'academic:batch:update',      'name': 'Update Batch',                 'module': 'academic',    'category': 'batch',       'resource': 'batch',        'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'academic:batch:delete',      'name': 'Delete Batch',                 'module': 'academic',    'category': 'batch',       'resource': 'batch',        'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'academic:enrollment:create', 'name': 'Enrol Student in Batch',       'module': 'academic',    'category': 'enrollment',  'resource': 'enrollment',   'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'academic:enrollment:delete', 'name': 'Remove Student from Batch',    'module': 'academic',    'category': 'enrollment',  'resource': 'enrollment',   'action': 'DELETE',  'scope': 'TENANT'},
    # ── ADMIN / SETTINGS MODULE ──
    {'code': 'admin:settings:read',        'name': 'View System Settings',         'module': 'admin',       'category': 'settings',    'resource': 'settings',     'action': 'READ',    'scope': 'TENANT'},
    {'code': 'admin:settings:update',      'name': 'Update System Settings',       'module': 'admin',       'category': 'settings',    'resource': 'settings',     'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'admin:role:create',          'name': 'Create Role',                  'module': 'admin',       'category': 'role',        'resource': 'role',         'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'admin:role:update',          'name': 'Update Role',                  'module': 'admin',       'category': 'role',        'resource': 'role',         'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'admin:role:delete',          'name': 'Delete Role',                  'module': 'admin',       'category': 'role',        'resource': 'role',         'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'admin:permission:read',      'name': 'View Permissions',             'module': 'admin',       'category': 'permission',  'resource': 'permission',   'action': 'READ',    'scope': 'TENANT'},
    {'code': 'admin:permission:assign',    'name': 'Assign Permissions',           'module': 'admin',       'category': 'permission',  'resource': 'permission',   'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'admin:user:create',          'name': 'Create Admin User',            'module': 'admin',       'category': 'user',        'resource': 'admin',        'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'admin:user:delete',          'name': 'Delete Admin User',            'module': 'admin',       'category': 'user',        'resource': 'admin',        'action': 'DELETE',  'scope': 'TENANT'},
    {'code': 'admin:tenant:read',          'name': 'View Tenant Details',          'module': 'admin',       'category': 'tenant',      'resource': 'tenant',       'action': 'READ',    'scope': 'GLOBAL'},
    {'code': 'admin:tenant:update',        'name': 'Update Tenant Settings',       'module': 'admin',       'category': 'tenant',      'resource': 'tenant',       'action': 'UPDATE',  'scope': 'GLOBAL'},
    # ── REPORT / ANALYTICS MODULE ──
    {'code': 'report:dashboard:read',      'name': 'View Dashboard',               'module': 'report',      'category': 'dashboard',   'resource': 'dashboard',    'action': 'READ',    'scope': 'TENANT'},
    {'code': 'report:analytics:read',      'name': 'View Analytics Reports',       'module': 'report',      'category': 'analytics',   'resource': 'analytics',    'action': 'READ',    'scope': 'TENANT'},
    {'code': 'report:export:execute',      'name': 'Export Reports',               'module': 'report',      'category': 'export',      'resource': 'report',       'action': 'EXPORT',  'scope': 'TENANT'},
    {'code': 'report:student:read',        'name': 'View Student Reports',         'module': 'report',      'category': 'student',     'resource': 'report',       'action': 'READ',    'scope': 'BATCH'},
    {'code': 'report:teacher:read',        'name': 'View Teacher Reports',         'module': 'report',      'category': 'teacher',     'resource': 'report',       'action': 'READ',    'scope': 'TENANT'},
    {'code': 'report:financial:read',      'name': 'View Financial Reports',       'module': 'report',      'category': 'financial',   'resource': 'report',       'action': 'READ',    'scope': 'TENANT'},
    # ── AUDIT / SECURITY MODULE ──
    {'code': 'audit:log:read',             'name': 'View Audit Logs',              'module': 'audit',       'category': 'log',         'resource': 'audit',        'action': 'READ',    'scope': 'TENANT'},
    {'code': 'audit:export:execute',       'name': 'Export Audit Logs',            'module': 'audit',       'category': 'export',      'resource': 'audit',        'action': 'EXPORT',  'scope': 'TENANT'},
    {'code': 'audit:policy:update',        'name': 'Manage Audit Policies',        'module': 'audit',       'category': 'policy',      'resource': 'policy',       'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'security:policy:read',       'name': 'View Security Policies',       'module': 'security',    'category': 'policy',      'resource': 'policy',       'action': 'READ',    'scope': 'TENANT'},
    {'code': 'security:policy:update',     'name': 'Update Security Policies',     'module': 'security',    'category': 'policy',      'resource': 'policy',       'action': 'UPDATE',  'scope': 'TENANT'},
    # ── WEBSITE MODULE ──
    {'code': 'website:content:create',     'name': 'Create Website Content',       'module': 'website',     'category': 'content',     'resource': 'website',      'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'website:content:update',     'name': 'Update Website Content',       'module': 'website',     'category': 'content',     'resource': 'website',      'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'website:news:create',        'name': 'Create News/Announcement',     'module': 'website',     'category': 'news',        'resource': 'news',         'action': 'CREATE',  'scope': 'TENANT'},
    {'code': 'website:testimonial:create', 'name': 'Add Testimonial',              'module': 'website',     'category': 'testimonial', 'resource': 'testimonial',  'action': 'CREATE',  'scope': 'TENANT'},
    # ── INTEGRATION MODULE ──
    {'code': 'integration:youtube:execute','name': 'Manage YouTube Integration',   'module': 'integration', 'category': 'youtube',     'resource': 'integration',  'action': 'EXECUTE', 'scope': 'TENANT'},
    {'code': 'integration:config:update',  'name': 'Update Integration Config',    'module': 'integration', 'category': 'config',      'resource': 'integration',  'action': 'UPDATE',  'scope': 'TENANT'},
    {'code': 'integration:ai:execute',     'name': 'Use AI Features',              'module': 'integration', 'category': 'ai',          'resource': 'ai',           'action': 'EXECUTE', 'scope': 'TENANT'},
]

created_perms = {}
for pd in permissions_data:
    perm, created = Permission.objects.update_or_create(
        code=pd['code'],
        defaults={**pd, 'is_active': True}
    )
    created_perms[pd['code']] = perm
    if created:
        print(f"  ✓ Created Permission: {pd['code']}")
    # else skip printing to avoid clutter

print(f"\n  Total permissions: {Permission.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 3. ROLE-PERMISSION MAPPINGS
# ════════════════════════════════════════════════════════════
print("Assigning permissions to roles...")

role_perm_map = {
    'SYS_SUPER_ADMIN': list(created_perms.keys()),  # All permissions
    'SYS_PLATFORM_ADMIN': list(created_perms.keys()),
    'TENANT_ADMIN': [p for p in created_perms.keys() if not p.startswith('admin:tenant:')],
    'ACADEMIC_ADMIN': [p for p in created_perms.keys() if p.startswith(('academic:', 'exam:', 'class:', 'student:list', 'student:profile:read', 'teacher:list', 'teacher:profile:read', 'attendance:', 'material:', 'report:dashboard', 'report:analytics', 'report:student'))],
    'FINANCE_ADMIN': [p for p in created_perms.keys() if p.startswith(('student:fee', 'student:list', 'report:financial', 'report:dashboard', 'student:export'))],
    'HR_ADMIN': [p for p in created_perms.keys() if p.startswith(('teacher:', 'attendance:', 'report:teacher', 'report:dashboard'))],
    'CONTENT_ADMIN': [p for p in created_perms.keys() if p.startswith(('material:', 'class:recording', 'website:', 'integration:youtube'))],
    'SUPPORT_ADMIN': [p for p in created_perms.keys() if p.startswith(('comm:', 'student:list', 'student:profile:read', 'teacher:list', 'report:dashboard'))],
    'EXAM_COORDINATOR': [p for p in created_perms.keys() if p.startswith(('exam:', 'student:list', 'report:student', 'report:dashboard'))],
    'BRANCH_ADMIN': [p for p in created_perms.keys() if p.startswith(('student:', 'teacher:list', 'teacher:profile:read', 'attendance:', 'exam:test:read', 'exam:result', 'class:schedule:read', 'report:dashboard', 'report:student', 'comm:announcement'))],
    'REPORT_VIEWER': [p for p in created_perms.keys() if p.startswith('report:')],
    'DATA_ENTRY_OPERATOR': ['student:profile:create', 'student:profile:update', 'student:list:read', 'student:fee:update', 'teacher:profile:create', 'teacher:profile:update', 'teacher:list:read', 'attendance:mark:create', 'attendance:mark:update', 'exam:marks:update'],
    'HEAD_TEACHER': [p for p in created_perms.keys() if p.startswith(('class:', 'exam:', 'attendance:', 'material:', 'student:list', 'student:profile:read', 'teacher:list', 'teacher:profile:read', 'comm:announcement', 'report:dashboard', 'report:student', 'report:teacher'))],
    'SENIOR_TEACHER': [p for p in created_perms.keys() if p.startswith(('class:', 'exam:test', 'exam:question', 'exam:attempt', 'exam:result:read', 'exam:marks', 'attendance:mark', 'attendance:view', 'attendance:report', 'material:content', 'student:list', 'report:dashboard', 'report:student', 'comm:announcement:create'))],
    'TEACHER': ['class:schedule:read', 'class:live:execute', 'class:recording:read', 'exam:test:create', 'exam:test:read', 'exam:test:update', 'exam:question:create', 'exam:question:read', 'exam:attempt:read', 'exam:result:read', 'exam:marks:update', 'attendance:mark:create', 'attendance:mark:update', 'attendance:view:read', 'material:content:create', 'material:content:read', 'material:content:update', 'student:list:read', 'comm:announcement:create', 'comm:announcement:read', 'comm:message:create', 'comm:message:read', 'report:dashboard:read', 'report:student:read'],
    'TEACHING_ASSISTANT': ['class:schedule:read', 'class:recording:read', 'attendance:mark:create', 'attendance:view:read', 'student:list:read', 'material:content:read', 'comm:message:create', 'comm:message:read', 'exam:attempt:read'],
    'GUEST_LECTURER': ['class:schedule:read', 'class:live:execute', 'class:recording:read', 'material:content:read', 'student:list:read'],
    'CONTENT_CREATOR': ['material:content:create', 'material:content:read', 'material:content:update', 'material:gallery:create', 'material:gallery:read', 'exam:question:create', 'exam:question:read', 'class:recording:read'],
    'STUDENT': ['student:profile:read', 'student:profile:update', 'class:schedule:read', 'class:recording:read', 'exam:test:read', 'exam:result:read', 'attendance:view:read', 'attendance:correction:create', 'material:content:read', 'material:gallery:read', 'comm:announcement:read', 'comm:message:create', 'comm:message:read', 'comm:ticket:create', 'report:dashboard:read'],
    'STUDENT_LEADER': ['student:profile:read', 'student:profile:update', 'student:list:read', 'class:schedule:read', 'class:recording:read', 'exam:test:read', 'exam:result:read', 'attendance:view:read', 'attendance:correction:create', 'material:content:read', 'material:gallery:read', 'comm:announcement:create', 'comm:announcement:read', 'comm:message:create', 'comm:message:read', 'comm:ticket:create', 'report:dashboard:read'],
    'TRIAL_STUDENT': ['student:profile:read', 'class:schedule:read', 'class:recording:read', 'material:content:read', 'comm:announcement:read'],
    'PARENT': ['student:profile:read', 'student:fee:read', 'exam:result:read', 'attendance:view:read', 'comm:announcement:read', 'comm:message:create', 'comm:message:read', 'comm:ticket:create', 'report:dashboard:read'],
    'PARENT_COMMITTEE': ['student:profile:read', 'student:list:read', 'student:fee:read', 'exam:result:read', 'attendance:view:read', 'attendance:report:read', 'comm:announcement:create', 'comm:announcement:read', 'comm:message:create', 'comm:message:read', 'comm:ticket:create', 'report:dashboard:read', 'report:student:read'],
}

rp_created = 0
for role_code, perm_codes in role_perm_map.items():
    role = created_roles.get(role_code)
    if not role:
        continue
    for pc in perm_codes:
        perm = created_perms.get(pc)
        if not perm:
            continue
        _, created = RolePermission.objects.get_or_create(role=role, permission=perm)
        if created:
            rp_created += 1
print(f"  ✓ Created {rp_created} role-permission mappings")
print(f"  Total RolePermission records: {RolePermission.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 4. STAFF ROLES
# ════════════════════════════════════════════════════════════
staff_roles_data = [
    # SUPER_ADMIN level
    {'level': 'SUPER_ADMIN', 'name': 'Platform Super Admin',
     'description': 'Complete platform access — can manage all tenants, settings, and system configuration.',
     'can_manage_students': True, 'can_manage_teachers': True, 'can_manage_exams': True,
     'can_manage_attendance': True, 'can_manage_content': True, 'can_manage_finance': True,
     'can_manage_settings': True, 'can_manage_integrations': True, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': True, 'can_view_audit': True,
     'can_manage_website': True, 'can_manage_ai': True},
    # ADMIN level
    {'level': 'ADMIN', 'name': 'Institute Administrator',
     'description': 'Full institute-level access — manages students, teachers, exams, attendance, and finance.',
     'can_manage_students': True, 'can_manage_teachers': True, 'can_manage_exams': True,
     'can_manage_attendance': True, 'can_manage_content': True, 'can_manage_finance': True,
     'can_manage_settings': True, 'can_manage_integrations': True, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': True, 'can_view_audit': True,
     'can_manage_website': True, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Academic Head',
     'description': 'Manages academic operations — subjects, batches, exam configuration, and teacher assignments.',
     'can_manage_students': True, 'can_manage_teachers': True, 'can_manage_exams': True,
     'can_manage_attendance': True, 'can_manage_content': True, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': False, 'can_view_audit': True,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Finance Manager',
     'description': 'Manages fee collection, payment tracking, financial reports, and student fee status.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': False, 'can_manage_content': False, 'can_manage_finance': True,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Branch Manager',
     'description': 'Manages a specific branch — student admissions, attendance, and local operations.',
     'can_manage_students': True, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': True, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': True,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Exam Controller',
     'description': 'Creates tests, manages question banks, schedules exams, and publishes results.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': True,
     'can_manage_attendance': False, 'can_manage_content': True, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Content Manager',
     'description': 'Manages study materials, video content, photo galleries, and website content updates.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': False, 'can_manage_content': True, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': True, 'can_view_reports': False,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': True, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'HR & Staff Manager',
     'description': 'Manages teacher profiles, staff attendance, and teacher-batch assignments.',
     'can_manage_students': False, 'can_manage_teachers': True, 'can_manage_exams': False,
     'can_manage_attendance': True, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': True, 'can_manage_roles': False, 'can_view_audit': True,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'ADMIN', 'name': 'Support Desk Manager',
     'description': 'Handles student and parent enquiries, support tickets, and communication.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': False, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': False,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    # OPERATOR level
    {'level': 'OPERATOR', 'name': 'Data Entry Operator',
     'description': 'Enters student data, marks attendance, updates fee records, and types test scores.',
     'can_manage_students': True, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': True, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': False,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'OPERATOR', 'name': 'Attendance Operator',
     'description': 'Marks and updates daily attendance for students and teachers.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': True, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'OPERATOR', 'name': 'Front Desk / Receptionist',
     'description': 'Handles walk-in enquiries, phone calls, and basic student information.',
     'can_manage_students': True, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': False, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': False,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
    {'level': 'OPERATOR', 'name': 'Report Viewer',
     'description': 'Read-only access to view reports and dashboards.',
     'can_manage_students': False, 'can_manage_teachers': False, 'can_manage_exams': False,
     'can_manage_attendance': False, 'can_manage_content': False, 'can_manage_finance': False,
     'can_manage_settings': False, 'can_manage_integrations': False, 'can_view_reports': True,
     'can_export_data': False, 'can_manage_roles': False, 'can_view_audit': False,
     'can_manage_website': False, 'can_manage_ai': False},
]

for srd in staff_roles_data:
    sr, created = StaffRole.objects.update_or_create(
        tenant=tenant, name=srd['name'],
        defaults={**srd, 'tenant': tenant, 'is_active': True}
    )
    print(f"  {'✓ Created' if created else '→ Updated'} StaffRole: [{srd['level']}] {srd['name']}")

print(f"\n  Total staff roles: {StaffRole.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 5. USER GROUPS
# ════════════════════════════════════════════════════════════
groups_data = [
    {'code': 'DEPT_PHYSICS',     'name': 'Physics Department',        'group_type': 'DEPARTMENT', 'description': 'All Physics teachers and related staff'},
    {'code': 'DEPT_CHEMISTRY',   'name': 'Chemistry Department',      'group_type': 'DEPARTMENT', 'description': 'All Chemistry teachers and related staff'},
    {'code': 'DEPT_MATHEMATICS', 'name': 'Mathematics Department',    'group_type': 'DEPARTMENT', 'description': 'All Mathematics teachers and related staff'},
    {'code': 'DEPT_BIOLOGY',     'name': 'Biology Department',        'group_type': 'DEPARTMENT', 'description': 'All Biology teachers and related staff'},
    {'code': 'DEPT_ENGLISH',     'name': 'English Department',        'group_type': 'DEPARTMENT', 'description': 'English language teachers'},
    {'code': 'DEPT_ADMIN',       'name': 'Administration Department', 'group_type': 'DEPARTMENT', 'description': 'Office staff, managers, and support personnel'},
    {'code': 'BATCH_JEE_11',     'name': 'JEE Class 11 Batch',       'group_type': 'BATCH',      'description': 'All Class 11 students preparing for JEE'},
    {'code': 'BATCH_JEE_12',     'name': 'JEE Class 12 Batch',       'group_type': 'BATCH',      'description': 'All Class 12 students preparing for JEE'},
    {'code': 'BATCH_JEE_DROP',   'name': 'JEE Dropper Batch',        'group_type': 'BATCH',      'description': 'Students in JEE dropper/repeater batch'},
    {'code': 'BATCH_NEET_11',    'name': 'NEET Class 11 Batch',      'group_type': 'BATCH',      'description': 'All Class 11 students preparing for NEET'},
    {'code': 'BATCH_NEET_12',    'name': 'NEET Class 12 Batch',      'group_type': 'BATCH',      'description': 'All Class 12 students preparing for NEET'},
    {'code': 'BATCH_NEET_DROP',  'name': 'NEET Dropper Batch',       'group_type': 'BATCH',      'description': 'Students in NEET dropper/repeater batch'},
    {'code': 'BATCH_FOUNDATION', 'name': 'Foundation Batch',          'group_type': 'BATCH',      'description': 'Junior students in foundation/olympiad program'},
    {'code': 'GRP_TOPPERS',      'name': 'Toppers Club',              'group_type': 'CUSTOM',     'description': 'Top-performing students for special mentoring'},
    {'code': 'GRP_MENTORS',      'name': 'Mentor Group',              'group_type': 'CUSTOM',     'description': 'Senior teachers acting as student mentors'},
    {'code': 'GRP_CONTENT_TEAM', 'name': 'Content Creation Team',     'group_type': 'CUSTOM',     'description': 'Teachers and staff responsible for creating study content'},
    {'code': 'GRP_EXAM_CELL',    'name': 'Exam Cell',                 'group_type': 'CUSTOM',     'description': 'Team responsible for exam creation and administration'},
    {'code': 'GRP_PARENT_CMTE',  'name': 'Parent Committee',          'group_type': 'CUSTOM',     'description': 'Selected parents involved in institute decisions'},
    {'code': 'SYS_ALL_TEACHERS', 'name': 'All Teachers',              'group_type': 'SYSTEM',     'description': 'System group containing all active teachers'},
    {'code': 'SYS_ALL_STUDENTS', 'name': 'All Students',              'group_type': 'SYSTEM',     'description': 'System group containing all active students'},
    {'code': 'SYS_ALL_ADMINS',   'name': 'All Administrators',        'group_type': 'SYSTEM',     'description': 'System group containing all admin users'},
]

for gd in groups_data:
    ug, created = UserGroup.objects.update_or_create(
        tenant=tenant, code=gd['code'],
        defaults={**gd, 'tenant': tenant, 'is_active': True}
    )
    print(f"  {'✓ Created' if created else '→ Updated'} Group: [{gd['group_type']}] {gd['name']}")

print(f"\n  Total user groups: {UserGroup.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 6. SECURITY POLICIES
# ════════════════════════════════════════════════════════════
security_policies_data = [
    {'name': 'Admin Security Policy — Strict',      'applies_to': 'ADMIN',   'priority': 100,
     'description': 'Strict security for admin users — strong passwords, MFA required, IP restrictions.',
     'min_password_length': 12, 'require_uppercase': True, 'require_lowercase': True,
     'require_digits': True, 'require_special_chars': True, 'password_expiry_days': 60,
     'password_history_count': 10, 'prevent_common_passwords': True,
     'mfa_required': True, 'mfa_required_for_admins': True,
     'allowed_mfa_methods': ['TOTP', 'EMAIL'],
     'max_concurrent_sessions': 2, 'session_timeout_minutes': 240, 'idle_timeout_minutes': 15,
     'max_failed_attempts': 3, 'lockout_duration_minutes': 60, 'progressive_lockout': True,
     'ip_whitelist_enabled': False, 'ip_whitelist': [], 'geo_restriction_enabled': False,
     'allowed_countries': ['IN'], 'device_trust_enabled': True},
    {'name': 'Teacher Security Policy — Standard',  'applies_to': 'TEACHER', 'priority': 50,
     'description': 'Standard security for teachers — moderate password requirements, MFA optional.',
     'min_password_length': 8, 'require_uppercase': True, 'require_lowercase': True,
     'require_digits': True, 'require_special_chars': False, 'password_expiry_days': 90,
     'password_history_count': 5, 'prevent_common_passwords': True,
     'mfa_required': False, 'mfa_required_for_admins': True,
     'allowed_mfa_methods': ['EMAIL', 'SMS'],
     'max_concurrent_sessions': 3, 'session_timeout_minutes': 480, 'idle_timeout_minutes': 30,
     'max_failed_attempts': 5, 'lockout_duration_minutes': 30, 'progressive_lockout': True,
     'ip_whitelist_enabled': False, 'ip_whitelist': [], 'geo_restriction_enabled': False,
     'allowed_countries': [], 'device_trust_enabled': False},
    {'name': 'Student Security Policy — Basic',     'applies_to': 'STUDENT', 'priority': 30,
     'description': 'Basic security for students — simple passwords, extended sessions.',
     'min_password_length': 6, 'require_uppercase': False, 'require_lowercase': True,
     'require_digits': True, 'require_special_chars': False, 'password_expiry_days': 180,
     'password_history_count': 3, 'prevent_common_passwords': True,
     'mfa_required': False, 'mfa_required_for_admins': False,
     'allowed_mfa_methods': ['EMAIL'],
     'max_concurrent_sessions': 5, 'session_timeout_minutes': 720, 'idle_timeout_minutes': 60,
     'max_failed_attempts': 10, 'lockout_duration_minutes': 15, 'progressive_lockout': False,
     'ip_whitelist_enabled': False, 'ip_whitelist': [], 'geo_restriction_enabled': False,
     'allowed_countries': [], 'device_trust_enabled': False},
    {'name': 'Default Security Policy — All Users', 'applies_to': 'ALL',     'priority': 10,
     'description': 'Fallback security policy applied when no specific policy matches.',
     'min_password_length': 8, 'require_uppercase': True, 'require_lowercase': True,
     'require_digits': True, 'require_special_chars': False, 'password_expiry_days': 90,
     'password_history_count': 5, 'prevent_common_passwords': True,
     'mfa_required': False, 'mfa_required_for_admins': True,
     'allowed_mfa_methods': ['EMAIL', 'TOTP'],
     'max_concurrent_sessions': 3, 'session_timeout_minutes': 480, 'idle_timeout_minutes': 30,
     'max_failed_attempts': 5, 'lockout_duration_minutes': 30, 'progressive_lockout': True,
     'ip_whitelist_enabled': False, 'ip_whitelist': [], 'geo_restriction_enabled': False,
     'allowed_countries': [], 'device_trust_enabled': False},
]

for spd in security_policies_data:
    sp, created = SecurityPolicy.objects.update_or_create(
        tenant=tenant, name=spd['name'],
        defaults={**spd, 'tenant': tenant, 'is_active': True}
    )
    print(f"  {'✓ Created' if created else '→ Updated'} SecurityPolicy: {spd['name']}")

print(f"\n  Total security policies: {SecurityPolicy.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 7. COMPLIANCE RULES
# ════════════════════════════════════════════════════════════
compliance_data = [
    {'code': 'DPDP_STUDENT_DATA',  'name': 'Student Data Protection (DPDP Act)',
     'description': 'Governs collection, storage, and processing of student personal data under India\'s Digital Personal Data Protection Act.',
     'regulation_type': 'DPDP', 'applicable_data_types': ['personal_info', 'academic_records', 'contact_info'],
     'applicable_user_types': ['STUDENT'], 'data_retention_days': 2555,
     'requires_consent': True, 'requires_encryption': True, 'requires_anonymization': False,
     'requires_audit_trail': True, 'auto_enforce': False},
    {'code': 'DPDP_TEACHER_DATA',  'name': 'Teacher Data Protection (DPDP Act)',
     'description': 'Governs teacher personal and employment data under DPDP Act.',
     'regulation_type': 'DPDP', 'applicable_data_types': ['personal_info', 'employment_records'],
     'applicable_user_types': ['TEACHER'], 'data_retention_days': 3650,
     'requires_consent': True, 'requires_encryption': True, 'requires_anonymization': False,
     'requires_audit_trail': True, 'auto_enforce': False},
    {'code': 'IT_ACT_SECPRACTICE', 'name': 'IT Act — Reasonable Security Practices',
     'description': 'Compliance with Section 43A of IT Act 2000 — requires reasonable security measures for sensitive personal data.',
     'regulation_type': 'IT_ACT', 'applicable_data_types': ['passwords', 'financial_info', 'biometric'],
     'applicable_user_types': ['STUDENT', 'TEACHER', 'ADMIN'], 'data_retention_days': None,
     'requires_consent': False, 'requires_encryption': True, 'requires_anonymization': False,
     'requires_audit_trail': True, 'auto_enforce': True, 'enforcement_action': 'encrypt_at_rest'},
    {'code': 'INTERNAL_AUDIT_LOG', 'name': 'Internal Audit Log Retention',
     'description': 'Internal policy: retain all audit logs for 365 days, then archive.',
     'regulation_type': 'INTERNAL', 'applicable_data_types': ['audit_logs', 'access_logs'],
     'applicable_user_types': ['STUDENT', 'TEACHER', 'ADMIN', 'PARENT'], 'data_retention_days': 365,
     'requires_consent': False, 'requires_encryption': False, 'requires_anonymization': False,
     'requires_audit_trail': True, 'auto_enforce': True, 'enforcement_action': 'archive_and_purge'},
    {'code': 'INTERNAL_EXAM_DATA', 'name': 'Exam Data Retention Policy',
     'description': 'Retain exam attempts, scores, and answer sheets for minimum 5 years for academic records.',
     'regulation_type': 'INTERNAL', 'applicable_data_types': ['test_attempts', 'scores', 'answer_sheets'],
     'applicable_user_types': ['STUDENT'], 'data_retention_days': 1825,
     'requires_consent': False, 'requires_encryption': False, 'requires_anonymization': False,
     'requires_audit_trail': True, 'auto_enforce': False},
    {'code': 'INTERNAL_ATTENDANCE','name': 'Attendance Data Retention',
     'description': 'Retain attendance records for current and previous academic year.',
     'regulation_type': 'INTERNAL', 'applicable_data_types': ['attendance_records'],
     'applicable_user_types': ['STUDENT', 'TEACHER'], 'data_retention_days': 730,
     'requires_consent': False, 'requires_encryption': False, 'requires_anonymization': False,
     'requires_audit_trail': False, 'auto_enforce': False},
    {'code': 'COPPA_MINOR_DATA',   'name': 'Minor Data Protection',
     'description': 'Enhanced protection for students under 13 — requires parental consent for data collection.',
     'regulation_type': 'COPPA', 'applicable_data_types': ['personal_info', 'academic_records', 'behavioral'],
     'applicable_user_types': ['STUDENT'], 'data_retention_days': None,
     'requires_consent': True, 'requires_encryption': True, 'requires_anonymization': True,
     'requires_audit_trail': True, 'auto_enforce': False},
]

for cd in compliance_data:
    cr, created = ComplianceRule.objects.update_or_create(
        code=cd['code'],
        defaults={**cd, 'tenant': tenant, 'is_active': True}
    )
    print(f"  {'✓ Created' if created else '→ Updated'} ComplianceRule: {cd['code']}")

print(f"\n  Total compliance rules: {ComplianceRule.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 8. FEATURE FLAGS
# ════════════════════════════════════════════════════════════
feature_flags_data = [
    {'flag_key': 'LIVE_CLASS_YOUTUBE',     'flag_name': 'YouTube Live Classes',                 'is_enabled': True,  'description': 'Enable live class streaming via YouTube.', 'allowed_user_types': ['TEACHER', 'ADMIN']},
    {'flag_key': 'LIVE_CLASS_ZOOM',        'flag_name': 'Zoom Live Classes',                    'is_enabled': False, 'description': 'Enable Zoom integration for live classes.', 'allowed_user_types': ['TEACHER', 'ADMIN']},
    {'flag_key': 'ONLINE_TEST',            'flag_name': 'Online Tests & Assessments',           'is_enabled': True,  'description': 'Allow students to take tests online.', 'allowed_user_types': ['STUDENT', 'TEACHER', 'ADMIN']},
    {'flag_key': 'OFFLINE_TEST_MARKS',     'flag_name': 'Offline Test Marks Entry',             'is_enabled': True,  'description': 'Enable manual entry of offline test marks.', 'allowed_user_types': ['TEACHER', 'ADMIN']},
    {'flag_key': 'STUDENT_DASHBOARD',      'flag_name': 'Student Dashboard',                    'is_enabled': True,  'description': 'Show student self-service dashboard.', 'allowed_user_types': ['STUDENT']},
    {'flag_key': 'TEACHER_DASHBOARD',      'flag_name': 'Teacher Dashboard',                    'is_enabled': True,  'description': 'Show teacher dashboard with class and student insights.', 'allowed_user_types': ['TEACHER']},
    {'flag_key': 'PARENT_PORTAL',          'flag_name': 'Parent Portal Access',                 'is_enabled': False, 'description': 'Allow parents to login and view child performance.', 'allowed_user_types': ['PARENT']},
    {'flag_key': 'AI_QUESTION_GENERATOR',  'flag_name': 'AI Question Paper Generator',          'is_enabled': False, 'description': 'Use LLM to automatically generate question papers.', 'allowed_user_types': ['TEACHER', 'ADMIN']},
    {'flag_key': 'AI_STUDENT_ANALYTICS',   'flag_name': 'AI Student Analytics',                 'is_enabled': False, 'description': 'AI-powered student performance predictions and recommendations.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'WHATSAPP_NOTIFICATIONS', 'flag_name': 'WhatsApp Notifications',               'is_enabled': False, 'description': 'Send notifications and alerts via WhatsApp.', 'allowed_user_types': ['STUDENT', 'TEACHER', 'PARENT']},
    {'flag_key': 'SMS_NOTIFICATIONS',      'flag_name': 'SMS Notifications',                    'is_enabled': True,  'description': 'Send SMS alerts for attendance, results, and payments.', 'allowed_user_types': ['STUDENT', 'TEACHER', 'PARENT']},
    {'flag_key': 'EMAIL_NOTIFICATIONS',    'flag_name': 'Email Notifications',                  'is_enabled': True,  'description': 'Send email notifications for important events.', 'allowed_user_types': ['STUDENT', 'TEACHER', 'ADMIN', 'PARENT']},
    {'flag_key': 'FEE_MANAGEMENT',         'flag_name': 'Fee Management Module',                'is_enabled': True,  'description': 'Enable fee tracking and payment management.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'ONLINE_PAYMENT',         'flag_name': 'Online Payment Gateway',               'is_enabled': False, 'description': 'Allow students to pay fees online.', 'allowed_user_types': ['STUDENT', 'PARENT']},
    {'flag_key': 'STUDY_MATERIAL_DOWNLOAD','flag_name': 'Study Material Download',              'is_enabled': True,  'description': 'Allow students to download study materials as PDF.', 'allowed_user_types': ['STUDENT']},
    {'flag_key': 'PHOTO_GALLERY',          'flag_name': 'Photo Gallery',                        'is_enabled': True,  'description': 'Enable photo gallery on website and dashboards.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'SCHOLARSHIP_TRACKER',    'flag_name': 'Scholarship Tracker',                  'is_enabled': True,  'description': 'Track student scholarship applications and results.', 'allowed_user_types': ['ADMIN', 'STUDENT']},
    {'flag_key': 'MULTI_BRANCH',           'flag_name': 'Multi-Branch Support',                 'is_enabled': False, 'description': 'Enable multi-branch/center management.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'ADVANCED_ANALYTICS',     'flag_name': 'Advanced Analytics Dashboard',         'is_enabled': False, 'description': 'Show advanced charts, trends, and comparative analytics.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'DARK_MODE',              'flag_name': 'Dark Mode',                            'is_enabled': True,  'description': 'Allow users to switch to dark theme.', 'allowed_user_types': ['STUDENT', 'TEACHER', 'ADMIN', 'PARENT']},
    {'flag_key': 'EXPORT_EXCEL',           'flag_name': 'Export to Excel',                      'is_enabled': True,  'description': 'Allow exporting data to Excel format.', 'allowed_user_types': ['ADMIN', 'TEACHER']},
    {'flag_key': 'BULK_IMPORT',            'flag_name': 'Bulk Import (CSV/Excel)',               'is_enabled': True,  'description': 'Allow bulk import of students, teachers via CSV.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'MFA_AUTHENTICATION',     'flag_name': 'Multi-Factor Authentication',          'is_enabled': False, 'description': 'Enable MFA for user logins.', 'allowed_user_types': ['ADMIN', 'TEACHER']},
    {'flag_key': 'ATTENDANCE_BIOMETRIC',   'flag_name': 'Biometric Attendance',                 'is_enabled': False, 'description': 'Enable biometric device integration for attendance.', 'allowed_user_types': ['ADMIN']},
    {'flag_key': 'WEBSITE_CMS',            'flag_name': 'Website CMS',                          'is_enabled': True,  'description': 'Enable website content management system.', 'allowed_user_types': ['ADMIN']},
]

for ffd in feature_flags_data:
    ff, created = FeatureFlag.objects.update_or_create(
        tenant=tenant, flag_key=ffd['flag_key'],
        defaults={**ffd, 'tenant': tenant, 'rollout_percentage': 100 if ffd['is_enabled'] else 0}
    )
    status = '✓ ON' if ffd['is_enabled'] else '✗ OFF'
    if created:
        print(f"  {status}  FeatureFlag: {ffd['flag_key']}")

print(f"\n  Total feature flags: {FeatureFlag.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# 9. SYSTEM SETTINGS
# ════════════════════════════════════════════════════════════
settings_data = [
    # General
    {'setting_key': 'INSTITUTE_NAME',            'setting_value': 'ENABLE PROGRAM',                 'value_type': 'STRING',  'category': 'general',        'description': 'Display name of the institute'},
    {'setting_key': 'INSTITUTE_CODE',            'setting_value': 'ENF',                              'value_type': 'STRING',  'category': 'general',        'description': 'Short code for the institute'},
    {'setting_key': 'SUPPORT_EMAIL',             'setting_value': 'support@lms.com',                  'value_type': 'STRING',  'category': 'general',        'description': 'Support email address'},
    {'setting_key': 'SUPPORT_PHONE',             'setting_value': '+91-9876543210',                   'value_type': 'STRING',  'category': 'general',        'description': 'Support phone number'},
    {'setting_key': 'DEFAULT_TIMEZONE',          'setting_value': 'Asia/Kolkata',                     'value_type': 'STRING',  'category': 'general',        'description': 'Default timezone for the platform'},
    {'setting_key': 'DEFAULT_LANGUAGE',          'setting_value': 'en',                               'value_type': 'STRING',  'category': 'general',        'description': 'Default language code'},
    {'setting_key': 'DATE_FORMAT',               'setting_value': 'DD/MM/YYYY',                       'value_type': 'STRING',  'category': 'general',        'description': 'Date display format'},
    # Academic
    {'setting_key': 'ACADEMIC_YEAR_START_MONTH',  'setting_value': '4',                               'value_type': 'INTEGER', 'category': 'academic',       'description': 'Academic year start month (1=Jan, 4=Apr)'},
    {'setting_key': 'DEFAULT_LIST_PER_PAGE',      'setting_value': '25',                              'value_type': 'INTEGER', 'category': 'academic',       'description': 'Default rows displayed per page in admin lists'},
    {'setting_key': 'MAX_STUDENTS_PER_BATCH',     'setting_value': '100',                             'value_type': 'INTEGER', 'category': 'academic',       'description': 'Maximum students allowed per batch'},
    {'setting_key': 'STUDENT_CODE_PREFIX',         'setting_value': 'STU',                            'value_type': 'STRING',  'category': 'academic',       'description': 'Prefix for auto-generated student codes'},
    {'setting_key': 'TEACHER_CODE_PREFIX',         'setting_value': 'TCH',                            'value_type': 'STRING',  'category': 'academic',       'description': 'Prefix for auto-generated teacher codes'},
    # Attendance
    {'setting_key': 'ATTENDANCE_CUTOFF_TIME',      'setting_value': '10:00',                          'value_type': 'STRING',  'category': 'attendance',     'description': 'Daily attendance cutoff time (HH:MM)'},
    {'setting_key': 'ATTENDANCE_MIN_PERCENTAGE',   'setting_value': '75',                             'value_type': 'INTEGER', 'category': 'attendance',     'description': 'Minimum attendance percentage required'},
    {'setting_key': 'ATTENDANCE_AUTO_ABSENT',      'setting_value': 'true',                           'value_type': 'BOOLEAN', 'category': 'attendance',     'description': 'Automatically mark absent if not present by cutoff'},
    # Exam
    {'setting_key': 'EXAM_RESULT_AUTO_PUBLISH',    'setting_value': 'false',                          'value_type': 'BOOLEAN', 'category': 'exam',           'description': 'Auto-publish results after grading'},
    {'setting_key': 'EXAM_NEGATIVE_MARKING',       'setting_value': 'true',                           'value_type': 'BOOLEAN', 'category': 'exam',           'description': 'Enable negative marking for MCQ tests'},
    {'setting_key': 'EXAM_DEFAULT_DURATION',       'setting_value': '180',                            'value_type': 'INTEGER', 'category': 'exam',           'description': 'Default test duration in minutes'},
    {'setting_key': 'EXAM_PASS_PERCENTAGE',        'setting_value': '33',                             'value_type': 'INTEGER', 'category': 'exam',           'description': 'Default pass percentage for tests'},
    # Notification
    {'setting_key': 'NOTIFICATION_EMAIL_ENABLED',  'setting_value': 'true',                           'value_type': 'BOOLEAN', 'category': 'notification',   'description': 'Enable email notifications system-wide'},
    {'setting_key': 'NOTIFICATION_SMS_ENABLED',    'setting_value': 'true',                           'value_type': 'BOOLEAN', 'category': 'notification',   'description': 'Enable SMS notifications system-wide'},
    {'setting_key': 'NOTIFICATION_PUSH_ENABLED',   'setting_value': 'false',                          'value_type': 'BOOLEAN', 'category': 'notification',   'description': 'Enable push notifications'},
    {'setting_key': 'NOTIFICATION_WHATSAPP_ENABLED','setting_value': 'false',                         'value_type': 'BOOLEAN', 'category': 'notification',   'description': 'Enable WhatsApp notifications'},
    # Security
    {'setting_key': 'SESSION_TIMEOUT_MINUTES',     'setting_value': '480',                            'value_type': 'INTEGER', 'category': 'security',       'description': 'Session timeout in minutes'},
    {'setting_key': 'MAX_LOGIN_ATTEMPTS',          'setting_value': '5',                              'value_type': 'INTEGER', 'category': 'security',       'description': 'Maximum failed login attempts before lockout'},
    {'setting_key': 'PASSWORD_MIN_LENGTH',         'setting_value': '8',                              'value_type': 'INTEGER', 'category': 'security',       'description': 'Minimum password length'},
    {'setting_key': 'ENABLE_MFA',                  'setting_value': 'false',                          'value_type': 'BOOLEAN', 'category': 'security',       'description': 'Enable multi-factor authentication globally'},
    # Storage & Upload
    {'setting_key': 'MAX_UPLOAD_SIZE_MB',          'setting_value': '50',                             'value_type': 'INTEGER', 'category': 'storage',        'description': 'Maximum upload file size in MB'},
    {'setting_key': 'ALLOWED_FILE_TYPES',          'setting_json': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'png', 'mp4'], 'setting_value': None, 'value_type': 'JSON', 'category': 'storage', 'description': 'Allowed file extensions for uploads'},
    # Branding
    {'setting_key': 'PRIMARY_COLOR',               'setting_value': '#844FC1',                        'value_type': 'STRING',  'category': 'branding',       'description': 'Primary brand color'},
    {'setting_key': 'SECONDARY_COLOR',             'setting_value': '#1E293B',                        'value_type': 'STRING',  'category': 'branding',       'description': 'Secondary brand color'},
    {'setting_key': 'LOGIN_PAGE_BRAND_TEXT',        'setting_value': 'Welcome to ENABLE PROGRAM',   'value_type': 'STRING',  'category': 'branding',       'description': 'Text shown on login page'},
]

for sd in settings_data:
    ss, created = SystemSetting.objects.update_or_create(
        tenant=tenant, setting_key=sd['setting_key'],
        defaults={**sd, 'tenant': tenant, 'is_editable': True}
    )
    if created:
        print(f"  ✓ Created Setting: {sd['setting_key']}")

print(f"\n  Total system settings: {SystemSetting.objects.count()}\n")

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print("=" * 60)
print("POPULATION COMPLETE — Summary")
print("=" * 60)
print(f"  Roles:              {Role.objects.count()}")
print(f"  Permissions:        {Permission.objects.count()}")
print(f"  Role-Permissions:   {RolePermission.objects.count()}")
print(f"  Staff Roles:        {StaffRole.objects.count()}")
print(f"  User Groups:        {UserGroup.objects.count()}")
print(f"  Security Policies:  {SecurityPolicy.objects.count()}")
print(f"  Compliance Rules:   {ComplianceRule.objects.count()}")
print(f"  Feature Flags:      {FeatureFlag.objects.count()}")
print(f"  System Settings:    {SystemSetting.objects.count()}")
print("=" * 60)
