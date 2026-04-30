"""
Seed Assessments demo data for Physics + Chemistry, classes 9-12.
- Creates Subjects (Physics, Chemistry) if missing
- Creates 1 Chapter + 1 Topic per (subject, class)
- Creates 1 published Test per (subject, class) with 5 MCQ questions each
- Picks one student per class to attempt one test (auto-graded)
"""
import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from tenants.models import Tenant
from accounts.models import Student, Teacher
from academics.models import Subject, Chapter, Topic
from assessments.models import (
    Test, TestSection, Question, TestAttempt, TestAttemptAnswer,
)


# ── Fixed bank of 5 MCQs per (subject, class) ──────────────────────
QUESTION_BANK = {
    ('PHYSICS', '9'): [
        ('Force is measured in which SI unit?', 'Newton', 'Joule', 'Watt', 'Pascal', 'A'),
        ('Acceleration is the rate of change of:', 'Speed', 'Velocity', 'Mass', 'Distance', 'B'),
        ('SI unit of pressure is:', 'Newton', 'Pascal', 'Joule', 'Hertz', 'B'),
        ('Sound travels fastest in:', 'Air', 'Water', 'Steel', 'Vacuum', 'C'),
        ('Work done is product of:', 'Force × Distance', 'Mass × Velocity', 'Power × Time', 'Force × Velocity', 'A'),
    ],
    ('PHYSICS', '10'): [
        ('Ohm\'s law states V = ?', 'I × R', 'I / R', 'I + R', 'I − R', 'A'),
        ('Convex lens converges or diverges light?', 'Diverges', 'Converges', 'Both', 'Neither', 'B'),
        ('SI unit of electric current is:', 'Volt', 'Ohm', 'Ampere', 'Watt', 'C'),
        ('Magnetic field around a wire is:', 'Linear', 'Circular', 'Triangular', 'Random', 'B'),
        ('Power is rate of doing:', 'Force', 'Energy', 'Work', 'Mass', 'C'),
    ],
    ('PHYSICS', '11'): [
        ('Dimensional formula of momentum is:', '[MLT⁻¹]', '[MLT⁻²]', '[ML²T⁻²]', '[MT⁻¹]', 'A'),
        ('Kepler\'s 3rd law: T² ∝ ?', 'r', 'r²', 'r³', '1/r', 'C'),
        ('Escape velocity from Earth (km/s):', '7.9', '11.2', '15.0', '20.5', 'B'),
        ('Bernoulli\'s principle relates pressure and:', 'Mass', 'Velocity', 'Density only', 'Temperature', 'B'),
        ('SHM time period of pendulum depends on:', 'Mass', 'Length', 'Amplitude', 'Color', 'B'),
    ],
    ('PHYSICS', '12'): [
        ('Capacitance unit is:', 'Henry', 'Farad', 'Ohm', 'Tesla', 'B'),
        ('Photoelectric effect was explained by:', 'Newton', 'Einstein', 'Bohr', 'Maxwell', 'B'),
        ('In an LCR series circuit, resonance occurs when:', 'XL = XC', 'XL > XC', 'XL < XC', 'R = 0', 'A'),
        ('de Broglie wavelength λ = ?', 'h/p', 'p/h', 'hν', 'h × p', 'A'),
        ('A diode conducts only in:', 'Forward bias', 'Reverse bias', 'Both', 'Neither', 'A'),
    ],
    ('CHEMISTRY', '9'): [
        ('Chemical formula of water:', 'H₂O', 'CO₂', 'NaCl', 'O₂', 'A'),
        ('Atomic number of carbon is:', '4', '6', '8', '12', 'B'),
        ('pH of pure water is:', '0', '7', '10', '14', 'B'),
        ('Smallest particle of matter is:', 'Atom', 'Cell', 'Molecule', 'Proton', 'A'),
        ('Symbol of sodium is:', 'S', 'Na', 'So', 'N', 'B'),
    ],
    ('CHEMISTRY', '10'): [
        ('Reaction with oxygen is called:', 'Reduction', 'Oxidation', 'Hydration', 'Dilution', 'B'),
        ('Vinegar contains:', 'Acetic acid', 'HCl', 'NaOH', 'H₂SO₄', 'A'),
        ('Hardest natural substance is:', 'Iron', 'Diamond', 'Quartz', 'Steel', 'B'),
        ('Group 1 elements are called:', 'Halogens', 'Alkali metals', 'Noble gases', 'Transition metals', 'B'),
        ('Color of CuSO₄ solution is:', 'Red', 'Blue', 'Green', 'Yellow', 'B'),
    ],
    ('CHEMISTRY', '11'): [
        ('Avogadro\'s number is:', '6.022 × 10²³', '9.1 × 10⁻³¹', '1.6 × 10⁻¹⁹', '3 × 10⁸', 'A'),
        ('Hybridization in CH₄ is:', 'sp', 'sp²', 'sp³', 'sp³d', 'C'),
        ('Most electronegative element:', 'O', 'F', 'Cl', 'N', 'B'),
        ('Ideal gas equation is:', 'PV = nRT', 'PV = mRT', 'P/V = nRT', 'PT = nRV', 'A'),
        ('IUPAC name of CH₃COOH:', 'Methanoic acid', 'Ethanoic acid', 'Propanoic acid', 'Butanoic acid', 'B'),
    ],
    ('CHEMISTRY', '12'): [
        ('Number of electrons in p-orbital max:', '2', '6', '10', '14', 'B'),
        ('SN1 reaction proceeds via:', 'Carbocation', 'Carbanion', 'Free radical', 'Carbene', 'A'),
        ('Faraday\'s constant is approximately:', '96500 C', '8.314 J', '6.022 × 10²³', '1.6 × 10⁻¹⁹', 'A'),
        ('Aldol condensation produces:', 'Alcohol', 'β-hydroxy carbonyl', 'Ester', 'Amide', 'B'),
        ('Coordination number of Ni in [Ni(CO)₄]:', '2', '4', '6', '8', 'B'),
    ],
}


def seed():
    tenant = Tenant.objects.first()
    print(f'Tenant: {tenant.name}')

    # 1. Subjects
    physics, _ = Subject.objects.get_or_create(
        tenant=tenant, name='Physics',
        defaults={'code': 'PHY', 'subject_type': 'PHYSICS', 'color': '#3b82f6'},
    )
    chemistry, _ = Subject.objects.get_or_create(
        tenant=tenant, name='Chemistry',
        defaults={'code': 'CHE', 'subject_type': 'CHEMISTRY', 'color': '#10b981'},
    )
    print(f'Subjects: Physics({physics.id}), Chemistry({chemistry.id})')

    classes = ['9', '10', '11', '12']
    subjects = [('PHYSICS', physics), ('CHEMISTRY', chemistry)]

    teacher = Teacher.objects.filter(tenant=tenant).first()
    print(f'Picked teacher: {teacher.first_name} {teacher.last_name}')

    created_tests = 0
    created_questions = 0
    created_chapters = 0
    created_topics = 0
    created_attempts = 0

    chapter_titles = {
        ('PHYSICS', '9'): ('Motion & Force', 'Newton\'s Laws of Motion'),
        ('PHYSICS', '10'): ('Electricity', 'Ohm\'s Law'),
        ('PHYSICS', '11'): ('Mechanics', 'Kinematics in 1D'),
        ('PHYSICS', '12'): ('Modern Physics', 'Photoelectric Effect'),
        ('CHEMISTRY', '9'): ('Atoms & Molecules', 'Atomic Structure'),
        ('CHEMISTRY', '10'): ('Acids, Bases & Salts', 'Indicators & pH'),
        ('CHEMISTRY', '11'): ('Atomic Structure', 'Quantum Numbers'),
        ('CHEMISTRY', '12'): ('Coordination Compounds', 'Werner\'s Theory'),
    }

    for subj_key, subj in subjects:
        for cls in classes:
            chap_title, topic_title = chapter_titles[(subj_key, cls)]
            chapter, was_new = Chapter.objects.get_or_create(
                tenant=tenant, subject=subj, name=chap_title,
                defaults={'class_level': cls, 'display_order': int(cls)},
            )
            if was_new:
                created_chapters += 1

            topic, was_new = Topic.objects.get_or_create(
                tenant=tenant, chapter=chapter, name=topic_title,
                defaults={'display_order': 1},
            )
            if was_new:
                created_topics += 1

            test_code = f'DEMO-{subj_key[:3]}-{cls}'
            qbank = QUESTION_BANK[(subj_key, cls)]

            # Wipe existing demo test for clean reseed
            Test.objects.filter(tenant=tenant, test_code=test_code).delete()

            now = timezone.now()
            test = Test.objects.create(
                tenant=tenant, test_code=test_code,
                title=f'Class {cls} {subj.name} – {chap_title} (Demo)',
                description=f'Auto-generated demo test for class {cls} {subj.name}.',
                test_type='CHAPTER_TEST', exam_target='BOARDS',
                difficulty_level='MEDIUM',
                subject=subj, chapter=chapter,
                total_duration_minutes=20,
                start_datetime=now - timedelta(hours=1),
                end_datetime=now + timedelta(days=30),
                total_marks=Decimal('20.00'),
                passing_marks=Decimal('8.00'),
                passing_percent=Decimal('40.00'),
                positive_marks_per_question=Decimal('4.00'),
                negative_marks_per_question=Decimal('-1.00'),
                max_attempts=3,
                shuffle_questions=True,
                show_correct_answers=True,
                show_explanations=True,
                access_mode='OPEN',
                result_display_mode='IMMEDIATE',
                status='PUBLISHED',
                published_at=now,
                teacher=teacher,
                total_questions=len(qbank),
            )
            created_tests += 1

            for i, (q_text, oa, ob, oc, od, ans) in enumerate(qbank, start=1):
                Question.objects.create(
                    tenant=tenant, test=test,
                    question_code=f'{test_code}-Q{i}',
                    question_text=q_text,
                    question_type='MCQ_SINGLE',
                    difficulty='MEDIUM',
                    option_a=oa, option_b=ob, option_c=oc, option_d=od,
                    correct_answer=ans,
                    answer_explanation=f'Correct answer is option {ans}.',
                    positive_marks=Decimal('4.00'),
                    negative_marks=Decimal('-1.00'),
                    subject=subj, chapter=chapter, topic=topic,
                    question_order=i,
                )
                created_questions += 1

            # Pick one student in this class to auto-attempt the test
            student = Student.objects.filter(
                tenant=tenant, student_class=cls,
            ).exclude(first_name='').first()
            if not student:
                student = Student.objects.filter(tenant=tenant).first()

            if student:
                start = now - timedelta(minutes=12)
                attempt = TestAttempt.objects.create(
                    tenant=tenant, test=test, student=student,
                    attempt_number=1,
                    started_at=start,
                    submitted_at=now,
                    time_taken_seconds=12 * 60,
                    total_questions=len(qbank),
                    status='EVALUATED',
                )
                # Auto-grade: simulate student getting the first 4 right and 5th wrong
                correct = 0
                attempted = 0
                raw_score = Decimal('0')
                for i, (_, oa, ob, oc, od, ans) in enumerate(qbank, start=1):
                    q = Question.objects.get(test=test, question_order=i)
                    selected = ans if i <= 4 else (
                        'A' if ans != 'A' else 'B'  # wrong on the last one
                    )
                    is_correct = selected == ans
                    marks = Decimal('4.00') if is_correct else Decimal('-1.00')
                    TestAttemptAnswer.objects.create(
                        tenant=tenant, attempt=attempt, question=q,
                        student_answer=selected,
                        status='ANSWERED',
                        is_correct=is_correct,
                        marks_awarded=marks,
                        time_spent_seconds=120,
                    )
                    attempted += 1
                    raw_score += marks
                    if is_correct:
                        correct += 1
                attempt.attempted = attempted
                attempt.correct = correct
                attempt.incorrect = attempted - correct
                attempt.skipped = 0
                attempt.raw_score = raw_score
                attempt.total_marks = Decimal('20.00')
                attempt.percentage = (raw_score / Decimal('20.00')) * 100 if raw_score > 0 else Decimal('0')
                attempt.result = 'PASS' if attempt.percentage >= 40 else 'FAIL'
                attempt.save()
                created_attempts += 1
                print(f'  → {test.test_code}: {student.first_name} scored {raw_score}/20 ({attempt.percentage:.0f}%) → {attempt.result}')

    print()
    print('=' * 60)
    print(f'Subjects:        Physics, Chemistry')
    print(f'Chapters added:  {created_chapters}')
    print(f'Topics added:    {created_topics}')
    print(f'Tests created:   {created_tests}')
    print(f'Questions added: {created_questions}')
    print(f'Attempts seeded: {created_attempts}')
    print('=' * 60)


with transaction.atomic():
    seed()
