# Drop eduassist tables (app removed from INSTALLED_APPS)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_alter_batchstudent_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS eduassist_messages CASCADE;",
                "DROP TABLE IF EXISTS eduassist_conversations CASCADE;",
                "DELETE FROM auth_permission WHERE content_type_id IN (SELECT id FROM django_content_type WHERE app_label = 'eduassist');",
                "DELETE FROM django_admin_log WHERE content_type_id IN (SELECT id FROM django_content_type WHERE app_label = 'eduassist');",
                "DELETE FROM django_content_type WHERE app_label = 'eduassist';",
                "DELETE FROM django_migrations WHERE app = 'eduassist';",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
