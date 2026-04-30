from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_student_category_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='physically_handicapped',
            field=models.BooleanField(
                default=False,
                help_text='Mark Yes if the student has a physical disability.',
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='tps',
            field=models.BooleanField(
                default=False,
                help_text='Tribal / Priority Scheme flag (Yes/No).',
                verbose_name='TPS',
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='previous_class_marks',
            field=models.CharField(
                blank=True, null=True, max_length=100,
                help_text='Total marks obtained in the previous academic year.',
                verbose_name='Previous Class Marks',
            ),
        ),
        migrations.AddField(
            model_name='teacher',
            name='teacher_district',
            field=models.CharField(
                blank=True, null=True, max_length=100,
                help_text='District where the teacher works (used in the Teacher Code prefix).',
                verbose_name='District',
            ),
        ),
    ]
