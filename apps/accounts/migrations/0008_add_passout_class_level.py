from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_batchpromotion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='student_class',
            field=models.CharField(
                choices=[
                    ('9', 'Class 9'),
                    ('10', 'Class 10'),
                    ('11', 'Class 11'),
                    ('12', 'Class 12'),
                    ('PASS', 'Class 12 Passout'),
                ],
                db_column='class_level',
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name='studentpromotion',
            name='from_class',
            field=models.CharField(
                choices=[
                    ('9', 'Class 9'),
                    ('10', 'Class 10'),
                    ('11', 'Class 11'),
                    ('12', 'Class 12'),
                    ('PASS', 'Class 12 Passout'),
                ],
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name='studentpromotion',
            name='to_class',
            field=models.CharField(
                choices=[
                    ('9', 'Class 9'),
                    ('10', 'Class 10'),
                    ('11', 'Class 11'),
                    ('12', 'Class 12'),
                    ('PASS', 'Class 12 Passout'),
                ],
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name='batchpromotion',
            name='from_class',
            field=models.CharField(
                choices=[
                    ('9', 'Class 9'),
                    ('10', 'Class 10'),
                    ('11', 'Class 11'),
                    ('12', 'Class 12'),
                    ('PASS', 'Class 12 Passout'),
                ],
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name='batchpromotion',
            name='to_class',
            field=models.CharField(
                choices=[
                    ('9', 'Class 9'),
                    ('10', 'Class 10'),
                    ('11', 'Class 11'),
                    ('12', 'Class 12'),
                    ('PASS', 'Class 12 Passout'),
                ],
                max_length=5,
            ),
        ),
    ]
