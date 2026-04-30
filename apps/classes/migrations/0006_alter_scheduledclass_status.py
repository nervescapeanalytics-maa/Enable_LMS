# Generated 2026-03-31: Add extended status choices for ScheduledClass
# (merged from claude/zealous-brattain SQL→Django mapping work)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0005_teacher_join_tracking'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduledclass',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('SCHEDULED', 'Scheduled'),
                    ('STANDBY', 'Standby'),
                    ('LIVE', 'Live'),
                    ('COMPLETED', 'Completed'),
                    ('CANCELLED', 'Cancelled'),
                    ('RESCHEDULED', 'Rescheduled'),
                    ('ARCHIVED', 'Archived'),
                ],
                default='DRAFT',
                max_length=15,
            ),
        ),
    ]
