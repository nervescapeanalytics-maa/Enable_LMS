"""
Seed a real-world JEE Main mock test:
  - 1 Test ("JEE Main Mock #1 (Demo Sectional)")
  - 3 TestSections: Mathematics, Physics, Chemistry
  - 5 questions per section (15 total) — single-choice MCQ, answer marked.

Idempotent on (tenant, test_code='DEMO-JEE-MOCK-1'): re-running upserts
the test, replaces questions, and recreates sections.

Usage (inside docker-api-1):
    python manage.py seed_jee_mock
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone


JEE_MOCK_DATA = {
    'Mathematics': [
        {
            'q': r'If \(\sin\theta + \cos\theta = \tfrac{1}{2}\), then \(\sin 2\theta\) is equal to:',
            'A': '−3/4', 'B': '3/4', 'C': '1/4', 'D': '−1/4',
            'correct': 'A',
            'expl': '(sinθ+cosθ)² = 1 + sin2θ ⇒ 1/4 = 1 + sin2θ ⇒ sin2θ = −3/4.',
        },
        {
            'q': r'The number of solutions of \(\log_4(x-1) = \log_2(x-3)\) is:',
            'A': '0', 'B': '1', 'C': '2', 'D': '3',
            'correct': 'B',
            'expl': 'Squaring (x−3)² = x−1 ⇒ x²−7x+10=0 ⇒ x=2,5. Only x=5 satisfies domain.',
        },
        {
            'q': r'The value of \(\displaystyle\int_0^{\pi/2}\frac{\sin x}{\sin x + \cos x}\,dx\) is:',
            'A': 'π/4', 'B': 'π/2', 'C': 'π', 'D': '0',
            'correct': 'A',
            'expl': 'Use king-rule property; integral equals π/4.',
        },
        {
            'q': r'If the lines 3x+4y=12 and ax+by=c are perpendicular, then a/b equals:',
            'A': '4/3', 'B': '−3/4', 'C': '3/4', 'D': '−4/3',
            'correct': 'A',
            'expl': 'Slope of given line = −3/4. Perpendicular slope = 4/3 = −a/b ⇒ a/b = 4/3 (with sign convention given).',
        },
        {
            'q': r'The coefficient of \(x^4\) in the expansion of \((1+x+x^2)^{10}\) is:',
            'A': '210', 'B': '615', 'C': '930', 'D': '1110',
            'correct': 'C',
            'expl': 'Use multinomial theorem; sum of products giving x⁴ = 615+255+60 = 930.',
        },
    ],
    'Physics': [
        {
            'q': 'A body of mass 2 kg moving with 10 m/s collides elastically head-on with a body of mass 3 kg at rest. Velocity of 2 kg body after collision is:',
            'A': '−2 m/s', 'B': '2 m/s', 'C': '4 m/s', 'D': '−4 m/s',
            'correct': 'A',
            'expl': 'v1 = (m1−m2)/(m1+m2)·u1 = (2−3)/5·10 = −2 m/s.',
        },
        {
            'q': 'A wire of resistance R is stretched to double its length. New resistance becomes:',
            'A': 'R', 'B': '2R', 'C': '4R', 'D': 'R/2',
            'correct': 'C',
            'expl': 'R ∝ L²/V (constant volume) ⇒ doubling L → resistance ×4.',
        },
        {
            'q': 'A simple pendulum has time period T on Earth. On a planet where g is one-fourth of Earth, time period becomes:',
            'A': 'T/2', 'B': 'T', 'C': '2T', 'D': '4T',
            'correct': 'C',
            'expl': 'T ∝ 1/√g; g→g/4 ⇒ T → 2T.',
        },
        {
            'q': 'The de Broglie wavelength of an electron accelerated through 150 V is approximately:',
            'A': '0.1 Å', 'B': '1 Å', 'C': '10 Å', 'D': '100 Å',
            'correct': 'B',
            'expl': 'λ = 12.27/√V Å = 12.27/√150 ≈ 1 Å.',
        },
        {
            'q': 'In Young’s double-slit experiment, the fringe width β depends on slit separation d as:',
            'A': 'β ∝ d', 'B': 'β ∝ 1/d', 'C': 'β ∝ d²', 'D': 'β independent of d',
            'correct': 'B',
            'expl': 'β = λD/d ⇒ inversely proportional to d.',
        },
    ],
    'Chemistry': [
        {
            'q': 'Which of the following has the highest boiling point?',
            'A': 'HF', 'B': 'HCl', 'C': 'HBr', 'D': 'HI',
            'correct': 'A',
            'expl': 'HF has strong intermolecular hydrogen bonding → highest BP among hydrogen halides.',
        },
        {
            'q': 'The IUPAC name of (CH3)2CHCH(OH)CH3 is:',
            'A': '3-methylbutan-2-ol', 'B': '2-methylbutan-3-ol',
            'C': '4-methylpentan-2-ol', 'D': '2-methylpentan-3-ol',
            'correct': 'A',
            'expl': 'Lowest locants assign OH at C-2 of a 3-methylbutan chain.',
        },
        {
            'q': 'Which species is iso-electronic with CO?',
            'A': 'NO+', 'B': 'O2', 'C': 'CN', 'D': 'NO',
            'correct': 'A',
            'expl': 'CO has 14 electrons; NO+ also has 14 electrons.',
        },
        {
            'q': 'Number of σ and π bonds in benzene (C6H6) respectively are:',
            'A': '12 σ, 3 π', 'B': '6 σ, 3 π', 'C': '12 σ, 6 π', 'D': '6 σ, 6 π',
            'correct': 'A',
            'expl': '6 C-H σ + 6 C-C σ = 12 σ; three delocalised π bonds.',
        },
        {
            'q': 'For a first-order reaction, the half-life depends on:',
            'A': 'initial concentration', 'B': 'rate constant only',
            'C': 'temperature only', 'D': 'both concentration and rate constant',
            'correct': 'B',
            'expl': 't½ = 0.693/k for first-order — independent of concentration.',
        },
    ],
}


class Command(BaseCommand):
    help = 'Seed JEE Main mock test (Math/Physics/Chemistry × 5 Qs each).'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=str, default=None,
                            help='Tenant ID or code (default: first tenant).')
        parser.add_argument('--test-code', type=str, default='DEMO-JEE-MOCK-1')
        parser.add_argument('--title', type=str,
                            default='JEE Main Mock #1 (Demo Sectional)')

    def handle(self, *args, **opts):
        from tenants.models import Tenant
        from assessments.models import Test, TestSection, Question

        tenant_arg = opts['tenant']
        if tenant_arg:
            tenant = Tenant.objects.filter(id=tenant_arg).first() or \
                     Tenant.objects.filter(code=tenant_arg).first()
        else:
            tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write('No tenant found.')
            return

        # Postgres RLS context
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.current_tenant_id', %s, false)",
                            [str(tenant.id)])
        except Exception:
            pass

        test_code = opts['test_code']
        title = opts['title']
        now = timezone.now()

        with transaction.atomic():
            test, created = Test.objects.update_or_create(
                tenant=tenant, test_code=test_code,
                defaults={
                    'title': title,
                    'description': 'Sectional mock — Mathematics, Physics, Chemistry. 5 Qs each.',
                    'instructions': ('Answer all 15 questions. +4 for correct, −1 for wrong, '
                                     '0 for unattempted. Negative marking applies.'),
                    'test_type': 'MOCK_EXAM',
                    'exam_target': 'JEE_MAINS',
                    'difficulty_level': 'MIXED',
                    'total_duration_minutes': 180,
                    'start_datetime': now - timedelta(hours=1),
                    'end_datetime': now + timedelta(days=30),
                    'total_marks': Decimal('60.00'),
                    'passing_marks': Decimal('20.00'),
                    'passing_percent': Decimal('33.00'),
                    'positive_marks_per_question': Decimal('4.00'),
                    'negative_marks_per_question': Decimal('-1.00'),
                    'max_attempts': 3,
                    'shuffle_questions': False,
                    'allow_review': True,
                    'allow_backward': True,
                    'access_mode': 'OPEN',
                    'result_display_mode': 'IMMEDIATE',
                    'show_correct_answers': True,
                    'show_explanations': True,
                    'show_rank': True,
                    'show_percentile': True,
                    'status': 'PUBLISHED',
                    'published_at': now,
                    'total_questions': 15,
                    'test_meta': {
                        'category': 'mock_test',
                        'exam': 'JEE_MAIN',
                        'pattern': 'sectional',
                        'subjects': ['Mathematics', 'Physics', 'Chemistry'],
                    },
                },
            )

            # Wipe prior sections + questions for a clean re-seed
            Question.objects.filter(test=test).delete()
            TestSection.objects.filter(test=test).delete()

            order = 1
            for sec_idx, (section_name, qs) in enumerate(JEE_MOCK_DATA.items(), start=1):
                section = TestSection.objects.create(
                    tenant=tenant, test=test,
                    section_name=section_name,
                    section_order=sec_idx,
                    total_questions=len(qs),
                    max_marks=Decimal(len(qs) * 4),
                    duration_minutes=60,
                    instructions=f'Answer all {len(qs)} questions from {section_name}.',
                )

                for i, item in enumerate(qs, start=1):
                    Question.objects.create(
                        tenant=tenant,
                        test=test,
                        section=section,
                        question_code=f'{test_code}-{section_name[:3].upper()}-{i:02d}',
                        question_text=item['q'],
                        question_type='MCQ_SINGLE',
                        difficulty='MEDIUM',
                        option_a=item['A'],
                        option_b=item['B'],
                        option_c=item['C'],
                        option_d=item['D'],
                        correct_answer=item['correct'],
                        answer_explanation=item['expl'],
                        positive_marks=Decimal('4.00'),
                        negative_marks=Decimal('-1.00'),
                        question_order=order,
                        is_active=True,
                    )
                    order += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded JEE mock test "{test.title}" (code={test.test_code}, id={test.id}) — '
            f'{order-1} questions across {len(JEE_MOCK_DATA)} sections. '
            f'{"Created" if created else "Updated"}.'
        ))
