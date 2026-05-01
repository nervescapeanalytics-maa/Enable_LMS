from django.db import migrations


def seed_flags(apps, schema_editor):
    try:
        from assessments.permissions import ensure_exam_feature_flags
    except Exception:
        return
    try:
        ensure_exam_feature_flags()
    except Exception:
        # Migration must not fail if FeatureFlag model isn't ready in some envs
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('assessments', '0002_alter_offlinetestmarks_options'),
        ('system_config', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed_flags, noop),
    ]
