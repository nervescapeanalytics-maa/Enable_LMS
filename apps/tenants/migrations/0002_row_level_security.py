"""
Row-Level Security (RLS) for tenant data isolation.

Adds PostgreSQL RLS policies on all tenant-scoped tables so that
even if application code forgets to filter by tenant_id, the database
itself blocks cross-tenant reads/writes.

The app variable `app.current_tenant_id` is expected to be set per
connection by middleware (see TenantMiddleware.process_request).
When the variable is empty (e.g. super-admin or admin panel), RLS
is bypassed via FORCE ROW LEVEL SECURITY = FALSE on the app DB role.
"""
from django.db import migrations

TENANT_TABLES = [
    'students', 'teachers', 'admins', 'parents',
    'batches', 'batch_students', 'batch_teachers',
    'academic_sessions', 'subjects', 'chapters', 'topics',
    'categories', 'groups', 'subject_sections',
    'scheduled_classes', 'recurring_class_templates',
    'class_access_tokens', 'class_watch_times', 'youtube_channels',
    'roles', 'staff_roles', 'user_role_assignments',
    'user_groups', 'group_memberships', 'group_role_assignments',
    'schools', 'attendance', 'study_materials',
]

ENABLE_SQL = []
DISABLE_SQL = []

for table in TENANT_TABLES:
    policy_name = f"rls_{table}_tenant"
    ENABLE_SQL.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    ENABLE_SQL.append(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
    ENABLE_SQL.append(
        f"DROP POLICY IF EXISTS {policy_name} ON {table};"
    )
    ENABLE_SQL.append(
        f"CREATE POLICY {policy_name} ON {table} "
        f"USING ( "
        f"  current_setting('app.current_tenant_id', true) = '' "
        f"  OR tenant_id::text = current_setting('app.current_tenant_id', true) "
        f");"
    )
    DISABLE_SQL.append(f"DROP POLICY IF EXISTS {policy_name} ON {table};")
    DISABLE_SQL.append(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")


class Migration(migrations.Migration):
    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="\n".join(ENABLE_SQL),
            reverse_sql="\n".join(DISABLE_SQL),
        ),
    ]
