"""Seed a demo JEE-style 3-section test with 3 questions per section."""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')
import django; django.setup()

from django.utils import timezone
from datetime import timedelta
from assessments.models import Test, TestSection, Question
from tenants.models import Tenant

tenant = Tenant.objects.first()
if not tenant:
    print('No tenant — abort'); sys.exit(1)

now = timezone.now()
test, created = Test.objects.update_or_create(
    tenant=tenant, test_code='DEMO-JEE-MOCK-1',
    defaults=dict(
        title='JEE Main Mock #1 (Demo Sectional)',
        description='3-section sectional paper: Physics + Chemistry + Maths.',
        test_type='MOCK_TEST', access_mode='OPEN',
        status='PUBLISHED',
        total_questions=9, total_marks=36,
        total_duration_minutes=180, passing_percent=33,
        start_datetime=now - timedelta(days=1),
        end_datetime=now + timedelta(days=30),
        published_at=now,
    ),
)
print(f"{'CREATED' if created else 'UPDATED'} Test {test.test_code}")

# Wipe old demo questions/sections for clean re-run
test.sections.all().delete()
Question.objects.filter(test=test, question_code__startswith='JEEDEMO-').delete()

sections_def = [
    ('Physics',   1, 60, 12),
    ('Chemistry', 2, 60, 12),
    ('Maths',     3, 60, 12),
]
sec_map = {}
for name, order, mins, marks in sections_def:
    s = TestSection.objects.create(
        tenant=tenant, test=test, section_name=name, section_order=order,
        total_questions=3, mandatory_questions=3,
        max_marks=marks, duration_minutes=mins,
        instructions=f'Answer all 3 {name} questions in {mins} minutes.',
    )
    sec_map[name] = s
    print(f'  + Section: {name} ({mins}min, {marks} marks)')

bank = {
    'Physics': [
        ('A ball falls freely. Acceleration is approximately?',
         '5 m/s²', '9.8 m/s²', '15 m/s²', '20 m/s²', 'B'),
        ('SI unit of electric current is?',
         'Volt', 'Ohm', 'Ampere', 'Watt', 'C'),
        ('Speed of light in vacuum (m/s)?',
         '3×10⁵', '3×10⁶', '3×10⁷', '3×10⁸', 'D'),
    ],
    'Chemistry': [
        ('Atomic number of Carbon?',
         '4', '6', '8', '12', 'B'),
        ('Which gas is released during photosynthesis?',
         'CO₂', 'N₂', 'O₂', 'H₂', 'C'),
        ('pH of pure water at 25 °C?',
         '5', '6', '7', '8', 'C'),
    ],
    'Maths': [
        ('Derivative of sin(x)?',
         '−sin(x)', 'cos(x)', '−cos(x)', 'tan(x)', 'B'),
        ('∫ 1/x dx =?',
         'x', 'ln|x| + C', 'eˣ', '1/x²', 'B'),
        ('Sum of angles in a triangle?',
         '90°', '120°', '180°', '360°', 'C'),
    ],
}
order = 1
for sec_name, items in bank.items():
    for i, (q, a, b, c, d, ans) in enumerate(items, start=1):
        Question.objects.create(
            tenant=tenant, test=test, section=sec_map[sec_name],
            subject=None,
            question_code=f'JEEDEMO-{sec_name[:3].upper()}-Q{i}',
            question_text=q, question_type='MCQ_SINGLE',
            difficulty='MEDIUM',
            option_a=a, option_b=b, option_c=c, option_d=d,
            correct_answer=ans, positive_marks=4, negative_marks=-1,
            question_order=order,
        )
        order += 1
print(f'  + {order-1} questions seeded')
print('\nDONE — open /admin/assessments/test/ → "JEE Main Mock #1" → scroll to "Test sections" inline.')
