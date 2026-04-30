from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove the separate guardian_name and alternate_contact (guardian phone)
    columns from the students table.  These are now merged into parent_name
    (Father / Guardian Name) and parent_phone (Father / Guardian Phone).
    """

    dependencies = [
        ('accounts', '0012_student_parent_guardian_labels'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='guardian_name',
        ),
        migrations.RemoveField(
            model_name='student',
            name='alternate_contact',
        ),
    ]
