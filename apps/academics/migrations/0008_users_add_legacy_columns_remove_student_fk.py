"""
Hand-written migration:
  1. Remove the 'student' ForeignKey to accounts.Student → plain UUIDField
  2. Add all 22 legacy columns from legacy_exam.users to public.users
  3. Synchronize Django state with the new schema

The columns exist in 'legacy_exam.users' but not yet in 'public.users'.
This migration adds them to the public schema table.
"""
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0007_rename_batchstudent_to_users'),
        ('accounts', '0005_alter_teacher_table'),
        ('tenants', '0002_row_level_security'),
    ]

    operations = [
        # ── 1. DB: Drop student_id FK constraint & make nullable ──
        migrations.RunSQL(
            sql="""
                DO $$
                DECLARE r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT con.conname
                        FROM pg_constraint con
                        JOIN pg_attribute att ON att.attrelid = con.conrelid
                                             AND att.attnum = ANY(con.conkey)
                        WHERE con.conrelid = 'public.users'::regclass
                          AND con.contype = 'f'
                          AND att.attname = 'student_id'
                    ) LOOP
                        EXECUTE format('ALTER TABLE public.users DROP CONSTRAINT %I', r.conname);
                    END LOOP;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE public.users ALTER COLUMN student_id DROP NOT NULL;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        # ── 2. DB: Add all 22 legacy columns to public.users ──
        migrations.RunSQL(
            sql="""
                ALTER TABLE public.users
                    ADD COLUMN IF NOT EXISTS uid              integer          NULL,
                    ADD COLUMN IF NOT EXISTS name             varchar(50)      NULL,
                    ADD COLUMN IF NOT EXISTS father_name      varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS dob              timestamp        NULL,
                    ADD COLUMN IF NOT EXISTS gender           varchar(10)      NULL,
                    ADD COLUMN IF NOT EXISTS phone            varchar(50)      NULL,
                    ADD COLUMN IF NOT EXISTS phone1           varchar(10)      NULL,
                    ADD COLUMN IF NOT EXISTS email            varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS userid           varchar(20)      NULL,
                    ADD COLUMN IF NOT EXISTS password         varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS photo            varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS category         varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS handicapped      varchar(100)     NULL,
                    ADD COLUMN IF NOT EXISTS other_school     varchar(200)     NULL,
                    ADD COLUMN IF NOT EXISTS city_name        varchar(500)     NULL,
                    ADD COLUMN IF NOT EXISTS previous_class_marks varchar(100) NULL,
                    ADD COLUMN IF NOT EXISTS tps              boolean          NULL,
                    ADD COLUMN IF NOT EXISTS status           varchar(10)      NULL,
                    ADD COLUMN IF NOT EXISTS date             timestamp        NULL,
                    ADD COLUMN IF NOT EXISTS session_id       integer          NULL,
                    ADD COLUMN IF NOT EXISTS cid              integer          NULL,
                    ADD COLUMN IF NOT EXISTS school_id        integer          NULL,
                    ADD COLUMN IF NOT EXISTS state_id         integer          NULL,
                    ADD COLUMN IF NOT EXISTS city_id          integer          NULL;
            """,
            reverse_sql="""
                ALTER TABLE public.users
                    DROP COLUMN IF EXISTS uid,
                    DROP COLUMN IF EXISTS name,
                    DROP COLUMN IF EXISTS father_name,
                    DROP COLUMN IF EXISTS dob,
                    DROP COLUMN IF EXISTS gender,
                    DROP COLUMN IF EXISTS phone,
                    DROP COLUMN IF EXISTS phone1,
                    DROP COLUMN IF EXISTS email,
                    DROP COLUMN IF EXISTS userid,
                    DROP COLUMN IF EXISTS password,
                    DROP COLUMN IF EXISTS photo,
                    DROP COLUMN IF EXISTS category,
                    DROP COLUMN IF EXISTS handicapped,
                    DROP COLUMN IF EXISTS other_school,
                    DROP COLUMN IF EXISTS city_name,
                    DROP COLUMN IF EXISTS previous_class_marks,
                    DROP COLUMN IF EXISTS tps,
                    DROP COLUMN IF EXISTS status,
                    DROP COLUMN IF EXISTS date,
                    DROP COLUMN IF EXISTS session_id,
                    DROP COLUMN IF EXISTS cid,
                    DROP COLUMN IF EXISTS school_id,
                    DROP COLUMN IF EXISTS state_id,
                    DROP COLUMN IF EXISTS city_id;
            """,
        ),

        # ── 3. DB: Add unique index on uid ──
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX IF NOT EXISTS idx_users_uid ON public.users (uid) WHERE uid IS NOT NULL;',
            reverse_sql='DROP INDEX IF EXISTS idx_users_uid;',
        ),

        # ── 4. State-only: Sync Django model state ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Remove old FK field
                migrations.RemoveField(
                    model_name='users',
                    name='student',
                ),
                # Add student_id as plain UUID
                migrations.AddField(
                    model_name='users',
                    name='student_id',
                    field=models.UUIDField(blank=True, null=True),
                ),
                # Legacy integer PK
                migrations.AddField(
                    model_name='users',
                    name='uid',
                    field=models.IntegerField(blank=True, null=True, unique=True),
                ),
                # Student profile fields
                migrations.AddField(
                    model_name='users',
                    name='name',
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='father_name',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='dob',
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='gender',
                    field=models.CharField(blank=True, max_length=10, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='phone',
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='phone1',
                    field=models.CharField(blank=True, max_length=10, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='email',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='userid',
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='photo',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='category',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='handicapped',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='other_school',
                    field=models.CharField(blank=True, max_length=200, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='city_name',
                    field=models.CharField(blank=True, max_length=500, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='previous_class_marks',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='tps',
                    field=models.BooleanField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='status',
                    field=models.CharField(blank=True, max_length=10, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='date',
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='password',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                # Legacy FK IDs (integer keys from SQL Server)
                migrations.AddField(
                    model_name='users',
                    name='session_id',
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='cid',
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='school_id',
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='state_id',
                    field=models.IntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='users',
                    name='city_id',
                    field=models.IntegerField(blank=True, null=True),
                ),
                # Update Meta
                migrations.AlterModelOptions(
                    name='users',
                    options={
                        'verbose_name': 'Student',
                        'verbose_name_plural': 'Students',
                    },
                ),
            ],
            database_operations=[
                # Already handled above
            ],
        ),
    ]
