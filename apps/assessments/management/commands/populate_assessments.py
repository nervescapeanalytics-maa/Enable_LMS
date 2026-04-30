"""
Management command to populate demo data for Assessments & Tests.
Creates: Tests, Questions, TestAttempts, TestAttemptAnswers.
"""
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Populate demo test, question, attempt and answer data for the assessments module.'

    def add_arguments(self, parser):
        parser.add_argument('--tests', type=int, default=6, help='Number of tests to create')
        parser.add_argument('--questions-per-test', type=int, default=15, help='Questions per test')

    def handle(self, *args, **options):
        from tenants.models import Tenant
        from accounts.models import Student, Teacher
        from academics.models import Batch
        from assessments.models import Test, Question, TestAttempt, TestAttemptAnswer

        tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write('No tenant found. Create a tenant first.')
            return

        # Set PostgreSQL RLS context so inserts pass row-level security
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(tenant.id)])

        # Auto-create demo batches if none exist
        if Batch.objects.filter(tenant=tenant).count() == 0:
            self.stdout.write('Creating demo batches …')
            for code, name in [('B-JEE-2025', 'JEE 2025 Batch'), ('B-NEET-2025', 'NEET 2025 Batch'), ('B-GEN-2025', 'General 2025')]:
                Batch.objects.create(tenant=tenant, code=code, name=name, status='ACTIVE')

        # Auto-create demo teachers if none exist
        if Teacher.objects.filter(tenant=tenant).count() == 0:
            self.stdout.write('Creating demo teachers …')
            teacher_data = [
                ('T-001', 'Rajesh', 'Sharma', 'rajesh.sharma@demo.lms', '9100000001'),
                ('T-002', 'Priya', 'Verma', 'priya.verma@demo.lms', '9100000002'),
                ('T-003', 'Amit', 'Patel', 'amit.patel@demo.lms', '9100000003'),
            ]
            for code, fn, ln, email, phone in teacher_data:
                Teacher.objects.create(
                    tenant=tenant, teacher_code=code, first_name=fn, last_name=ln,
                    email=email, phone=phone, password_hash='demo', status='ACTIVE',
                    department='Science', employment_type='FULL_TIME',
                )

        # Auto-create demo students if none exist
        if Student.objects.filter(tenant=tenant).count() == 0:
            self.stdout.write('Creating demo students …')
            first_names = ['Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Sai', 'Reyansh', 'Ayaan', 'Krishna', 'Ishaan',
                           'Ananya', 'Diya', 'Myra', 'Sara', 'Aanya', 'Aadhya', 'Ira', 'Saanvi', 'Pari', 'Anika']
            last_names = ['Kumar', 'Singh', 'Gupta', 'Reddy', 'Sharma', 'Patel', 'Joshi', 'Verma', 'Rao', 'Mishra']
            batches_list = list(Batch.objects.filter(tenant=tenant))
            for i, fn in enumerate(first_names):
                ln = last_names[i % len(last_names)]
                Student.objects.create(
                    tenant=tenant, student_code=f'STU-{i+1:04d}',
                    first_name=fn, last_name=ln,
                    email=f'{fn.lower()}.{ln.lower()}@demo.lms', phone=f'91000{10000+i}',
                    password_hash='demo', status='ACTIVE',
                    student_class='11', exam_target='JEE',
                    city='Hyderabad', state='Telangana', pin_code='500001',
                    batch=random.choice(batches_list) if batches_list else None,
                )

        students = list(Student.objects.filter(tenant=tenant, status='ACTIVE')[:20])
        teachers = list(Teacher.objects.filter(tenant=tenant)[:5])
        batches = list(Batch.objects.filter(tenant=tenant, status__iexact='ACTIVE')[:4])

        if not students:
            self.stderr.write('No students found even after auto-creation.')
            return

        num_tests = options['tests']
        q_per_test = options['questions_per_test']

        test_definitions = [
            ('Physics Unit Test 1', 'UNIT', 'JEE', 'EASY'),
            ('Chemistry Mid-Term', 'MID_TERM', 'NEET', 'MODERATE'),
            ('Mathematics Weekly Quiz', 'QUIZ', 'JEE', 'EASY'),
            ('Biology Practice Test', 'PRACTICE', 'NEET', 'MODERATE'),
            ('Physics Final Exam', 'FINAL', 'BOTH', 'HARD'),
            ('Chemistry Mock Test', 'MOCK', 'JEE', 'MODERATE'),
            ('General Aptitude Quiz', 'QUIZ', 'BOTH', 'EASY'),
            ('Mathematics Full Test', 'FULL_TEST', 'JEE', 'HARD'),
        ]

        question_templates = {
            'MCQ': [
                ('What is the SI unit of force?', 'Newton', 'Joule', 'Watt', 'Pascal', 'A'),
                ('Which element has atomic number 6?', 'Nitrogen', 'Oxygen', 'Carbon', 'Boron', 'C'),
                ('What is the derivative of sin(x)?', 'cos(x)', '-cos(x)', 'sin(x)', '-sin(x)', 'A'),
                ('Which organelle is the powerhouse of the cell?', 'Nucleus', 'Ribosome', 'Mitochondria', 'Golgi', 'C'),
                ('What is the speed of light?', '3×10⁸ m/s', '3×10⁶ m/s', '3×10¹⁰ m/s', '3×10⁴ m/s', 'A'),
                ('pH of pure water at 25°C is?', '6', '7', '8', '14', 'B'),
                ('∫ 2x dx equals?', 'x', 'x²', '2x²', 'x² + C', 'D'),
                ('Which gas is most abundant in atmosphere?', 'Oxygen', 'Nitrogen', 'CO₂', 'Argon', 'B'),
                ('Value of acceleration due to gravity?', '9.8 m/s²', '10.2 m/s²', '8.9 m/s²', '11 m/s²', 'A'),
                ('Chemical formula of glucose?', 'C₆H₁₂O₆', 'C₆H₆', 'CH₃COOH', 'NaCl', 'A'),
                ('What is 15² ?', '215', '225', '235', '245', 'B'),
                ('DNA stands for?', 'Deoxyribo Nucleic Acid', 'Dioxyribo Nucleic Acid', 'Denatured Nucleic Acid', 'None', 'A'),
                ('Ohm\'s law relates?', 'V, I, R', 'P, V, I', 'F, m, a', 'E, m, c', 'A'),
                ('Molarity is expressed in?', 'mol/L', 'g/L', 'mol/kg', 'g/mol', 'A'),
                ('What is log₁₀(1000)?', '2', '3', '4', '10', 'B'),
            ],
            'TRUE_FALSE': [
                ('The Earth revolves around the Sun.', 'True', 'False', '', '', 'A'),
                ('Water is a compound of hydrogen and nitrogen.', 'True', 'False', '', '', 'B'),
                ('π is a rational number.', 'True', 'False', '', '', 'B'),
            ],
            'NUMERICAL': [
                ('If F = ma, and m=5kg, a=3m/s², what is F in Newtons?', '15', '', '', '', 'A'),
                ('What is 7 × 8?', '56', '', '', '', 'A'),
            ],
        }

        now = timezone.now()
        tests_created = 0
        questions_created = 0
        attempts_created = 0

        for i in range(min(num_tests, len(test_definitions))):
            title, test_type, target, difficulty = test_definitions[i]
            test_code = f'TST-{now.year}-{i+1:04d}'

            teacher = random.choice(teachers) if teachers else None
            batch = random.choice(batches) if batches else None

            test = Test.objects.create(
                tenant=tenant,
                test_code=test_code,
                title=title,
                test_type=test_type,
                exam_target=target,
                difficulty_level=difficulty,
                batch=batch,
                created_by=teacher.id if teacher else None,
                total_marks=Decimal(q_per_test * 4),
                passing_marks=Decimal(q_per_test * 4 * 0.35),
                negative_marks_per_question=Decimal('1.00'),
                total_duration_minutes=60 + i * 10,
                start_datetime=now - timedelta(days=random.randint(1, 30)),
                end_datetime=now + timedelta(days=random.randint(1, 15)),
                status='PUBLISHED',
                instructions=f'This is a {difficulty.lower()} level {test_type.replace("_"," ").lower()}. Answer all questions carefully.',
            )
            tests_created += 1

            # Create questions
            test_questions = []
            all_q = list(question_templates['MCQ'])
            random.shuffle(all_q)
            for qi in range(q_per_test):
                q_type = 'MCQ'
                if qi >= len(all_q):
                    qi_idx = qi % len(all_q)
                else:
                    qi_idx = qi
                q_text, opt_a, opt_b, opt_c, opt_d, correct = all_q[qi_idx]

                q = Question.objects.create(
                    tenant=tenant,
                    test=test,
                    question_order=qi + 1,
                    question_type=q_type,
                    question_text=q_text,
                    option_a=opt_a,
                    option_b=opt_b,
                    option_c=opt_c if opt_c else None,
                    option_d=opt_d if opt_d else None,
                    correct_answer=correct,
                    positive_marks=Decimal('4.00'),
                    negative_marks=Decimal('1.00'),
                    difficulty=random.choice(['EASY', 'MODERATE', 'HARD']),
                )
                test_questions.append(q)
                questions_created += 1

            # Create test attempts for random students
            attempt_students = random.sample(students, min(len(students), random.randint(5, 12)))
            for student in attempt_students:
                marks = Decimal('0')
                correct_count = 0
                wrong_count = 0
                answers = []

                for q in test_questions:
                    chose = random.choice(['A', 'B', 'C', 'D', None])
                    is_correct = (chose == q.correct_answer) if chose else False
                    if is_correct:
                        awarded = q.positive_marks or Decimal('4.00')
                        correct_count += 1
                    elif chose:
                        awarded = -Decimal('1.00')
                        wrong_count += 1
                    else:
                        awarded = Decimal('0')

                    marks += awarded
                    answers.append({
                        'question': q,
                        'selected': chose,
                        'is_correct': is_correct,
                        'marks_awarded': awarded,
                    })

                marks = max(marks, Decimal('0'))
                total = test.total_marks or Decimal('60')
                pct = (marks / total * 100) if total > 0 else Decimal('0')
                result = 'PASS' if marks >= (test.passing_marks or Decimal('21')) else 'FAIL'

                unanswered = q_per_test - correct_count - wrong_count
                attempt = TestAttempt.objects.create(
                    tenant=tenant,
                    test=test,
                    student=student,
                    started_at=now - timedelta(hours=random.randint(1, 48)),
                    submitted_at=now - timedelta(minutes=random.randint(5, 120)),
                    raw_score=marks,
                    total_marks=test.total_marks,
                    percentage=pct,
                    result=result,
                    status='SUBMITTED',
                    correct=correct_count,
                    incorrect=wrong_count,
                    skipped=unanswered,
                    attempted=correct_count + wrong_count,
                    total_questions=q_per_test,
                    time_taken_seconds=random.randint(1800, 3600),
                )
                attempts_created += 1

                # Create answer records
                for ans in answers:
                    TestAttemptAnswer.objects.create(
                        tenant=tenant,
                        attempt=attempt,
                        question=ans['question'],
                        student_answer=ans['selected'] or '',
                        is_correct=ans['is_correct'],
                        marks_awarded=ans['marks_awarded'],
                        time_spent_seconds=random.randint(30, 240),
                    )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Created {tests_created} tests, {questions_created} questions, '
            f'{attempts_created} attempts with answers.'
        ))
