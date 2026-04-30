"""Seed default report templates."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create default report templates for the Reporting Center.'

    def handle(self, *args, **options):
        from system_config.models import ReportTemplate
        from tenants.models import Tenant

        tenant = Tenant.objects.first()

        # Set PostgreSQL RLS context
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(tenant.id)])

        templates = [
            {
                'name': 'Daily Attendance Summary',
                'description': 'Today\'s attendance for all students and teachers.',
                'report_type': 'ATTENDANCE',
                'default_format': 'EXCEL',
                'filters_json': {'date_range': 'today', 'user_type': 'all'},
                'columns_json': ['Date', 'User Type', 'User ID', 'Status', 'Source'],
            },
            {
                'name': 'Active Students List',
                'description': 'Export all currently active students with fee status.',
                'report_type': 'STUDENT',
                'default_format': 'EXCEL',
                'filters_json': {'status': 'ACTIVE'},
                'columns_json': ['Code', 'Name', 'Email', 'Phone', 'Class', 'Fee Status'],
            },
            {
                'name': 'Fee Pending Students',
                'description': 'Students with pending or overdue fee payments.',
                'report_type': 'STUDENT',
                'default_format': 'CSV',
                'filters_json': {'status': 'ACTIVE', 'fee_status': 'PENDING'},
                'columns_json': ['Code', 'Name', 'Email', 'Phone', 'Class', 'Fee Status'],
            },
            {
                'name': 'Monthly Attendance Report',
                'description': 'Last 30 days attendance across all batches.',
                'report_type': 'ATTENDANCE',
                'default_format': 'EXCEL',
                'filters_json': {'date_range': 'month'},
                'columns_json': ['Date', 'User Type', 'User ID', 'Status', 'Source', 'Batch'],
            },
            {
                'name': 'Teacher Directory',
                'description': 'All active teachers with department and contact info.',
                'report_type': 'TEACHER',
                'default_format': 'EXCEL',
                'filters_json': {'status': 'ACTIVE'},
                'columns_json': ['Code', 'Name', 'Email', 'Phone', 'Department', 'Employment Type'],
            },
        ]

        created = 0
        for tpl in templates:
            _, was_created = ReportTemplate.objects.get_or_create(
                name=tpl['name'],
                defaults={
                    'tenant': tenant,
                    'description': tpl['description'],
                    'report_type': tpl['report_type'],
                    'default_format': tpl['default_format'],
                    'filters_json': tpl['filters_json'],
                    'columns_json': tpl['columns_json'],
                    'is_active': True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Created {created} report templates ({len(templates) - created} already existed).'))
