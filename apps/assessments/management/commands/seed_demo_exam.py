"""
seed_demo_exam — idempotent demo data seeder.

Creates / refreshes:
  * Demo Admin (1)
  * Demo Teachers (3)
  * Demo Students (5) enrolled in a demo Batch
  * Demo Subject, Chapter, Batch
  * A demo Test scheduled to START 5 MINUTES FROM NOW, end 2 hours later
  * 8 sample Questions (MCQ_SINGLE / NUMERICAL / TRUE_FALSE) attached to the test

Usage:
    docker compose -p docker exec api python manage.py seed_demo_exam
        [--tenant <id-or-code>] [--password Demo@2026] [--start-mins 5]

Login credentials printed at the end. Safe to re-run; uses get_or_create.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed a demo admin/teacher/student stack + a scheduled demo exam."

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=str, default=None,
                            help='Tenant id or code (default: first tenant).')
        parser.add_argument('--password', type=str, default='Demo@2026',
                            help='Shared password for all demo accounts.')
        parser.add_argument('--start-mins', type=int, default=5,
                            help='Minutes from now when the demo exam starts.')
        parser.add_argument('--domain', type=str, default='automatebot.shop',
                            help='Email domain for demo accounts.')

    def handle(self, *args, **opts):
        from tenants.models import Tenant
        from accounts.models import Admin, Teacher, Student
        from academics.models import Subject, Chapter, Batch
        from assessments.models import Test, Question

        tenant_arg = opts['tenant']
        password = opts['password']
        start_mins = opts['start_mins']
        domain = opts['domain'].strip().lstrip('@')

        if tenant_arg:
            tenant = (Tenant.objects.filter(id=tenant_arg).first()
                      or Tenant.objects.filter(code=tenant_arg).first())
        else:
            tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write(self.style.ERROR('No tenant found. Create one first.'))
            return

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.current_tenant_id', %s, false)",
                            [str(tenant.id)])
        except Exception:
            pass

        now = timezone.now()
        start_at = now + timedelta(minutes=start_mins)
        end_at = start_at + timedelta(hours=2)

        created_accounts = []

        with transaction.atomic():
            # ── Admin ──────────────────────────────────────────────────────
            admin, was_new = Admin.objects.get_or_create(
                tenant=tenant, email=f'demo_admin@{domain}',
                defaults={
                    'first_name': 'Demo', 'last_name': 'Admin',
                    'phone': '9000000000', 'status': 'ACTIVE',
                    'admin_code': 'DEMO-ADM-01',
                    'email_verified': True,
                },
            )
            admin.set_password(password)
            admin.save(update_fields=['password_hash', 'password_changed_at'])
            created_accounts.append(('ADMIN', admin.email, password, 'new' if was_new else 'updated'))

            # ── Subject / Chapter ──────────────────────────────────────────
            subject, _ = Subject.objects.get_or_create(
                tenant=tenant, code='DEMO-PHY',
                defaults={'name': 'Demo Physics'},
            )
            chapter, _ = Chapter.objects.get_or_create(
                tenant=tenant, subject=subject, code='DEMO-PHY-CH1',
                defaults={'name': 'Kinematics (Demo)', 'display_order': 1},
            )

            # ── Batch ──────────────────────────────────────────────────────
            batch, _ = Batch.objects.get_or_create(
                tenant=tenant, code='DEMO-BATCH-2026',
                defaults={
                    'name': 'Demo Batch 2026',
                    'description': 'Auto-generated demo batch.',
                    'class_level': '12',
                    'exam_target': 'JEE',
                    'max_students': 50,
                    'start_date': now.date(),
                    'end_date': (now + timedelta(days=180)).date(),
                    'status': 'ACTIVE',
                },
            )

            # ── Teachers ───────────────────────────────────────────────────
            teachers = []
            for i in range(1, 4):
                t, was_new = Teacher.objects.get_or_create(
                    tenant=tenant, email=f'demo_teacher{i}@{domain}',
                    defaults={
                        'first_name': 'Demo', 'last_name': f'Teacher {i}',
                        'phone': f'910000000{i}', 'status': 'ACTIVE',
                        'email_verified': True,
                    },
                )
                t.set_password(password)
                t.save(update_fields=['password_hash', 'password_changed_at'])
                teachers.append(t)
                created_accounts.append(('TEACHER', t.email, password, 'new' if was_new else 'updated'))

            # ── Students ───────────────────────────────────────────────────
            students = []
            for i in range(1, 6):
                s, was_new = Student.objects.get_or_create(
                    tenant=tenant, email=f'demo_student{i}@{domain}',
                    defaults={
                        'first_name': 'Demo', 'last_name': f'Student {i}',
                        'phone': f'920000000{i}',
                        'student_code': f'DEMO-STU-{i:03d}',
                        'student_class': '12',
                        'exam_target': 'JEE',
                        'status': 'ACTIVE',
                        'batch': batch,
                        'email_verified': True,
                    },
                )
                # ensure batch + password (even on existing)
                if s.batch_id != batch.id:
                    s.batch = batch
                s.set_password(password)
                s.save(update_fields=['password_hash', 'password_changed_at', 'batch'])
                students.append(s)
                created_accounts.append(('STUDENT', s.email, password, 'new' if was_new else 'updated'))

            # ── Test ───────────────────────────────────────────────────────
            primary_teacher = teachers[0]
            test, t_new = Test.objects.update_or_create(
                tenant=tenant, test_code='DEMO-EXAM-001',
                defaults={
                    'title': 'Demo Realtime Exam — Physics Quick Check',
                    'description': 'Auto-seeded demo exam for end-to-end testing.',
                    'instructions': 'Answer all questions. +4 correct / -1 wrong.',
                    'test_type': 'PRACTICE',
                    'exam_target': 'JEE',
                    'difficulty_level': 'MEDIUM',
                    'subject': subject,
                    'chapter': chapter,
                    'batch': batch,
                    'total_duration_minutes': 60,
                    'start_datetime': start_at,
                    'end_datetime': end_at,
                    'total_marks': Decimal('32.00'),
                    'passing_marks': Decimal('12.00'),
                    'passing_percent': Decimal('33.00'),
                    'positive_marks_per_question': Decimal('4.00'),
                    'negative_marks_per_question': Decimal('-1.00'),
                    'max_attempts': 1,
                    'shuffle_questions': False,
                    'allow_review': True,
                    'allow_backward': True,
                    'access_mode': 'BATCH_ONLY',
                    'result_display_mode': 'IMMEDIATE',
                    'show_correct_answers': True,
                    'show_explanations': True,
                    'show_rank': True,
                    'show_percentile': True,
                    'status': 'PUBLISHED',
                    'published_at': now,
                    'published_by': admin.id,
                    'created_by': admin.id,
                    'created_by_type': 'ADMIN',
                    'teacher': primary_teacher,
                    'total_questions': 8,
                    'test_meta': {'demo': True, 'seeded_by': 'seed_demo_exam'},
                },
            )

            # ── Questions (replace any existing demo questions on this test) ──
            Question.objects.filter(test=test, question_code__startswith='DEMO-Q').delete()
            samples = [
                # (type, text, opts(dict|None), correct, explanation)
                ('MCQ_SINGLE', 'A body in uniform motion has',
                 {'A': 'zero acceleration', 'B': 'constant velocity',
                  'C': 'both A and B', 'D': 'none'}, 'C',
                 'Uniform motion → constant velocity → zero acceleration.'),
                ('MCQ_SINGLE', 'SI unit of force is',
                 {'A': 'Joule', 'B': 'Newton', 'C': 'Watt', 'D': 'Pascal'}, 'B',
                 'Force = mass × acceleration → kg·m/s² = Newton.'),
                ('MCQ_SINGLE', 'Acceleration due to gravity (Earth, sea level) is approximately',
                 {'A': '9.8 m/s²', 'B': '9.8 m/s', 'C': '9.8 km/s²', 'D': '98 m/s²'},
                 'A', 'Standard g ≈ 9.8 m/s².'),
                ('MCQ_SINGLE', 'A car accelerates from rest at 2 m/s² for 5 s. Final velocity?',
                 {'A': '5 m/s', 'B': '10 m/s', 'C': '15 m/s', 'D': '20 m/s'}, 'B',
                 'v = u + at = 0 + 2·5 = 10 m/s.'),
                ('TRUE_FALSE', 'Displacement is a vector quantity.',
                 {'A': 'True', 'B': 'False'}, 'A',
                 'Displacement has both magnitude and direction.'),
                ('TRUE_FALSE', 'Speed can be negative.',
                 {'A': 'True', 'B': 'False'}, 'B',
                 'Speed is a scalar; only magnitude → non-negative.'),
                ('NUMERICAL', 'A ball is dropped from rest. Distance fallen in 2 s? (g=10) Answer in metres.',
                 None, '20',
                 's = ½·g·t² = ½·10·4 = 20 m.'),
                ('NUMERICAL', 'Two forces 3 N and 4 N act perpendicularly on a body. Resultant in newtons?',
                 None, '5',
                 '√(3² + 4²) = 5 N.'),
            ]
            for i, (qtype, text, opts_map, correct, expl) in enumerate(samples, start=1):
                q = Question(
                    tenant=tenant, test=test,
                    question_code=f'DEMO-Q{i:02d}',
                    question_text=text,
                    question_type=qtype,
                    difficulty='MEDIUM',
                    subject=subject,
                    chapter=chapter,
                    correct_answer=correct,
                    answer_explanation=expl,
                    positive_marks=Decimal('4.00'),
                    negative_marks=Decimal('-1.00'),
                    question_order=i,
                    is_active=True,
                )
                if opts_map:
                    q.option_a = opts_map.get('A')
                    q.option_b = opts_map.get('B')
                    q.option_c = opts_map.get('C')
                    q.option_d = opts_map.get('D')
                if qtype == 'NUMERICAL':
                    try:
                        q.correct_answer_value = Decimal(correct)
                        q.numerical_tolerance = Decimal('0.01')
                    except Exception:
                        pass
                q.save()

            test.total_questions = Question.objects.filter(
                test=test, is_deleted=False).count()
            test.save(update_fields=['total_questions'])

        # ── Summary ─────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n=== Demo Exam Seeded ==='))
        self.stdout.write(f'Tenant     : {tenant.code} — {tenant.name}')
        self.stdout.write(f'Test code  : {test.test_code} ({"created" if t_new else "updated"})')
        self.stdout.write(f'Title      : {test.title}')
        self.stdout.write(f'Starts at  : {start_at.isoformat()}  ({start_mins} min from now)')
        self.stdout.write(f'Ends at    : {end_at.isoformat()}')
        self.stdout.write(f'Batch      : {batch.code} — {batch.name}')
        self.stdout.write(f'Questions  : {test.total_questions}')
        self.stdout.write(f'Teacher    : {primary_teacher.email}')
        self.stdout.write('\n=== Accounts ===')
        for role, email, pwd, status in created_accounts:
            self.stdout.write(f'  [{role:7}] {email:40}  pw={pwd:10}  ({status})')
        self.stdout.write('\nLogin URLs:')
        self.stdout.write('  Admin   : /admin-login/')
        self.stdout.write('  Teacher : /teacher/login/')
        self.stdout.write('  Student : /login/')
        self.stdout.write(self.style.SUCCESS('\nDone.\n'))
