"""
Hand-written migration:
  1. Rename model BatchStudent → Users (no DB change — db_table was already 'users')
  2. Change related_name on Batch FK from 'batch_students' to 'users'
  3. Re-introduce BatchTeacher as an explicit through-model (matches current models.py)
  4. Wire Batch.teachers M2M through BatchTeacher
"""
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0006_alter_academicsession_options_alter_batch_teachers_and_more'),
        ('accounts', '0005_alter_teacher_table'),
        ('tenants', '0002_row_level_security'),
    ]

    operations = [
        # ── 1. Rename model BatchStudent → Users (state only) ──
        migrations.RenameModel(
            old_name='BatchStudent',
            new_name='Users',
        ),

        # ── 2. Update related_name on Users.batch FK ──
        migrations.AlterField(
            model_name='users',
            name='batch',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users',
                to='academics.batch',
            ),
        ),

        # ── 3. Re-introduce BatchTeacher as explicit through-model ──
        # DB side: recreate the batch_teachers table
        # State side: create the model and rewire M2M
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='BatchTeacher',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('is_primary', models.BooleanField(default=False)),
                        ('assigned_at', models.DateTimeField(default=django.utils.timezone.now)),
                        ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batch_teachers', to='academics.batch')),
                        ('subject', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='academics.subject')),
                        ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teacher_batches', to='accounts.teacher')),
                        ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tenants.tenant')),
                    ],
                    options={
                        'verbose_name': 'Teacher',
                        'verbose_name_plural': 'Teachers',
                        'db_table': 'batch_teachers',
                    },
                ),
                migrations.AlterField(
                    model_name='batch',
                    name='teachers',
                    field=models.ManyToManyField(
                        related_name='teaching_batches',
                        through='academics.BatchTeacher',
                        to='accounts.teacher',
                    ),
                ),
            ],
            database_operations=[
                # Drop the auto M2M table created in 0006
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS "batches_teachers" CASCADE;',
                    reverse_sql=migrations.RunSQL.noop,
                ),
                # Create the explicit through-table
                migrations.RunSQL(
                    sql='''
                        CREATE TABLE IF NOT EXISTS "batch_teachers" (
                            "id" uuid NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
                            "is_primary" boolean NOT NULL DEFAULT false,
                            "assigned_at" timestamptz NOT NULL DEFAULT now(),
                            "batch_id" uuid NOT NULL REFERENCES "batches" ("id") DEFERRABLE INITIALLY DEFERRED,
                            "subject_id" uuid REFERENCES "subject" ("id") DEFERRABLE INITIALLY DEFERRED,
                            "teacher_id" uuid NOT NULL REFERENCES "school_teacher" ("id") DEFERRABLE INITIALLY DEFERRED,
                            "tenant_id" uuid NOT NULL REFERENCES "tenants" ("id") DEFERRABLE INITIALLY DEFERRED
                        );
                    ''',
                    reverse_sql='DROP TABLE IF EXISTS "batch_teachers" CASCADE;',
                ),
            ],
        ),

        # ── 4. Add constraints ──
        migrations.AddConstraint(
            model_name='batchteacher',
            constraint=models.UniqueConstraint(
                fields=['batch', 'teacher', 'subject'],
                name='uq_batch_teacher_subject',
            ),
        ),
    ]
