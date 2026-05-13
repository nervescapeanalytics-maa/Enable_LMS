# Generated for dry-run / preview feature on 2026-05-13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0006_zipimportlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="testattempt",
            name="is_preview",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text="Admin/teacher dry-run attempt — excluded from grading stats.",
            ),
        ),
        migrations.AddField(
            model_name="testattempt",
            name="preview_actor_type",
            field=models.CharField(
                max_length=20,
                null=True,
                blank=True,
                help_text="ADMIN or TEACHER — who launched this preview attempt.",
            ),
        ),
        migrations.AddField(
            model_name="testattempt",
            name="preview_actor_id",
            field=models.UUIDField(
                null=True,
                blank=True,
                help_text="UUID of the Admin/Teacher who launched this preview attempt.",
            ),
        ),
    ]
