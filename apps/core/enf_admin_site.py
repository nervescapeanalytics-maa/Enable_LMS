"""
ENABLE PROGRAM - Custom Admin Site Configuration
Monkey-patches the default admin site to add dashboard stats.
Supports tenant-scoped counts via the admin tenant switcher.
"""
from django.contrib import admin


def _tenant_filter(qs, request):
    """Apply the admin session tenant filter if one is selected."""
    tid = request.session.get('admin_tenant_id')
    if tid and hasattr(qs.model, 'tenant'):
        return qs.filter(tenant_id=tid)
    return qs


def custom_admin_index(self, request, extra_context=None):
    """Override the default admin index to inject dashboard statistics."""
    extra_context = extra_context or {}

    selected_tid = request.session.get('admin_tenant_id')
    extra_context['viewing_tenant'] = request.session.get('admin_tenant_name') if selected_tid else None

    try:
        from accounts.models import Student
        extra_context['student_count'] = _tenant_filter(
            Student.objects.filter(status='ACTIVE'), request
        ).count()
    except Exception:
        extra_context['student_count'] = 0

    try:
        from accounts.models import Teacher
        extra_context['teacher_count'] = _tenant_filter(Teacher.objects, request).count()
    except Exception:
        extra_context['teacher_count'] = 0

    try:
        from academics.models import Batch
        extra_context['batch_count'] = _tenant_filter(Batch.objects.filter(status__iexact='ACTIVE'), request).count()
    except Exception:
        extra_context['batch_count'] = 0

    try:
        from assessments.models import Test
        extra_context['test_count'] = _tenant_filter(Test.objects, request).count()
    except Exception:
        extra_context['test_count'] = 0

    try:
        from sessions_tracking.models import UserSession
        extra_context['active_sessions'] = _tenant_filter(
            UserSession.objects.filter(status='ACTIVE'), request
        ).count()
    except Exception:
        extra_context['active_sessions'] = 0

    try:
        from tenants.models import Tenant
        extra_context['tenant_count'] = Tenant.objects.count()
    except Exception:
        extra_context['tenant_count'] = 0

    if not selected_tid:
        try:
            from tenants.models import Tenant
            from accounts.models import Teacher, Student
            from academics.models import Batch
            tenant_stats = []
            for t in Tenant.objects.filter(status__in=['ACTIVE', 'active', 'TRIAL']).order_by('name'):
                tenant_stats.append({
                    'name': t.name,
                    'code': t.code,
                    'students': Student.objects.filter(tenant=t, status='ACTIVE').count(),
                    'teachers': Teacher.objects.filter(tenant=t).count(),
                    'batches': Batch.objects.filter(tenant=t, status__iexact='ACTIVE').count(),
                })
            extra_context['tenant_breakdown'] = tenant_stats
        except Exception:
            extra_context['tenant_breakdown'] = []

    # ── AI Features ──
    try:
        from system_config.models import AIFeatureConfig
        ai_qs = AIFeatureConfig.objects.all().order_by('sort_order', 'feature_name')
        extra_context['ai_features'] = ai_qs
        extra_context['ai_feature_count'] = ai_qs.count()
        extra_context['ai_enabled_count'] = ai_qs.filter(is_enabled=True).count()
    except Exception:
        extra_context['ai_features'] = []
        extra_context['ai_feature_count'] = 0
        extra_context['ai_enabled_count'] = 0

    # ── Class Link Configs ──
    try:
        from system_config.models import ClassLinkConfig
        extra_context['class_link_count'] = ClassLinkConfig.objects.filter(is_active=True).count()
    except Exception:
        extra_context['class_link_count'] = 0

    # ── Attendance Rules ──
    try:
        from system_config.models import AttendanceRule
        extra_context['attendance_rule_count'] = AttendanceRule.objects.filter(is_active=True).count()
    except Exception:
        extra_context['attendance_rule_count'] = 0

    # ── Attendance Today ──
    try:
        from attendance.models import Attendance
        from datetime import date
        today = date.today()
        today_qs = _tenant_filter(Attendance.objects.filter(attendance_date=today), request)
        extra_context['today_present'] = today_qs.filter(status='PRESENT').count()
        extra_context['today_absent'] = today_qs.filter(status='ABSENT').count()
        extra_context['today_late'] = today_qs.filter(status='LATE').count()
        extra_context['today_leave'] = today_qs.filter(status='LEAVE').count()
    except Exception:
        extra_context['today_present'] = 0
        extra_context['today_absent'] = 0
        extra_context['today_late'] = 0
        extra_context['today_leave'] = 0

    # ── RBAC Counts ──
    try:
        from accounts.models import Role, Permission
        extra_context['admin_role_count'] = _tenant_filter(
            Role.objects.filter(applies_to__in=['ADMIN', 'ALL'], is_active=True), request
        ).count()
        extra_context['teacher_role_count'] = _tenant_filter(
            Role.objects.filter(applies_to__in=['TEACHER', 'ALL'], is_active=True), request
        ).count()
        extra_context['student_role_count'] = _tenant_filter(
            Role.objects.filter(applies_to__in=['STUDENT', 'ALL'], is_active=True), request
        ).count()
        extra_context['permission_count'] = Permission.objects.filter(is_active=True).count()
    except Exception:
        extra_context['admin_role_count'] = 0
        extra_context['teacher_role_count'] = 0
        extra_context['student_role_count'] = 0
        extra_context['permission_count'] = 0

    # ── User Groups ──
    try:
        from accounts.models import UserGroup
        groups = _tenant_filter(UserGroup.objects.all(), request).order_by('name')[:10]
        extra_context['groups'] = groups
        extra_context['groups_count'] = _tenant_filter(UserGroup.objects, request).count()
    except Exception:
        extra_context['groups'] = []
        extra_context['groups_count'] = 0

    # ── Integration Configs ──
    try:
        from system_config.models import IntegrationConfig
        youtube_int = IntegrationConfig.objects.filter(integration_type='YOUTUBE', is_active=True).first()
        llm_int = IntegrationConfig.objects.filter(integration_type='LLM', is_active=True).first()
        storage_int = IntegrationConfig.objects.filter(integration_type='STORAGE', is_active=True).first()
        extra_context['youtube_integration_active'] = youtube_int is not None
        extra_context['youtube_integration_status'] = 'Active' if youtube_int else 'Not Configured'
        extra_context['llm_integration_active'] = llm_int is not None
        extra_context['llm_integration_status'] = 'Active' if llm_int else 'Not Configured'
        extra_context['storage_integration_active'] = storage_int is not None
        extra_context['storage_integration_status'] = 'Active' if storage_int else 'Not Configured'
        extra_context['meeting_integration_active'] = extra_context.get('class_link_count', 0) > 0
    except Exception:
        extra_context['youtube_integration_active'] = False
        extra_context['youtube_integration_status'] = 'Not Configured'
        extra_context['llm_integration_active'] = False
        extra_context['llm_integration_status'] = 'Not Configured'
        extra_context['storage_integration_active'] = False
        extra_context['storage_integration_status'] = 'Not Configured'
        extra_context['meeting_integration_active'] = False

    # ── Community & Knowledge Features ──
    try:
        from system_config.models import FeatureFlag
        community_flag = FeatureFlag.objects.filter(flag_key__icontains='community', is_enabled=True).first()
        extra_context['community_features_active'] = community_flag is not None
        extra_context['community_feature_status'] = 'Enabled' if community_flag else 'Available'
        knowledge_flag = FeatureFlag.objects.filter(flag_key__icontains='knowledge', is_enabled=True).first()
        extra_context['knowledge_tools_active'] = knowledge_flag is not None
        extra_context['knowledge_tools_status'] = 'Enabled' if knowledge_flag else 'Available'
    except Exception:
        extra_context['community_features_active'] = False
        extra_context['community_feature_status'] = 'Available'
        extra_context['knowledge_tools_active'] = False
        extra_context['knowledge_tools_status'] = 'Available'

    # ── Batches for Report Filters ──
    try:
        from academics.models import Batch
        extra_context['batches'] = _tenant_filter(
            Batch.objects.filter(status__iexact='ACTIVE'), request
        ).order_by('name')[:20]
    except Exception:
        extra_context['batches'] = []

    # ── Report Templates ──
    try:
        from system_config.models import ReportTemplate
        extra_context['report_templates'] = ReportTemplate.objects.filter(is_active=True).order_by('-created_at')[:5]
    except Exception:
        extra_context['report_templates'] = []

    # ── System Health Status (dynamic) ──
    import subprocess, os, platform
    # Database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            extra_context['db_version'] = (cursor.fetchone()[0] or '')[:60]
            cursor.execute("SELECT pg_database_size(current_database())")
            db_bytes = cursor.fetchone()[0] or 0
            extra_context['db_size_mb'] = round(db_bytes / (1024 * 1024), 1)
        extra_context['db_status'] = 'Online'
    except Exception:
        extra_context['db_status'] = 'Error'
        extra_context['db_version'] = ''
        extra_context['db_size_mb'] = 0

    # Server info
    import time
    extra_context['server_hostname'] = platform.node()
    extra_context['server_python'] = platform.python_version()
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_sec = float(f.read().split()[0])
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            extra_context['server_uptime'] = f"{days}d {hours}h"
    except Exception:
        extra_context['server_uptime'] = 'N/A'

    # Disk usage
    try:
        st = os.statvfs('/')
        total_gb = (st.f_blocks * st.f_frsize) / (1024**3)
        free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
        used_pct = round((1 - free_gb / total_gb) * 100, 1) if total_gb else 0
        extra_context['disk_total_gb'] = round(total_gb, 1)
        extra_context['disk_free_gb'] = round(free_gb, 1)
        extra_context['disk_used_pct'] = used_pct
    except Exception:
        extra_context['disk_total_gb'] = 0
        extra_context['disk_free_gb'] = 0
        extra_context['disk_used_pct'] = 0

    # Memory
    try:
        with open('/proc/meminfo', 'r') as f:
            mem = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(parts[1].strip().split()[0])  # kB
                    mem[key] = val
            total_mb = mem.get('MemTotal', 0) / 1024
            avail_mb = mem.get('MemAvailable', mem.get('MemFree', 0)) / 1024
            used_pct = round((1 - avail_mb / total_mb) * 100, 1) if total_mb else 0
            extra_context['mem_total_mb'] = round(total_mb)
            extra_context['mem_used_pct'] = used_pct
    except Exception:
        extra_context['mem_total_mb'] = 0
        extra_context['mem_used_pct'] = 0

    # Gunicorn status
    try:
        result = subprocess.run(['systemctl', 'is-active', 'gunicorn'], capture_output=True, text=True, timeout=3)
        extra_context['gunicorn_status'] = result.stdout.strip()
    except Exception:
        extra_context['gunicorn_status'] = 'unknown'

    # Celery status
    try:
        result = subprocess.run(['systemctl', 'is-active', 'celery-worker'], capture_output=True, text=True, timeout=3)
        extra_context['celery_status'] = result.stdout.strip()
    except Exception:
        extra_context['celery_status'] = 'unknown'

    # Table counts
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            extra_context['table_count'] = cursor.fetchone()[0]
    except Exception:
        extra_context['table_count'] = 0

    # ── Chart Data (JSON) ──
    import json

    # Attendance doughnut
    extra_context['attendance_chart_json'] = json.dumps({
        'labels': ['Present', 'Absent', 'Late', 'On Leave'],
        'data': [
            extra_context.get('today_present', 0),
            extra_context.get('today_absent', 0),
            extra_context.get('today_late', 0),
            extra_context.get('today_leave', 0),
        ],
        'colors': ['#16a34a', '#dc2626', '#d97706', '#7c3aed'],
    })

    # Tenant breakdown bar chart
    tb = extra_context.get('tenant_breakdown', [])
    extra_context['tenant_chart_json'] = json.dumps({
        'labels': [t['name'] for t in tb],
        'students': [t['students'] for t in tb],
        'teachers': [t['teachers'] for t in tb],
        'batches': [t['batches'] for t in tb],
    })

    # Enrollment trend — last 7 days
    try:
        from accounts.models import Student as _StudentForChart
        from datetime import date, timedelta
        today = date.today()
        trend_labels = []
        trend_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            trend_labels.append(d.strftime('%b %d'))
            trend_data.append(
                _tenant_filter(_StudentForChart.objects.filter(created_at__date=d), request).count()
            )
        extra_context['enrollment_chart_json'] = json.dumps({
            'labels': trend_labels,
            'data': trend_data,
        })
    except Exception:
        extra_context['enrollment_chart_json'] = json.dumps({'labels': [], 'data': []})

    # Overview pie: students vs teachers vs batches
    extra_context['overview_chart_json'] = json.dumps({
        'labels': ['Students', 'Teachers', 'Batches', 'Tests'],
        'data': [
            extra_context.get('student_count', 0),
            extra_context.get('teacher_count', 0),
            extra_context.get('batch_count', 0),
            extra_context.get('test_count', 0),
        ],
        'colors': ['#3b82f6', '#16a34a', '#d97706', '#dc2626'],
    })

    return original_index(self, request, extra_context=extra_context)


# ═══════════════════════════════════════════════════════════════════
# Model ordering for 'Identity Management' section
# ═══════════════════════════════════════════════════════════════════
# Defines the order in which models appear under the accounts app.
IDENTITY_MODEL_ORDER = [
    # 1. User Lifecycle
    'Student', 'Teacher', 'Admin', 'Parent', 'UserRoleAssignment',
    # 2. Permissions & Roles
    'Permission', 'Role', 'StaffRole',
    # 3. Groups & Assignment
    'UserGroup', 'GroupMembership', 'GroupRoleAssignment',
    # 4. Account Protection
    'SecurityPolicy', 'LoginAttemptLog', 'TrustedDevice',
    # 5. Audit & Monitoring
    'AccessLog', 'AuditEntry', 'BehaviorEvent',
    # 6. Compliance
    'ComplianceRule', 'ConsentRecord', 'DataAccessRequest', 'RetentionPolicy',
]


# Model ordering for 'Live Classes & YouTube' section
# Feature 1: Live Classes -> ScheduledClass, ClassLinkConfigProxy (Streaming Platforms)
# Feature 2: YouTube & Streaming -> YouTubeChannel (merged with Integration Configs)
# Supporting: ClassAccessToken, ClassWatchTime
LIVE_CLASSES_MODEL_ORDER = [
    'ScheduledClass', 'ClassLinkConfigProxy',
    'IntegrationConfigProxy',
    'YouTubeChannel',
    'ClassAccessToken', 'ClassWatchTime',
]

LIVE_CLASSES_ALLOWED = set(LIVE_CLASSES_MODEL_ORDER)


def custom_get_app_list(self, request, app_label=None):
    """Override get_app_list to control model ordering, hide entire apps,
    move models between sections, and create synthetic sidebar sections."""
    app_list = original_get_app_list(self, request, app_label)

    ai_features_models = []
    attendance_rule_models = []
    security_gov_models = []
    website_setting_extra_models = []  # models moved FROM other apps TO Website Setting
    academics_injected_models = []     # modern Student/Teacher moved into Academics

    # ── Pass 1: Collect models to move between sections ──
    for app in app_list:
        if app['app_label'] == 'materials':
            remaining = []
            for m in app['models']:
                if m['object_name'] in ('PhotoGallery', 'Scholarship', 'TopperStudent'):
                    website_setting_extra_models.append(m)
                elif m['object_name'] == 'MaterialAccess':
                    continue  # hide from sidebar
                else:
                    remaining.append(m)
            app['name'] = 'Study Materials'
            app['models'] = remaining

        elif app['app_label'] == 'academics':
            # Hide legacy Users / BatchTeacher — empty tables; real data lives
            # in accounts.Student / accounts.Teacher.
            # Also hide Category, Religion, State — these are internal master
            # data; expose Cities only (Cities already includes state column).
            _HIDDEN_ACADEMICS = {
                'Users', 'BatchTeacher',
                'Category', 'Religion', 'State',
            }
            app['models'] = [
                m for m in app['models']
                if m['object_name'] not in _HIDDEN_ACADEMICS
            ]

    # ── Pass 2: Apply all section reorganization ──
    for app in app_list:
        if app['app_label'] == 'accounts':
            app['name'] = 'Identity Management'
            # Move Student & Teacher visibility into Academics (keep entries in
            # Identity too — each dict can only live in one list, so we move, not clone).
            for m in list(app['models']):
                if m['object_name'] in ('Student', 'Teacher'):
                    academics_injected_models.append(m)
                    app['models'].remove(m)
            model_dict = {m['object_name']: m for m in app['models']}
            ordered = []
            for name in IDENTITY_MODEL_ORDER:
                if name in model_dict:
                    ordered.append(model_dict.pop(name))
            ordered.extend(model_dict.values())
            app['models'] = ordered

        elif app['app_label'] == 'classes':
            app['name'] = 'Live Classes & YouTube'
            model_dict = {m['object_name']: m for m in app['models']
                          if m['object_name'] in LIVE_CLASSES_ALLOWED}
            ordered = []
            for name in LIVE_CLASSES_MODEL_ORDER:
                if name in model_dict:
                    ordered.append(model_dict.pop(name))
            ordered.extend(model_dict.values())
            app['models'] = ordered

        elif app['app_label'] == 'system_config':
            # Extract AI Features → own section
            # Move AttendanceRule → Attendance Management
            # Move ReportTemplate, MFAPolicy → Security & Operational Governance
            # Keep MaintenanceWindow here in Website Setting
            # Remove SystemSetting from sidebar (WebsiteSetting is visible)
            # Rename section to "Website Setting"
            app['name'] = 'Website Setting'
            remaining = []
            for m in app['models']:
                if m['object_name'] == 'AIFeatureConfig':
                    ai_features_models.append(m)
                elif m['object_name'] == 'AttendanceRule':
                    attendance_rule_models.append(m)
                elif m['object_name'] in ('ReportTemplate', 'MFAPolicy'):
                    security_gov_models.append(m)
                elif m['object_name'] in ('SystemSetting', 'IntegrationConfig'):
                    continue  # hide from sidebar (IntegrationConfig shown via proxy in Live Classes)
                else:
                    remaining.append(m)
            # Append models moved from materials: PhotoGallery, Scholarship, TopperStudent
            remaining.extend(website_setting_extra_models)
            app['models'] = remaining

    # Inject AttendanceRule into the Attendance Management section
    for app in app_list:
        if app['app_label'] == 'attendance':
            app['models'].extend(attendance_rule_models)
            break

    # Inject modern Student / Teacher into the Academics section
    # (they live in the accounts app but belong here visually).
    for app in app_list:
        if app['app_label'] == 'academics':
            # Place Students & Teachers first in the Academics section.
            order = {'Student': 0, 'Teacher': 1}
            app['models'] = sorted(
                academics_injected_models + app['models'],
                key=lambda m: (order.get(m['object_name'], 99), m.get('name', ''))
            )
            break

    # Create a standalone "AI Features" sidebar section
    if ai_features_models:
        app_list.append({
            'name': 'AI Features',
            'app_label': 'ai_features',
            'app_url': '/admin/system_config/aifeatureconfig/',
            'has_module_perms': True,
            'models': ai_features_models,
        })

    # Create a standalone "Security & Operational Governance" sidebar section
    if security_gov_models:
        app_list.append({
            'name': 'Security & Operational Governance',
            'app_label': 'security_governance',
            'app_url': '/admin/system_config/',
            'has_module_perms': True,
            'models': security_gov_models,
        })

    # ── Hide entire sidebar sections ──
    HIDDEN_APPS = {'auth', 'communication', 'realtime', 'scheduling', 'authtoken'}
    app_list = [a for a in app_list if not (
        a['app_label'] in HIDDEN_APPS
        or (a['app_label'] == 'audit' and len(a.get('models', [])) == 0)
    )]

    # ── Enforce sidebar section ordering ──
    SECTION_ORDER = [
        'academics',          # Academics
        'assessments',        # Assessments & Tests
        'attendance',         # Attendance Management
        'accounts',           # Identity Management
        'classes',            # Live Classes & YouTube
        'tenants',            # Multi-Tenancy
        'sessions_tracking',  # Session & Activity Tracking
        'materials',          # Study Materials
        'system_config',      # Website Setting
        'ai_features',        # AI Features
        'security_governance', # Security & Operational Governance
    ]
    order_map = {label: idx for idx, label in enumerate(SECTION_ORDER)}
    app_list.sort(key=lambda a: order_map.get(a['app_label'], 999))

    # ── StaffRole-based sidebar subset ────────────────────────────────
    # Non-technical admins get a strict subset of the sidebar driven by the
    # boolean flags on their `AdminUser.staff_role`. Superusers and anyone
    # without a staff_role assignment see everything.
    app_list = _filter_app_list_by_staff_role(request, app_list)

    return app_list


# Map (app_label, object_name) → StaffRole boolean attr.
# A None value means "no capability gate" (always visible when user is staff).
STAFF_ROLE_MODEL_MATRIX = {
    # Academics
    ('academics', 'Batch'):           'can_manage_students',
    ('academics', 'Subject'):         'can_manage_content',
    ('academics', 'Chapter'):         'can_manage_content',
    ('academics', 'Topic'):           'can_manage_content',
    ('academics', 'Group'):           'can_manage_students',
    ('academics', 'School'):          'can_manage_students',
    ('academics', 'City'):            None,
    ('academics', 'AcademicSession'): 'can_manage_settings',
    ('academics', 'Student'):         'can_manage_students',
    ('academics', 'Teacher'):         'can_manage_teachers',
    # Assessments
    ('assessments', 'Test'):          'can_manage_exams',
    ('assessments', 'Question'):      'can_manage_exams',
    ('assessments', 'TestSection'):   'can_manage_exams',
    ('assessments', 'TestAttempt'):   'can_view_reports',
    ('assessments', 'TestAttemptAnswer'): 'can_view_reports',
    ('assessments', 'TestFeedback'):  'can_view_reports',
    ('assessments', 'OfflineTestMark'): 'can_manage_exams',
    # Attendance
    ('attendance', 'Attendance'):             'can_manage_attendance',
    ('attendance', 'AttendanceSummary'):      'can_view_reports',
    ('attendance', 'AttendanceCorrectionRequest'): 'can_manage_attendance',
    ('attendance', 'AttendanceRule'):         'can_manage_settings',
    # Accounts / identity
    ('accounts', 'AdminUser'):        'can_manage_roles',
    ('accounts', 'Parent'):           'can_manage_students',
    ('accounts', 'Role'):             'can_manage_roles',
    ('accounts', 'Permission'):       'can_manage_roles',
    ('accounts', 'StaffRole'):        'can_manage_roles',
    ('accounts', 'UserRoleAssignment'): 'can_manage_roles',
    ('accounts', 'UserGroup'):        'can_manage_roles',
    ('accounts', 'GroupMembership'):  'can_manage_roles',
    ('accounts', 'GroupRoleAssignment'): 'can_manage_roles',
    # Live classes
    ('classes', 'LiveClass'):         'can_manage_exams',
    ('classes', 'StreamingPlatform'): 'can_manage_integrations',
    ('classes', 'YouTubeIntegrationConfig'): 'can_manage_integrations',
    ('classes', 'YouTubeChannel'):    'can_manage_integrations',
    ('classes', 'ClassAccessToken'):  'can_manage_integrations',
    ('classes', 'ClassWatchTime'):    'can_view_reports',
    # Materials
    ('materials', 'StudyMaterial'):   'can_manage_content',
    # Sessions / audit
    ('sessions_tracking', 'UserSession'):  'can_view_audit',
    ('sessions_tracking', 'UserActivity'): 'can_view_audit',
    ('sessions_tracking', 'LoginHistory'): 'can_view_audit',
    ('sessions_tracking', 'UserDevice'):   'can_view_audit',
    # System config / website
    ('system_config', 'FeatureFlag'):        'can_manage_settings',
    ('system_config', 'MaintenanceWindow'):  'can_manage_settings',
    ('system_config', 'WebsiteConfiguration'): 'can_manage_website',
    ('system_config', 'FooterConfig'):       'can_manage_website',
    ('system_config', 'EnquiryForm'):        'can_manage_website',
    ('system_config', 'Testimonial'):        'can_manage_website',
    ('system_config', 'TickerItem'):         'can_manage_website',
    ('system_config', 'WebsiteNews'):        'can_manage_website',
    ('system_config', 'PhotoGallery'):       'can_manage_website',
    ('system_config', 'Scholarship'):        'can_manage_website',
    ('system_config', 'TopperStudent'):      'can_manage_website',
    ('system_config', 'ReportTemplate'):     'can_view_reports',
    ('system_config', 'MFAPolicy'):          'can_manage_settings',
    # AI / tenants
    ('ai_features', 'AIFeature'):     'can_manage_ai',
    ('tenants', 'Tenant'):            'can_manage_settings',
}


def _filter_app_list_by_staff_role(request, app_list):
    user = getattr(request, 'user', None)
    if user is None or user.is_superuser or not user.is_authenticated:
        return app_list
    # AdminUser → staff_role (proxy models / non-AdminUser accounts see all).
    sr = getattr(user, 'staff_role', None)
    if sr is None:
        return app_list
    filtered = []
    for app in app_list:
        app_label = app['app_label']
        kept = []
        for m in app['models']:
            obj_name = m['object_name']
            attr = STAFF_ROLE_MODEL_MATRIX.get((app_label, obj_name), '__unlisted__')
            if attr == '__unlisted__':
                # Unmapped models → visible by default; tighten over time.
                kept.append(m)
            elif attr is None:
                kept.append(m)
            elif bool(getattr(sr, attr, False)):
                kept.append(m)
        if kept:
            app['models'] = kept
            filtered.append(app)
    return filtered


original_get_app_list = admin.AdminSite.get_app_list
admin.AdminSite.get_app_list = custom_get_app_list


# Store original and replace
original_index = admin.AdminSite.index
admin.AdminSite.index = custom_admin_index

# Customize branding
admin.site.site_header = 'ENABLE PROGRAM — Admin Console'
admin.site.site_title = 'ENF Admin'
admin.site.index_title = 'Administration Dashboard'
admin.site.site_url = '/'
