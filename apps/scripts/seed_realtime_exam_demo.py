"""Seed a 10-mark Real-Time Exam Demo and schedule it for tomorrow at 12:00 noon.

Idempotent: re-running updates the same Test (matched by test_code).

Usage (inside the api container):
    python manage.py shell < /app/scripts/seed_realtime_exam_demo.py
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from tenants.models import Tenant
from academics.models import Subject
from accounts.models import Teacher
from assessments.models import Test, TestSection, Question

TEST_CODE = 'RT-DEMO-NOON'

tenant = Tenant.objects.first()
assert tenant, 'No tenant in DB; cannot seed'

subject = Subject.objects.filter(tenant=tenant).first()
teacher = Teacher.objects.filter(tenant=tenant).first()

# "Tomorrow at 12:00 noon" — interpret as the next noon slot at least 6h away
# in the project's local TZ. (When run after midnight IST, this still resolves
# to "tomorrow noon" from the user's perspective.)
now = timezone.localtime()
candidate = now.replace(hour=12, minute=0, second=0, microsecond=0)
if candidate <= now + timedelta(hours=6):
    candidate = candidate + timedelta(days=1)
tomorrow_noon = candidate
end_dt = tomorrow_noon + timedelta(minutes=60)

defaults = dict(
    title='Real-Time Exam Demo (Noon Slot)',
    description='Demo exam for real-time scenarios. 10 single-choice questions, 1 mark each.',
    instructions=(
        'Read each question carefully. +1 for a correct answer, 0 for skipped. '
        'Test auto-submits at the end of 60 minutes.'
    ),
    test_type=Test.TestType.MOCK_EXAM,
    exam_target=Test.ExamTarget.GENERAL,
    difficulty_level=Test.DifficultyLevel.MEDIUM,
    subject=subject,
    teacher=teacher,
    total_duration_minutes=60,
    start_datetime=tomorrow_noon,
    end_datetime=end_dt,
    show_timer=True,
    total_marks=Decimal('10.00'),
    passing_marks=Decimal('4.00'),
    passing_percent=Decimal('40.00'),
    positive_marks_per_question=Decimal('1.00'),
    negative_marks_per_question=Decimal('0.00'),
    partial_marking=False,
    max_attempts=1,
    shuffle_questions=True,
    shuffle_options=True,
    allow_review=True,
    allow_backward=True,
    access_mode=Test.AccessMode.SCHEDULED,
    result_display_mode=Test.ResultMode.IMMEDIATE,
    show_correct_answers=True,
    show_explanations=True,
    show_rank=True,
    show_percentile=True,
    enable_proctoring=True,
    prevent_tab_switch=True,
    max_tab_switches=3,
    prevent_copy_paste=True,
    prevent_screenshot=True,
    status=Test.TestStatus.PUBLISHED,
    published_at=now,
    total_questions=10,
)

test, created = Test.objects.update_or_create(
    tenant=tenant, test_code=TEST_CODE, defaults=defaults,
)
print(('CREATED' if created else 'UPDATED'), 'Test', test.test_code, '→', test.start_datetime)

# Section
section, _ = TestSection.objects.update_or_create(
    tenant=tenant, test=test, section_order=1,
    defaults=dict(
        section_name='General Awareness',
        subject=subject,
        total_questions=10,
        mandatory_questions=10,
        max_marks=Decimal('10.00'),
        duration_minutes=60,
        instructions='Single-choice, 1 mark per question.',
    ),
)
print('Section:', section.section_name)

# 10 demo questions (single-choice, 1 mark each, no negative)
QUESTIONS = [
    ('Q1', 'Which planet is known as the Red Planet?',
     'Earth', 'Mars', 'Jupiter', 'Venus', 'B',
     'Mars appears red due to iron oxide (rust) on its surface.'),
    ('Q2', 'Speed of light in vacuum is approximately?',
     '3×10^5 km/s', '3×10^8 m/s', '3×10^6 m/s', '3×10^10 m/s', 'B',
     'c ≈ 299 792 458 m/s ≈ 3×10^8 m/s.'),
    ('Q3', 'The chemical symbol for Gold is?',
     'Gd', 'Go', 'Au', 'Ag', 'C',
     'Au is from the Latin "aurum".'),
    ('Q4', 'Pythagoras theorem applies to which type of triangle?',
     'Equilateral', 'Right-angled', 'Isosceles', 'Scalene', 'B',
     'a²+b²=c² holds only for right-angled triangles.'),
    ('Q5', 'Who wrote "Hamlet"?',
     'Charles Dickens', 'Mark Twain', 'William Shakespeare', 'Jane Austen', 'C',
     'Hamlet (~1600) is by William Shakespeare.'),
    ('Q6', 'What is the largest organ in the human body?',
     'Liver', 'Brain', 'Heart', 'Skin', 'D',
     'Skin is the largest organ by surface area and weight.'),
    ('Q7', 'Which gas do plants absorb during photosynthesis?',
     'Oxygen', 'Nitrogen', 'Carbon dioxide', 'Hydrogen', 'C',
     'Plants take in CO₂ and release O₂.'),
    ('Q8', 'The capital of Australia is?',
     'Sydney', 'Melbourne', 'Canberra', 'Perth', 'C',
     'Canberra is the capital; Sydney is the largest city.'),
    ('Q9', 'Square root of 144 is?',
     '10', '11', '12', '13', 'C',
     '12 × 12 = 144.'),
    ('Q10', 'Which is the smallest prime number?',
     '0', '1', '2', '3', 'C',
     '2 is the smallest (and only even) prime.'),
]

for order, (code, qtext, a, b, c, d, ans, expl) in enumerate(QUESTIONS, start=1):
    Question.objects.update_or_create(
        tenant=tenant, test=test, question_code=f'{TEST_CODE}-{code}',
        defaults=dict(
            section=section,
            question_text=qtext,
            question_type=Question.QuestionType.MCQ_SINGLE,
            difficulty=Question.Difficulty.EASY,
            option_a=a, option_b=b, option_c=c, option_d=d,
            correct_answer=ans,
            answer_explanation=expl,
            positive_marks=Decimal('1.00'),
            negative_marks=Decimal('0.00'),
            subject=subject,
            question_order=order,
            is_active=True,
            is_deleted=False,
        ),
    )

# Refresh denormalised counts
test.total_questions = test.questions.filter(is_deleted=False).count()
test.save(update_fields=['total_questions'])
section.total_questions = test.total_questions
section.save(update_fields=['total_questions'])

print(f'Total questions: {test.total_questions}')
print(f'Scheduled: {test.start_datetime}  →  {test.end_datetime}')
print(f'Status:    {test.status}')
print(f'Test ID:   {test.id}')
