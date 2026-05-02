# Generated for offline test marks linkage to Test + Batch.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0004_phase4_test_version_and_settings"),
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="offlinetestmarks",
            name="test",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offline_marks",
                to="assessments.test",
            ),
        ),
        migrations.AddField(
            model_name="offlinetestmarks",
            name="batch",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offline_marks",
                to="academics.batch",
            ),
        ),
        migrations.AddIndex(
            model_name="offlinetestmarks",
            index=models.Index(fields=["tenant", "test"], name="idx_offline_test"),
        ),
        migrations.AddIndex(
            model_name="offlinetestmarks",
            index=models.Index(fields=["tenant", "batch"], name="idx_offline_batch"),
        ),
    ]
