from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_student_verbose_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='guardian_name',
            field=models.CharField(
                blank=True, null=True, max_length=200,
                verbose_name='Guardian Name',
                help_text='Guardian / mother / legal custodian name (if different from Father).',
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='parent_name',
            field=models.CharField(
                blank=True, null=True, max_length=200,
                verbose_name='Father Name',
                help_text="Father's full name (displayed as 'Father Name' in lists).",
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='parent_phone',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                verbose_name='Father Phone',
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='alternate_contact',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                verbose_name='Guardian Contact',
                help_text='Secondary guardian phone — also shown in the Guardian column.',
            ),
        ),
    ]
