"""Phase 1 nav-RBAC: per-StaffRole UI navigation permission rows."""
import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_staffrole_granular_exam_perms'),
    ]

    operations = [
        migrations.CreateModel(
            name='NavMenuPermission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, help_text='Namespaced nav code, e.g. "nav.exams.list".', max_length=80)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('staff_role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nav_permissions', to='accounts.staffrole')),
            ],
            options={
                'db_table': 'nav_menu_permissions',
                'ordering': ['code'],
            },
        ),
        migrations.AddConstraint(
            model_name='navmenupermission',
            constraint=models.UniqueConstraint(fields=('staff_role', 'code'), name='uq_nav_menu_perm'),
        ),
    ]
