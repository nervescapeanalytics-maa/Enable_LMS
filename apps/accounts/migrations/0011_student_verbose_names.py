from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_student_extras_teacher_district'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='school_name',
            field=models.CharField(
                blank=True, null=True, max_length=300, verbose_name='School Name',
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='city',
            field=models.CharField(max_length=100, verbose_name='City / Village'),
        ),
        migrations.AlterField(
            model_name='student',
            name='district',
            field=models.CharField(
                blank=True, null=True, max_length=100, verbose_name='District',
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='state',
            field=models.CharField(max_length=100, verbose_name='State'),
        ),
    ]
