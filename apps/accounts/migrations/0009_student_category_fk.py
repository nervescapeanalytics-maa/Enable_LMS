from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0001_initial'),
        ('accounts', '0008_add_passout_class_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students',
                to='academics.category',
                help_text='Student category (e.g. JEE, NEET, Foundation).',
            ),
        ),
    ]
