#!/usr/bin/env python
"""
Populate Assessments & Exams with realistic data for Classes 9, 10, 11, 12.

Creates:
  - Academic Session (2025-2026)
  - Groups (Science, Foundation)
  - Subjects (Physics, Chemistry, Mathematics, Biology, English)
  - Chapters & Topics per subject per class level
  - Batches for Class 9, 10, 11, 12
  - Teachers (20) assigned to batches
  - Students (70+) distributed across batches
  - Tests/Exams: scheduled, live NOW, completed, upcoming
  - Real Indian-curriculum MCQ questions per test
  - Enrollments (BatchStudent records)
"""
import os, sys, uuid, random
from datetime import datetime, timedelta, date, time
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.utils import timezone
from django.contrib.auth.hashers import make_password
from tenants.models import Tenant
from academics.models import AcademicSession, Group, Subject, Chapter, Topic, Batch, Users as BatchStudent, BatchTeacher
from accounts.models import Student, Teacher
from assessments.models import Test, TestSection, Question, TestAttempt, TestAttemptAnswer

from django.db import connection

now = timezone.now()
TENANT_ID = 'f883ed57-6f3a-40fa-b7f8-f0eebcd7e04c'

# Set RLS tenant context
with connection.cursor() as cur:
    cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", [TENANT_ID])

tenant = Tenant.objects.get(id=TENANT_ID)

# Password hashes
TEACHER_PWD = make_password('teacher123')
STUDENT_PWD = make_password('student123')

print("=" * 70)
print("  ENABLE-LMS: Populating Assessments & Exams — Realistic Data")
print("=" * 70)
print(f"  Tenant : {tenant.name}")
print(f"  Time   : {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print("=" * 70)

# ============================================================
# 0. CLEANUP — Remove assessment data only (FK-safe)
# ============================================================
print("\n[0/10] Cleaning up stale assessment data...")
from assessments.models import TestFeedback
del_answers = TestAttemptAnswer.objects.filter(tenant=tenant).delete()[0]
del_attempts2 = TestAttempt.objects.filter(tenant=tenant).delete()[0]
del_fb = TestFeedback.objects.filter(tenant=tenant).delete()[0]
del_q = Question.objects.filter(tenant=tenant).delete()[0]
del_t = Test.objects.filter(tenant=tenant).delete()[0]
print(f"  ✓ Cleaned: {del_t} tests, {del_q} questions, {del_attempts2} attempts, {del_answers} answers")

# ============================================================
# 1. ACADEMIC SESSION
# ============================================================
print("\n[1/10] Academic Session...")
session, _ = AcademicSession.objects.update_or_create(
    tenant=tenant, session_name='2025-2026',
    defaults={
        'start_date': date(2025, 4, 1),
        'end_date': date(2026, 3, 31),
        'is_current': True,
        'status': True,
    }
)
print(f"  ✓ Session: {session.session_name} (id={session.id})")

# ============================================================
# 2. GROUPS
# ============================================================
print("\n[2/10] Groups...")
groups = {}
for gname in ['Science Stream', 'Foundation']:
    g, _ = Group.objects.update_or_create(
        tenant=tenant, name=gname,
        defaults={'description': f'{gname} academic group', 'status': True}
    )
    groups[gname] = g
    print(f"  ✓ {gname}")

# ============================================================
# 3. SUBJECTS
# ============================================================
print("\n[3/10] Subjects...")
SUBJECTS_DATA = [
    ('Physics', 'PHY', 'PHYSICS', '#3B82F6'),
    ('Chemistry', 'CHE', 'CHEMISTRY', '#EF4444'),
    ('Mathematics', 'MAT', 'MATHEMATICS', '#10B981'),
    ('Biology', 'BIO', 'BIOLOGY', '#8B5CF6'),
    ('English', 'ENG', 'OTHER', '#F59E0B'),
]

# Code mapping: DB may use CHM/MTH while script uses CHE/MAT
DB_CODE_MAP = {'PHY': 'PHY', 'CHE': 'CHM', 'MAT': 'MTH', 'BIO': 'BIO', 'ENG': 'ENG'}

subjects = {}
for sname, code, stype, color in SUBJECTS_DATA:
    db_code = DB_CODE_MAP.get(code, code)
    # Use existing subject (first one) or create
    existing = Subject.objects.filter(tenant=tenant, code=db_code)
    if existing.exists():
        s = existing.first()
        print(f"  ✓ {sname} ({db_code}) — using existing (id={s.id})")
    else:
        s = Subject.objects.create(
            tenant=tenant, code=db_code, name=sname,
            subject_type=stype, color=color, status='Active'
        )
        print(f"  + {sname} ({db_code}) — created")
    subjects[code] = s

# ============================================================
# 4. CHAPTERS & TOPICS — Real Indian Curriculum (CBSE/NCERT)
# ============================================================
print("\n[4/10] Chapters & Topics...")
CURRICULUM = {
    '9': {
        'PHY': [
            ('Motion', ['Distance and Displacement', 'Speed and Velocity', 'Acceleration', 'Equations of Motion', 'Graphical Representation']),
            ('Force and Laws of Motion', ['Balanced and Unbalanced Forces', "Newton's First Law", "Newton's Second Law", "Newton's Third Law", 'Conservation of Momentum']),
            ('Gravitation', ['Universal Law of Gravitation', 'Free Fall', 'Mass and Weight', 'Thrust and Pressure', 'Archimedes Principle']),
            ('Work and Energy', ['Work Done by a Force', 'Kinetic Energy', 'Potential Energy', 'Law of Conservation of Energy', 'Power']),
            ('Sound', ['Production of Sound', 'Propagation of Sound', 'Reflection of Sound', 'Echo', 'Ultrasound']),
        ],
        'CHE': [
            ('Matter in Our Surroundings', ['Physical Nature of Matter', 'States of Matter', 'Change of State', 'Evaporation', 'Effect of Temperature']),
            ('Is Matter Around Us Pure', ['Mixtures', 'Solutions', 'Suspensions', 'Colloids', 'Separation Techniques']),
            ('Atoms and Molecules', ['Laws of Chemical Combination', 'Dalton\'s Atomic Theory', 'Atoms and Molecules', 'Ions', 'Mole Concept']),
            ('Structure of the Atom', ['Charged Particles in Matter', 'Thomson Model', 'Rutherford Model', 'Bohr Model', 'Neutrons']),
        ],
        'MAT': [
            ('Number Systems', ['Natural Numbers', 'Irrational Numbers', 'Real Numbers', 'Representing on Number Line', 'Laws of Exponents']),
            ('Polynomials', ['Polynomials in One Variable', 'Zeroes of a Polynomial', 'Remainder Theorem', 'Factor Theorem', 'Algebraic Identities']),
            ('Coordinate Geometry', ['Cartesian System', 'Plotting Points', 'Coordinates of a Point', 'Quadrant System']),
            ('Linear Equations in Two Variables', ['Linear Equations', 'Solution of Linear Equation', 'Graph of Linear Equation']),
            ('Triangles', ['Congruence of Triangles', 'Properties of Triangles', 'Inequalities in a Triangle']),
        ],
        'BIO': [
            ('The Fundamental Unit of Life', ['Cell Theory', 'Structural Organisation of Cell', 'Plasma Membrane', 'Nucleus', 'Cytoplasm']),
            ('Tissues', ['Plant Tissues', 'Animal Tissues', 'Meristematic Tissue', 'Permanent Tissue']),
            ('Improvement in Food Resources', ['Crop Variety Improvement', 'Crop Production Management', 'Animal Husbandry']),
        ],
        'ENG': [
            ('Grammar — Tenses', ['Present Tenses', 'Past Tenses', 'Future Tenses', 'Perfect Tenses']),
            ('Reading Comprehension', ['Unseen Passages', 'Note Making', 'Summarizing']),
        ],
    },
    '10': {
        'PHY': [
            ('Light — Reflection and Refraction', ['Reflection by Spherical Mirrors', 'Mirror Formula', 'Refraction of Light', 'Lens Formula', 'Power of a Lens']),
            ('Human Eye and Colourful World', ['Human Eye', 'Defects of Vision', 'Atmospheric Refraction', 'Scattering of Light', 'Tyndall Effect']),
            ('Electricity', ['Electric Current', "Ohm's Law", 'Resistance', 'Series and Parallel Circuits', 'Heating Effect of Current']),
            ('Magnetic Effects of Electric Current', ['Magnetic Field', 'Force on Current-Carrying Conductor', 'Electromagnetic Induction', 'Electric Motor', 'Electric Generator']),
        ],
        'CHE': [
            ('Chemical Reactions and Equations', ['Chemical Equations', 'Types of Chemical Reactions', 'Corrosion', 'Rancidity']),
            ('Acids, Bases and Salts', ['Properties of Acids and Bases', 'pH Scale', 'Salts', 'Bleaching Powder', 'Baking Soda']),
            ('Metals and Non-metals', ['Physical Properties', 'Chemical Properties', 'Reactivity Series', 'Extraction of Metals', 'Corrosion']),
            ('Carbon and its Compounds', ['Covalent Bonding', 'Versatile Nature of Carbon', 'Homologous Series', 'Nomenclature', 'Chemical Properties']),
        ],
        'MAT': [
            ('Real Numbers', ['Euclid\'s Division Lemma', 'Fundamental Theorem of Arithmetic', 'Irrational Numbers', 'Rational Numbers']),
            ('Polynomials', ['Geometrical Meaning of Zeroes', 'Relationship Between Zeroes and Coefficients', 'Division Algorithm']),
            ('Pair of Linear Equations', ['Graphical Method', 'Algebraic Methods', 'Substitution Method', 'Elimination Method', 'Cross-Multiplication']),
            ('Quadratic Equations', ['Standard Form', 'Factorisation Method', 'Completing the Square', 'Quadratic Formula', 'Nature of Roots']),
            ('Arithmetic Progressions', ['nth Term of AP', 'Sum of n Terms', 'Applications of AP']),
        ],
        'BIO': [
            ('Life Processes', ['Nutrition', 'Respiration', 'Transportation', 'Excretion', 'Photosynthesis']),
            ('Control and Coordination', ['Nervous System', 'Reflex Actions', 'Hormones in Animals', 'Hormones in Plants']),
            ('Heredity and Evolution', ['Mendel\'s Laws', 'Sex Determination', 'Evolution', 'Speciation']),
        ],
        'ENG': [
            ('Letter Writing', ['Formal Letters', 'Informal Letters', 'Complaint Letters']),
            ('Essay Writing', ['Descriptive Essays', 'Argumentative Essays', 'Narrative Essays']),
        ],
    },
    '11': {
        'PHY': [
            ('Units and Measurements', ['SI Units', 'Dimensional Analysis', 'Errors in Measurement', 'Significant Figures']),
            ('Motion in a Straight Line', ['Position and Displacement', 'Average Velocity', 'Instantaneous Velocity', 'Kinematic Equations', 'Relative Velocity']),
            ('Motion in a Plane', ['Vectors', 'Vector Addition', 'Projectile Motion', 'Uniform Circular Motion', 'Centripetal Acceleration']),
            ('Laws of Motion', ['Newton\'s Laws', 'Momentum', 'Impulse', 'Friction', 'Circular Motion Dynamics']),
            ('Work, Energy and Power', ['Work-Energy Theorem', 'Kinetic Energy', 'Potential Energy', 'Conservation of Energy', 'Collisions']),
            ('Rotational Motion', ['Angular Velocity', 'Torque', 'Moment of Inertia', 'Angular Momentum', 'Rolling Motion']),
        ],
        'CHE': [
            ('Some Basic Concepts of Chemistry', ['Mole Concept', 'Stoichiometry', 'Atomic Mass', 'Molecular Mass', 'Percentage Composition']),
            ('Structure of Atom', ['Bohr\'s Model', 'Quantum Mechanical Model', 'Quantum Numbers', 'Electron Configuration', 'Shapes of Orbitals']),
            ('Chemical Bonding', ['Ionic Bond', 'Covalent Bond', 'VSEPR Theory', 'Hybridization', 'Molecular Orbital Theory']),
            ('States of Matter', ['Ideal Gas Law', 'Kinetic Theory', 'Real Gases', 'Liquefaction', 'Vapour Pressure']),
            ('Thermodynamics', ['First Law', 'Enthalpy', 'Hess\'s Law', 'Entropy', 'Gibbs Free Energy']),
        ],
        'MAT': [
            ('Sets', ['Types of Sets', 'Venn Diagrams', 'Operations on Sets', 'De Morgan\'s Laws']),
            ('Relations and Functions', ['Cartesian Product', 'Relations', 'Functions', 'Domain and Range']),
            ('Trigonometric Functions', ['Trigonometric Ratios', 'Trigonometric Identities', 'Graphs', 'General Solutions']),
            ('Complex Numbers', ['Algebra of Complex Numbers', 'Modulus and Argument', 'Polar Form', 'Square Roots']),
            ('Sequences and Series', ['Arithmetic Progression', 'Geometric Progression', 'Sum to n Terms', 'Infinite GP']),
            ('Permutations and Combinations', ['Fundamental Counting Principle', 'Permutations', 'Combinations', 'Applications']),
        ],
        'BIO': [
            ('The Living World', ['Diversity in Living World', 'Taxonomic Categories', 'Biological Classification']),
            ('Cell: The Unit of Life', ['Cell Theory', 'Prokaryotic Cell', 'Eukaryotic Cell', 'Cell Organelles']),
            ('Cell Cycle and Cell Division', ['Cell Cycle', 'Mitosis', 'Meiosis', 'Significance of Meiosis']),
            ('Photosynthesis', ['Light Reaction', 'Dark Reaction', 'C3 and C4 Pathways', 'Photorespiration']),
        ],
        'ENG': [
            ('Creative Writing', ['Narrative Writing', 'Descriptive Writing', 'Speech Writing', 'Debate Writing']),
            ('Advanced Grammar', ['Reported Speech', 'Active-Passive Voice', 'Conditionals', 'Modals']),
        ],
    },
    '12': {
        'PHY': [
            ('Electric Charges and Fields', ['Coulomb\'s Law', 'Electric Field', 'Electric Dipole', 'Gauss\'s Law', 'Field Due to Charge Distributions']),
            ('Electrostatic Potential', ['Electric Potential', 'Equipotential Surfaces', 'Potential Energy', 'Capacitors', 'Dielectrics']),
            ('Current Electricity', ['Ohm\'s Law', 'Resistivity', 'Kirchhoff\'s Laws', 'Wheatstone Bridge', 'Meter Bridge']),
            ('Electromagnetic Induction', ['Faraday\'s Law', 'Lenz\'s Law', 'Motional EMF', 'Inductance', 'AC Circuits']),
            ('Optics', ['Ray Optics', 'Wave Optics', 'Interference', 'Diffraction', 'Polarisation']),
            ('Atoms and Nuclei', ['Atomic Models', 'Hydrogen Spectrum', 'Radioactivity', 'Nuclear Fission', 'Nuclear Fusion']),
        ],
        'CHE': [
            ('Solid State', ['Types of Solids', 'Crystal Lattice', 'Unit Cell', 'Packing Efficiency', 'Defects in Solids']),
            ('Solutions', ['Types of Solutions', 'Concentration Terms', 'Raoult\'s Law', 'Colligative Properties', 'Abnormal Molar Mass']),
            ('Electrochemistry', ['Electrolytic Cells', 'Galvanic Cells', 'Nernst Equation', 'Conductance', 'Kohlrausch\'s Law']),
            ('Chemical Kinetics', ['Rate of Reaction', 'Order of Reaction', 'Rate Law', 'Arrhenius Equation', 'Collision Theory']),
            ('d and f Block Elements', ['Transition Elements', 'Properties', 'Lanthanoids', 'Actinoids', 'Compounds']),
        ],
        'MAT': [
            ('Relations and Functions', ['Types of Relations', 'Types of Functions', 'Composition of Functions', 'Inverse Functions']),
            ('Inverse Trigonometric Functions', ['Principal Values', 'Properties', 'Graphs', 'Simple Problems']),
            ('Matrices', ['Types of Matrices', 'Matrix Operations', 'Transpose', 'Symmetric Matrices']),
            ('Determinants', ['Properties of Determinants', 'Area of Triangle', 'Adjoint and Inverse', 'Solving Linear Equations']),
            ('Continuity and Differentiability', ['Continuity', 'Differentiability', 'Chain Rule', 'Implicit Differentiation', 'Logarithmic Differentiation']),
            ('Integrals', ['Indefinite Integrals', 'Integration Methods', 'Definite Integrals', 'Properties of Definite Integrals']),
        ],
        'BIO': [
            ('Reproduction in Organisms', ['Asexual Reproduction', 'Sexual Reproduction', 'Post-fertilisation Events']),
            ('Human Reproduction', ['Male Reproductive System', 'Female Reproductive System', 'Gametogenesis', 'Fertilisation', 'Pregnancy']),
            ('Genetics and Evolution', ['Mendelian Genetics', 'Chromosomal Theory', 'DNA Structure', 'Gene Expression', 'Human Genome']),
            ('Biotechnology', ['Recombinant DNA Technology', 'PCR', 'Gene Cloning', 'Applications in Medicine', 'Transgenic Organisms']),
        ],
        'ENG': [
            ('Report Writing', ['Newspaper Reports', 'Event Reports', 'Investigation Reports']),
            ('Literature Analysis', ['Poetry Analysis', 'Prose Analysis', 'Drama Analysis']),
        ],
    },
}

chapters_map = {}  # (class_level, subject_code, chapter_name) -> chapter obj
topics_map = {}
ch_order = 0
for cls_level, subj_data in CURRICULUM.items():
    for subj_code, chapters in subj_data.items():
        db_code = DB_CODE_MAP.get(subj_code, subj_code)
        for ch_name, topic_names in chapters:
            ch_order += 1
            # Handle potential duplicates from prior runs
            existing_ch = Chapter.objects.filter(
                tenant=tenant, subject=subjects[subj_code], name=ch_name, class_level=cls_level
            )
            if existing_ch.exists():
                ch = existing_ch.first()
                # Clean duplicates
                dupes = existing_ch.exclude(id=ch.id)
                if dupes.exists():
                    # Move topics from dupes to the kept chapter, then delete dupes
                    for dupe in dupes:
                        Topic.objects.filter(chapter=dupe).update(chapter=ch)
                    dupes.delete()
            else:
                ch = Chapter.objects.create(
                    tenant=tenant, subject=subjects[subj_code], name=ch_name, class_level=cls_level,
                    code=f'{db_code}-{cls_level}-{ch_order:03d}',
                    session=session, display_order=ch_order, status=True,
                )
            chapters_map[(cls_level, subj_code, ch_name)] = ch
            for t_order, t_name in enumerate(topic_names, 1):
                existing_tp = Topic.objects.filter(tenant=tenant, chapter=ch, name=t_name)
                if existing_tp.exists():
                    tp = existing_tp.first()
                    existing_tp.exclude(id=tp.id).delete()
                else:
                    tp = Topic.objects.create(
                        tenant=tenant, chapter=ch, name=t_name,
                        display_order=t_order, status=True,
                    )
                topics_map[(cls_level, subj_code, ch_name, t_name)] = tp

total_ch = Chapter.objects.filter(tenant=tenant).count()
total_tp = Topic.objects.filter(tenant=tenant).count()
print(f"  ✓ {total_ch} chapters, {total_tp} topics created")

# ============================================================
# 5. BATCHES — Class 9, 10, 11 (A/B), 12 (A/B)
# ============================================================
print("\n[5/10] Batches...")
BATCHES_DATA = [
    ('CLS9-A', 'Class 9 — Section A', '9', 'BOTH', 'Foundation'),
    ('CLS9-B', 'Class 9 — Section B', '9', 'BOTH', 'Foundation'),
    ('CLS10-A', 'Class 10 — Section A', '10', 'BOTH', 'Foundation'),
    ('CLS10-B', 'Class 10 — Section B', '10', 'BOTH', 'Foundation'),
    ('CLS11-JEE', 'Class 11 — JEE Batch', '11', 'JEE', 'Science Stream'),
    ('CLS11-NEET', 'Class 11 — NEET Batch', '11', 'NEET', 'Science Stream'),
    ('CLS12-JEE', 'Class 12 — JEE Batch', '12', 'JEE', 'Science Stream'),
    ('CLS12-NEET', 'Class 12 — NEET Batch', '12', 'NEET', 'Science Stream'),
]
batches = {}
for code, name, cls, target, grp_name in BATCHES_DATA:
    b, _ = Batch.objects.update_or_create(
        tenant=tenant, code=code,
        defaults={
            'name': name, 'class_level': cls, 'exam_target': target,
            'session': session, 'group': groups.get(grp_name, groups['Science Stream']),
            'max_students': 60, 'start_date': date(2025, 4, 1), 'end_date': date(2026, 3, 31),
            'status': 'ACTIVE',
        }
    )
    batches[code] = b
    print(f"  ✓ {name}")

# ============================================================
# 6. TEACHERS (20)
# ============================================================
print("\n[6/10] Teachers...")
TEACHERS_DATA = [
    ('TCH001', 'Dr. Kavita', 'Reddy', 'kavita.reddy@lms.com', '919876500001', 'PHY', 'Ph.D. Physics, IIT Delhi'),
    ('TCH002', 'Mr. Manoj', 'Tiwari', 'manoj.tiwari@lms.com', '919876500002', 'CHE', 'M.Sc. Chemistry, BHU'),
    ('TCH003', 'Ms. Pallavi', 'Saxena', 'pallavi.saxena@lms.com', '919876500003', 'MAT', 'M.Sc. Mathematics, DU'),
    ('TCH004', 'Dr. Ramesh', 'Yadav', 'ramesh.yadav@lms.com', '919876500004', 'BIO', 'Ph.D. Botany, JNU'),
    ('TCH005', 'Mrs. Lakshmi', 'Iyer', 'lakshmi.iyer@lms.com', '919876500005', 'ENG', 'M.A. English, Presidency'),
    ('TCH006', 'Dr. Suresh', 'Kumar', 'dr.suresh.kumar@lms.com', '919876500006', 'PHY', 'M.Tech. Applied Physics'),
    ('TCH007', 'Mr. Rajesh', 'Tripathi', 'rajesh.tripathi@lms.com', '919876500007', 'MAT', 'M.Sc. Mathematics, AMU'),
    ('TCH008', 'Dr. Meena', 'Agarwal', 'meena.agarwal@lms.com', '919876500008', 'BIO', 'Ph.D. Zoology'),
    ('TCH009', 'Mr. Anil', 'Pandey', 'anil.pandey@lms.com', '919876500009', 'PHY', 'M.Sc. Physics, IIT Kanpur'),
    ('TCH010', 'Mrs. Geeta', 'Mishra', 'geeta.mishra@lms.com', '919876500010', 'CHE', 'M.Sc. Organic Chemistry'),
    ('TCH011', 'Dr. Prakash', 'Jha', 'prakash.jha@lms.com', '919876500011', 'MAT', 'Ph.D. Applied Mathematics'),
    ('TCH012', 'Ms. Deepa', 'Nair', 'deepa.nair@lms.com', '919876500012', 'BIO', 'M.Sc. Microbiology'),
    ('TCH013', 'Mr. Vivek', 'Shukla', 'vivek.shukla@lms.com', '919876500013', 'PHY', 'M.Sc. Nuclear Physics'),
    ('TCH014', 'Mrs. Shalini', 'Dubey', 'shalini.dubey@lms.com', '919876500014', 'CHE', 'M.Sc. Inorganic Chemistry'),
    ('TCH015', 'Mr. Santosh', 'Pillai', 'santosh.pillai2@lms.com', '919876500015', 'MAT', 'M.Sc. Statistics'),
    ('TCH016', 'Dr. Anjali', 'Sharma', 'anjali.sharma@lms.com', '919876500016', 'ENG', 'Ph.D. English Literature'),
    ('TCH017', 'Mr. Ravi', 'Shankar', 'ravi.shankar@lms.com', '919876500017', 'PHY', 'M.Tech. Optics'),
    ('TCH018', 'Dr. Priya', 'Singh', 'priya.singh@lms.com', '919876500018', 'CHE', 'Ph.D. Physical Chemistry'),
    ('TCH019', 'Mr. Amit', 'Verma', 'amit.verma@lms.com', '919876500019', 'MAT', 'M.Sc. Pure Mathematics'),
    ('TCH020', 'Mrs. Sunita', 'Mathur', 'sunita.mathur@lms.com', '919876500020', 'BIO', 'M.Sc. Genetics'),
]
teachers_obj = {}
for tcode, fname, lname, email, phone, subj_code, qual in TEACHERS_DATA:
    t, created = Teacher.objects.update_or_create(
        tenant=tenant, teacher_code=tcode,
        defaults={
            'first_name': fname, 'last_name': lname,
            'email': email, 'phone': phone,
            'password_hash': TEACHER_PWD,
            'qualification': qual,
            'subjects': [subj_code],
            'status': 'ACTIVE',
        }
    )
    teachers_obj[tcode] = t
    if created:
        print(f"  + {fname} {lname} ({email})")
    else:
        print(f"  ✓ {fname} {lname} ({email})")

# Assign teachers to batches
BATCH_TEACHER_MAP = {
    'CLS9-A': [('TCH006', 'PHY'), ('TCH010', 'CHE'), ('TCH007', 'MAT'), ('TCH012', 'BIO'), ('TCH005', 'ENG')],
    'CLS9-B': [('TCH009', 'PHY'), ('TCH014', 'CHE'), ('TCH011', 'MAT'), ('TCH008', 'BIO'), ('TCH016', 'ENG')],
    'CLS10-A': [('TCH001', 'PHY'), ('TCH002', 'CHE'), ('TCH003', 'MAT'), ('TCH004', 'BIO'), ('TCH005', 'ENG')],
    'CLS10-B': [('TCH013', 'PHY'), ('TCH018', 'CHE'), ('TCH015', 'MAT'), ('TCH020', 'BIO'), ('TCH016', 'ENG')],
    'CLS11-JEE': [('TCH001', 'PHY'), ('TCH002', 'CHE'), ('TCH003', 'MAT')],
    'CLS11-NEET': [('TCH009', 'PHY'), ('TCH010', 'CHE'), ('TCH008', 'BIO')],
    'CLS12-JEE': [('TCH017', 'PHY'), ('TCH018', 'CHE'), ('TCH019', 'MAT')],
    'CLS12-NEET': [('TCH006', 'PHY'), ('TCH014', 'CHE'), ('TCH020', 'BIO')],
}
for batch_code, teacher_list in BATCH_TEACHER_MAP.items():
    for tcode, scode in teacher_list:
        BatchTeacher.objects.update_or_create(
            tenant=tenant, batch=batches[batch_code], teacher=teachers_obj[tcode],
            defaults={'subject': subjects[scode], 'is_primary': teacher_list[0][0] == tcode}
        )
print(f"  ✓ Teacher-batch assignments done")

# ============================================================
# 7. STUDENTS (80 across classes 9-12)
# ============================================================
print("\n[7/10] Students...")

INDIAN_NAMES = [
    # (first, last, gender)
    ('Aarav', 'Sharma', 'MALE'), ('Priya', 'Patel', 'FEMALE'), ('Vikram', 'Singh', 'MALE'),
    ('Ananya', 'Gupta', 'FEMALE'), ('Rohan', 'Khan', 'MALE'), ('Nisha', 'Verma', 'FEMALE'),
    ('Arjun', 'Rao', 'MALE'), ('Diya', 'Nair', 'FEMALE'), ('Rahul', 'Joshi', 'MALE'),
    ('Pooja', 'Desai', 'FEMALE'), ('Aditya', 'Kulkarni', 'MALE'), ('Shruti', 'Srivastava', 'FEMALE'),
    ('Karan', 'Bhat', 'MALE'), ('Zara', 'Iyer', 'FEMALE'), ('Sanjay', 'Reddy', 'MALE'),
    ('Riya', 'Das', 'FEMALE'), ('Nikhil', 'Mishra', 'MALE'), ('Kavya', 'Saxena', 'FEMALE'),
    ('Varun', 'Chopra', 'MALE'), ('Shreya', 'Bansal', 'FEMALE'),
    ('Ishaan', 'Mehta', 'MALE'), ('Tanya', 'Kapoor', 'FEMALE'), ('Dev', 'Malhotra', 'MALE'),
    ('Sneha', 'Thakur', 'FEMALE'), ('Yash', 'Chauhan', 'MALE'), ('Meera', 'Bhatt', 'FEMALE'),
    ('Aakash', 'Rawat', 'MALE'), ('Sia', 'Goyal', 'FEMALE'), ('Manav', 'Pandey', 'MALE'),
    ('Ritika', 'Jain', 'FEMALE'), ('Kunal', 'Agarwal', 'MALE'), ('Divya', 'Tiwari', 'FEMALE'),
    ('Harsh', 'Yadav', 'MALE'), ('Neha', 'Dubey', 'FEMALE'), ('Pranav', 'Shukla', 'MALE'),
    ('Simran', 'Bajaj', 'FEMALE'), ('Raj', 'Pillai', 'MALE'), ('Aditi', 'Menon', 'FEMALE'),
    ('Arun', 'Nambiar', 'MALE'), ('Jaya', 'Dixit', 'FEMALE'), ('Siddharth', 'Saxena', 'MALE'),
    ('Anjali', 'Bose', 'FEMALE'), ('Dhruv', 'Choudhury', 'MALE'), ('Tanvi', 'Shetty', 'FEMALE'),
    ('Om', 'Prakash', 'MALE'), ('Kriti', 'Ahluwalia', 'FEMALE'), ('Akash', 'Sethi', 'MALE'),
    ('Roshni', 'Gill', 'FEMALE'), ('Parth', 'Vyas', 'MALE'), ('Misha', 'Kohli', 'FEMALE'),
    ('Vivaan', 'Khanna', 'MALE'), ('Kiara', 'Luthra', 'FEMALE'), ('Sohail', 'Pathan', 'MALE'),
    ('Tara', 'Hegde', 'FEMALE'), ('Reyansh', 'Garg', 'MALE'), ('Anvi', 'Raina', 'FEMALE'),
    ('Atharv', 'Mukherjee', 'MALE'), ('Pari', 'Chatterjee', 'FEMALE'), ('Kabir', 'Grover', 'MALE'),
    ('Myra', 'Sachdev', 'FEMALE'), ('Arnav', 'Biswas', 'MALE'), ('Aisha', 'Sheikh', 'FEMALE'),
    ('Rudra', 'Trivedi', 'MALE'), ('Sara', 'Kaul', 'FEMALE'), ('Laksh', 'Oberoi', 'MALE'),
    ('Navya', 'Mistry', 'FEMALE'), ('Vihaan', 'Chawla', 'MALE'), ('Ira', 'Deshpande', 'FEMALE'),
    ('Advait', 'Khurana', 'MALE'), ('Pihu', 'Tandon', 'FEMALE'), ('Shaurya', 'Batra', 'MALE'),
    ('Avni', 'Madan', 'FEMALE'), ('Ishan', 'Dhawan', 'MALE'), ('Ahana', 'Kashyap', 'FEMALE'),
    ('Neil', 'Soni', 'MALE'), ('Kyra', 'Bedi', 'FEMALE'), ('Agastya', 'Narang', 'MALE'),
    ('Trisha', 'Anand', 'FEMALE'), ('Veer', 'Mehra', 'MALE'), ('Naina', 'Talwar', 'FEMALE'),
    ('Ranvir', 'Sandhu', 'MALE'), ('Aarna', 'Walia', 'FEMALE'),
]

CITIES = ['New Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Jaipur', 'Lucknow', 'Kota']
STATES = ['Delhi', 'Maharashtra', 'Karnataka', 'Telangana', 'Tamil Nadu', 'West Bengal', 'Maharashtra', 'Rajasthan', 'Uttar Pradesh', 'Rajasthan']

# 10 per class 9A, 10 per class 9B, etc.
BATCH_STUDENT_ALLOC = [
    ('CLS9-A', 0, 10), ('CLS9-B', 10, 20),
    ('CLS10-A', 20, 30), ('CLS10-B', 30, 40),
    ('CLS11-JEE', 40, 50), ('CLS11-NEET', 50, 60),
    ('CLS12-JEE', 60, 70), ('CLS12-NEET', 70, 80),
]

students_by_batch = {}
student_counter = 0
for batch_code, start_idx, end_idx in BATCH_STUDENT_ALLOC:
    batch = batches[batch_code]
    cls = batch.class_level
    students_by_batch[batch_code] = []
    for i in range(start_idx, end_idx):
        fname, lname, gender = INDIAN_NAMES[i]
        student_counter += 1
        scode = f'STU2026{student_counter:03d}'
        email = f'{fname.lower()}.{lname.lower()}{student_counter}@lms.com'
        phone = f'91987600{student_counter:04d}'
        city_idx = i % len(CITIES)

        target = batch.exam_target if batch.exam_target in ('JEE', 'NEET') else 'BOTH'
        stream = 'PCM' if target in ('JEE', 'BOTH') else 'PCB'
        if target == 'NEET':
            stream = 'PCB'

        s, created = Student.objects.update_or_create(
            tenant=tenant, student_code=scode,
            defaults={
                'first_name': fname, 'last_name': lname,
                'email': email, 'phone': phone,
                'password_hash': STUDENT_PWD,
                'student_class': cls, 'exam_target': target,
                'stream': stream, 'board': 'CBSE', 'medium': 'ENGLISH',
                'gender': gender,
                'city': CITIES[city_idx], 'state': STATES[city_idx], 'pin_code': f'{110000 + i*11:06d}',
                'batch': batch,
                'status': 'ACTIVE',
                'subscription_type': random.choice(['PREMIUM', 'BASIC', 'PREMIUM', 'PREMIUM']),
                'fee_status': random.choice(['PAID', 'PAID', 'PAID', 'PARTIAL']),
            }
        )
        students_by_batch[batch_code].append(s)

        # Also create BatchStudent enrollment record
        BatchStudent.objects.update_or_create(
            tenant=tenant, batch=batch, email=email,
            defaults={
                'student_id': s.id, 'name': f'{fname} {lname}',
                'phone': phone, 'gender': gender.capitalize(), 'is_active': True,
            }
        )

print(f"  ✓ {student_counter} students created and enrolled")

# ============================================================
# 8. QUESTION BANK — Realistic Indian-curriculum MCQs
# ============================================================
print("\n[8/10] Question Bank...")

# Real questions per subject per class level
QUESTION_BANK = {
    ('9', 'PHY'): [
        ("A car travels 100 m in 5 seconds. What is its average speed?", "A", "20 m/s", "25 m/s", "15 m/s", "10 m/s", "Average speed = Distance/Time = 100/5 = 20 m/s", "EASY"),
        ("Which of Newton's laws defines the concept of inertia?", "A", "First Law", "Second Law", "Third Law", "Law of Gravitation", "Newton's First Law is also called the Law of Inertia.", "EASY"),
        ("The SI unit of force is:", "B", "Joule", "Newton", "Watt", "Pascal", "Force is measured in Newtons (N) = kg⋅m/s².", "EASY"),
        ("If a body of mass 5 kg is accelerated at 2 m/s², the force applied is:", "A", "10 N", "5 N", "2.5 N", "7 N", "F = ma = 5 × 2 = 10 N.", "MEDIUM"),
        ("The value of 'g' on the surface of Earth is approximately:", "C", "8.9 m/s²", "10.8 m/s²", "9.8 m/s²", "6.67 m/s²", "Standard value of g = 9.8 m/s².", "EASY"),
        ("Work done when force is perpendicular to displacement is:", "B", "Maximum", "Zero", "Negative", "Cannot be determined", "W = Fs cos90° = 0.", "MEDIUM"),
        ("Sound waves are:", "B", "Transverse waves", "Longitudinal waves", "Electromagnetic waves", "Standing waves", "Sound propagates as longitudinal (compression-rarefaction) waves.", "EASY"),
        ("The speed of sound in air at room temperature is approximately:", "C", "100 m/s", "230 m/s", "340 m/s", "500 m/s", "Speed of sound in air ≈ 340 m/s at 20°C.", "MEDIUM"),
        ("An echo is heard when minimum distance from the reflecting surface is:", "B", "8.5 m", "17 m", "34 m", "51 m", "Minimum distance = speed × time/2 = 340 × 0.1/2 = 17 m.", "HARD"),
        ("For an object thrown vertically upward, the velocity at the highest point is:", "A", "Zero", "Maximum", "Equal to initial", "9.8 m/s", "At the highest point, all KE converts to PE, velocity = 0.", "MEDIUM"),
    ],
    ('9', 'CHE'): [
        ("Which of the following is a chemical change?", "B", "Melting of ice", "Burning of paper", "Dissolving sugar", "Breaking glass", "Burning is an irreversible chemical reaction producing new substances.", "EASY"),
        ("The number of atoms in one mole of a substance is:", "C", "6.022 × 10²⁰", "6.022 × 10²¹", "6.022 × 10²³", "6.022 × 10²⁴", "Avogadro's number = 6.022 × 10²³.", "EASY"),
        ("Which is NOT a mixture?", "D", "Air", "Sea water", "Soil", "Distilled water", "Distilled water is a pure compound (H₂O).", "EASY"),
        ("In Thomson's model of atom, the atom resembles:", "A", "Watermelon", "Solar system", "Nuclear model", "Wave model", "Thomson's plum pudding model — positive sphere with electrons embedded like seeds in watermelon.", "MEDIUM"),
        ("Rutherford's alpha particle scattering experiment led to the discovery of:", "B", "Electron", "Nucleus", "Neutron", "Proton", "Most alpha particles passed through, but some bounced back — indicating a dense nucleus.", "MEDIUM"),
        ("Which element has the atomic number 8?", "C", "Nitrogen", "Carbon", "Oxygen", "Fluorine", "Oxygen has 8 protons ∴ atomic number = 8.", "EASY"),
        ("The chemical formula of Calcium Hydroxide is:", "B", "CaO", "Ca(OH)₂", "CaCO₃", "CaCl₂", "Calcium Hydroxide = slaked lime = Ca(OH)₂.", "MEDIUM"),
        ("A colloid has particle size in the range:", "B", "< 1 nm", "1 nm to 100 nm", "100 nm to 1000 nm", "> 1000 nm", "Colloids have particles between 1-100 nm — smaller than suspension, larger than solution.", "HARD"),
    ],
    ('9', 'MAT'): [
        ("√2 is a/an:", "B", "Rational number", "Irrational number", "Natural number", "Integer", "√2 = 1.41421356... is non-terminating, non-repeating — irrational.", "EASY"),
        ("The degree of the polynomial 4x³ + 2x² - 7 is:", "C", "1", "2", "3", "7", "Highest power of x is 3 ∴ degree = 3.", "EASY"),
        ("If p(x) = x² - 3x + 2, then p(1) =", "A", "0", "1", "2", "-1", "p(1) = 1 - 3 + 2 = 0. So x=1 is a zero.", "MEDIUM"),
        ("The point (-3, 4) lies in which quadrant?", "B", "First", "Second", "Third", "Fourth", "x < 0 and y > 0 → Second quadrant.", "EASY"),
        ("Two angles of a triangle are 45° and 65°. The third angle is:", "C", "60°", "80°", "70°", "90°", "Sum of angles = 180°. Third = 180 - 45 - 65 = 70°.", "EASY"),
        ("The zero of the linear polynomial 2x + 3 is:", "B", "3/2", "-3/2", "2/3", "-2/3", "2x + 3 = 0 ⟹ x = -3/2.", "MEDIUM"),
        ("If x = 2, y = 1 is a solution of 2x + 3y = k, then k =", "A", "7", "5", "8", "6", "2(2) + 3(1) = 4 + 3 = 7.", "MEDIUM"),
        ("The Heron's formula for area of a triangle is:", "A", "√[s(s-a)(s-b)(s-c)]", "½ × b × h", "a × b × sin C", "πr²", "Heron's formula uses semi-perimeter s = (a+b+c)/2.", "MEDIUM"),
    ],
    ('10', 'PHY'): [
        ("The power of a concave lens is:", "B", "Positive", "Negative", "Zero", "Infinite", "Concave (diverging) lens has negative focal length ∴ negative power.", "EASY"),
        ("1 kilowatt-hour (kWh) equals:", "C", "3.6 × 10³ J", "3.6 × 10⁵ J", "3.6 × 10⁶ J", "3.6 × 10⁹ J", "1 kWh = 1000W × 3600s = 3.6 × 10⁶ J.", "MEDIUM"),
        ("The SI unit of resistance is:", "A", "Ohm (Ω)", "Volt (V)", "Ampere (A)", "Watt (W)", "Resistance = V/I, measured in Ohms.", "EASY"),
        ("If two resistors of 4Ω and 6Ω are connected in parallel, the equivalent resistance is:", "B", "10 Ω", "2.4 Ω", "5 Ω", "24 Ω", "1/R = 1/4 + 1/6 = 5/12, R = 2.4 Ω.", "MEDIUM"),
        ("Fleming's Left Hand Rule is used to determine:", "A", "Direction of force on a current-carrying conductor", "Direction of induced current", "Direction of magnetic field", "Direction of electric field", "Used for motors — force on conductor in magnetic field.", "MEDIUM"),
        ("The image formed by a convex lens when object is at 2F is:", "C", "Virtual and erect", "Virtual and inverted", "Real, inverted, same size", "Real, inverted, magnified", "At 2F: image is at 2F, real, inverted, same size (m = -1).", "MEDIUM"),
        ("Which colour of visible light has the shortest wavelength?", "D", "Red", "Yellow", "Green", "Violet", "VIBGYOR — Violet has shortest wavelength (~380 nm).", "EASY"),
        ("A 100W bulb is used for 10 hours. The energy consumed is:", "A", "1 kWh", "10 kWh", "0.1 kWh", "100 kWh", "E = P × t = 100W × 10h = 1000 Wh = 1 kWh.", "EASY"),
        ("Myopia is corrected using:", "B", "Convex lens", "Concave lens", "Cylindrical lens", "Bifocal lens", "Myopia (short-sightedness) is corrected with a diverging (concave) lens.", "MEDIUM"),
        ("The magnetic field inside a solenoid is:", "A", "Uniform", "Non-uniform", "Zero", "Variable", "Inside a long solenoid, B is uniform and parallel to the axis.", "MEDIUM"),
    ],
    ('10', 'CHE'): [
        ("pH of a neutral solution at 25°C is:", "B", "0", "7", "14", "1", "Pure water [H⁺] = 10⁻⁷, pH = 7.", "EASY"),
        ("Which gas is evolved when dilute HCl reacts with Zinc?", "A", "Hydrogen", "Oxygen", "Chlorine", "Nitrogen", "Zn + 2HCl → ZnCl₂ + H₂↑ (pop test).", "EASY"),
        ("The most reactive metal in the reactivity series is:", "C", "Iron", "Copper", "Potassium", "Gold", "K > Na > Ca > Mg > ... Potassium is most reactive.", "MEDIUM"),
        ("Ethanol has the molecular formula:", "B", "CH₃OH", "C₂H₅OH", "C₃H₇OH", "C₆H₁₂O₆", "Ethanol = C₂H₅OH (2 carbons).", "EASY"),
        ("Baking soda is chemically:", "A", "NaHCO₃", "Na₂CO₃", "NaCl", "NaOH", "Baking soda = Sodium hydrogen carbonate = NaHCO₃.", "EASY"),
        ("An oxidation reaction involves:", "B", "Gain of electrons", "Loss of electrons", "Gain of protons", "No change", "Oxidation = Loss of electrons (OIL RIG).", "MEDIUM"),
        ("The functional group —COOH is called:", "C", "Aldehyde", "Ketone", "Carboxylic acid", "Alcohol", "—COOH is the carboxyl group, found in carboxylic acids.", "MEDIUM"),
        ("Which reaction is used to extract metals in the middle of the reactivity series?", "B", "Electrolysis", "Reduction with carbon", "Self-reduction", "Amalgamation", "Moderately reactive metals (Zn, Fe) are reduced with carbon/coke.", "HARD"),
    ],
    ('10', 'MAT'): [
        ("HCF of 12 and 18 is:", "A", "6", "3", "12", "36", "12 = 2² × 3, 18 = 2 × 3². HCF = 2 × 3 = 6.", "EASY"),
        ("If one zero of p(x) = x² - 6x + k is 2, then k =", "B", "4", "8", "12", "6", "p(2) = 4 - 12 + k = 0 ⟹ k = 8.", "MEDIUM"),
        ("The n-th term of AP: 2, 5, 8, 11... is:", "A", "3n - 1", "3n + 1", "2n + 1", "n + 3", "a = 2, d = 3. aₙ = 2 + (n-1)3 = 3n - 1.", "MEDIUM"),
        ("The discriminant of 2x² - 5x + 3 = 0 is:", "C", "-1", "0", "1", "49", "D = b²-4ac = 25 - 24 = 1.", "MEDIUM"),
        ("The sum of first 10 natural numbers is:", "B", "50", "55", "45", "100", "S = n(n+1)/2 = 10 × 11/2 = 55.", "EASY"),
        ("If lines are parallel, then the pair of linear equations has:", "A", "No solution", "Unique solution", "Infinitely many solutions", "Two solutions", "Parallel lines never intersect → inconsistent → no solution.", "MEDIUM"),
        ("The quadratic formula is x =", "B", "b ± √(b²-4ac) / 2a", "(-b ± √(b²-4ac)) / 2a", "b² - 4ac / 2a", "None of these", "Standard quadratic formula: x = [-b ± √(b²-4ac)] / 2a.", "EASY"),
        ("If sin θ = 3/5, then cos θ =", "A", "4/5", "3/4", "5/3", "5/4", "cos²θ = 1 - sin²θ = 1 - 9/25 = 16/25, cos θ = 4/5.", "MEDIUM"),
    ],
    ('11', 'PHY'): [
        ("The dimension of Planck's constant is:", "B", "[MLT⁻¹]", "[ML²T⁻¹]", "[ML²T⁻²]", "[MLT⁻²]", "h = E/ν, [h] = [ML²T⁻²]/[T⁻¹] = [ML²T⁻¹].", "MEDIUM"),
        ("A projectile is launched at 60° with speed 20 m/s. The range is: (g=10)", "C", "20 m", "20√3 m", "34.64 m", "40 m", "R = u²sin2θ/g = 400 × sin120°/10 = 400 × (√3/2)/10 ≈ 34.64 m.", "HARD"),
        ("Two vectors of magnitude 3 and 4 are perpendicular. Their resultant is:", "A", "5", "7", "1", "12", "R = √(3² + 4²) = √25 = 5.", "EASY"),
        ("The coefficient of static friction is 0.5. Normal force is 20 N. Maximum static friction is:", "B", "5 N", "10 N", "20 N", "40 N", "f = μN = 0.5 × 20 = 10 N.", "EASY"),
        ("In a perfectly inelastic collision:", "C", "KE is conserved", "Momentum is not conserved", "KE is not conserved", "Both KE and momentum are not conserved", "In inelastic collision, momentum is conserved but KE is not.", "MEDIUM"),
        ("The moment of inertia of a solid sphere about its diameter is:", "A", "(2/5)MR²", "(1/2)MR²", "(2/3)MR²", "MR²", "I = (2/5)MR² for a solid sphere about a diameter.", "HARD"),
        ("A body starts from rest with uniform acceleration 2 m/s². Distance in 5th second:", "C", "8 m", "10 m", "9 m", "12 m", "sₙ = u + a(2n-1)/2 = 0 + 2(9)/2 = 9 m.", "MEDIUM"),
        ("Unit vector along [3, 4, 0] is:", "B", "[3, 4, 0]", "[3/5, 4/5, 0]", "[0.6, 0.8, 1]", "[1, 1, 0]", "Magnitude = 5. Unit = [3/5, 4/5, 0].", "MEDIUM"),
        ("Angular momentum is conserved when:", "A", "Net external torque is zero", "Net external force is zero", "Linear momentum is conserved", "KE is conserved", "τ_ext = 0 ⟹ dL/dt = 0 ⟹ L = constant.", "MEDIUM"),
        ("If velocity is doubled, kinetic energy becomes:", "C", "Double", "Triple", "Four times", "Half", "KE = ½mv². If v → 2v, KE → 4 × (½mv²).", "EASY"),
    ],
    ('11', 'CHE'): [
        ("The number of moles in 36 g of water is:", "A", "2", "1", "3", "0.5", "Molar mass of H₂O = 18 g/mol. n = 36/18 = 2 mol.", "EASY"),
        ("Which quantum number determines the shape of an orbital?", "B", "Principal (n)", "Azimuthal (l)", "Magnetic (ml)", "Spin (ms)", "l determines orbital shape: s(0), p(1), d(2), f(3).", "MEDIUM"),
        ("sp³ hybridization gives:", "A", "Tetrahedral geometry", "Linear geometry", "Trigonal planar", "Octahedral", "sp³ → 4 hybrid orbitals → tetrahedral (109.5°).", "MEDIUM"),
        ("An ideal gas obeys:", "C", "Boyle's law only", "Charles's law only", "Both Boyle's and Charles's laws", "Neither", "Ideal gas: PV = nRT, following all gas laws.", "EASY"),
        ("Enthalpy change for an exothermic reaction is:", "B", "Positive", "Negative", "Zero", "Undefined", "Exothermic: heat released, ΔH < 0.", "EASY"),
        ("The bond order of O₂ is:", "C", "1", "1.5", "2", "3", "O₂: BO = (10-6)/2 = 2 from MO theory.", "MEDIUM"),
        ("Which of the following has the highest lattice energy?", "A", "NaCl", "KCl", "RbCl", "CsCl", "Smaller ions → higher lattice energy. Na⁺ < K⁺ < Rb⁺ < Cs⁺.", "HARD"),
        ("At STP, the volume of 1 mole of an ideal gas is:", "B", "11.2 L", "22.4 L", "44.8 L", "5.6 L", "Molar volume at STP = 22.4 L/mol.", "EASY"),
        ("The process in which entropy always increases is:", "C", "Freezing", "Condensation", "Sublimation", "Crystallization", "Sublimation: solid→gas, huge increase in disorder.", "MEDIUM"),
        ("First ionization energy generally increases across a period because:", "A", "Effective nuclear charge increases", "Atomic radius increases", "Electron affinity decreases", "Shielding increases", "Across period: Zeff ↑, atomic radius ↓, IE ↑.", "MEDIUM"),
    ],
    ('11', 'MAT'): [
        ("If A = {1, 2, 3} and B = {2, 3, 4}, then A ∩ B =", "B", "{1, 4}", "{2, 3}", "{1, 2, 3, 4}", "{}", "Intersection = common elements = {2, 3}.", "EASY"),
        ("The value of sin 30° + cos 60° is:", "A", "1", "√3", "1/2", "√3/2", "sin 30° = 1/2, cos 60° = 1/2. Sum = 1.", "EASY"),
        ("i² + i⁴ + i⁶ =", "C", "1", "-1", "-1 + 1 + (-1) = -1", "3i", "i² = -1, i⁴ = 1, i⁶ = -1. Sum = -1.", "MEDIUM"),
        ("⁵C₂ =", "A", "10", "20", "5", "25", "⁵C₂ = 5!/(2!3!) = 10.", "EASY"),
        ("Sum of infinite GP: 1, 1/2, 1/4, ... is:", "B", "1", "2", "4", "∞", "S = a/(1-r) = 1/(1-½) = 2.", "MEDIUM"),
        ("Number of permutations of the word 'MATH' is:", "C", "12", "16", "24", "6", "4 distinct letters: 4! = 24.", "EASY"),
        ("If f(x) = x² + 1, then f(f(1)) =", "A", "5", "3", "4", "2", "f(1) = 2, f(2) = 5.", "MEDIUM"),
        ("The general solution of sin x = 0 is:", "B", "x = (2n+1)π/2", "x = nπ", "x = 2nπ", "x = nπ/2", "sin x = 0 when x = nπ, n ∈ Z.", "MEDIUM"),
        ("Domain of f(x) = √(x - 3) is:", "A", "x ≥ 3", "x > 3", "x ≤ 3", "All real numbers", "Under root must be ≥ 0: x - 3 ≥ 0 ⟹ x ≥ 3.", "MEDIUM"),
        ("De Morgan's law states (A ∪ B)' =", "C", "A' ∪ B'", "A ∩ B", "A' ∩ B'", "A' ∪ B", "(A ∪ B)' = A' ∩ B'.", "EASY"),
    ],
    ('12', 'PHY'): [
        ("Coulomb's law force between two charges is inversely proportional to:", "B", "Distance", "Square of distance", "Cube of distance", "Charge", "F = kq₁q₂/r², inversely proportional to r².", "EASY"),
        ("The electric field inside a conductor in electrostatic equilibrium is:", "A", "Zero", "Maximum", "Uniform", "Variable", "In electrostatic equilibrium, E = 0 inside a conductor.", "EASY"),
        ("The capacitance of a parallel plate capacitor with dielectric constant K becomes:", "C", "C/K", "C + K", "KC", "C - K", "C' = KC₀. Dielectric increases capacitance by factor K.", "MEDIUM"),
        ("Kirchhoff's junction rule is based on conservation of:", "A", "Charge", "Energy", "Momentum", "Mass", "Junction rule: ΣI_in = ΣI_out (charge conservation).", "EASY"),
        ("In a Wheatstone bridge at balance, the galvanometer shows:", "B", "Maximum deflection", "Zero deflection", "Oscillation", "Positive deflection only", "At balance: P/Q = R/S, no current through galvanometer.", "MEDIUM"),
        ("The induced EMF in a coil is proportional to:", "A", "Rate of change of magnetic flux", "Magnetic flux", "Area of coil", "Resistance of coil", "Faraday's law: ε = -dΦ/dt.", "MEDIUM"),
        ("In Young's double slit experiment, fringe width increases when:", "C", "Slit separation increases", "Wavelength decreases", "Distance to screen increases", "Slit width increases", "β = λD/d. β ↑ when D ↑ or d ↓ or λ ↑.", "MEDIUM"),
        ("The de Broglie wavelength of an electron accelerated through V volts is:", "B", "h/√(2meV)", "1.227/√V nm", "Both A and B", "h/mv only", "λ = h/√(2meV) = 1.227/√V nm.", "HARD"),
        ("The binding energy per nucleon is maximum for:", "C", "Hydrogen", "Uranium", "Iron (Fe-56)", "Helium", "Fe-56 has the highest BE/nucleon ≈ 8.8 MeV — most stable.", "MEDIUM"),
        ("The energy of a photon of wavelength 6600 Å is: (h = 6.6×10⁻³⁴)", "A", "3 × 10⁻¹⁹ J", "3 × 10⁻²⁰ J", "3 × 10⁻¹⁸ J", "6 × 10⁻¹⁹ J", "E = hc/λ = (6.6×10⁻³⁴ × 3×10⁸) / (6600×10⁻¹⁰) = 3×10⁻¹⁹ J.", "HARD"),
    ],
    ('12', 'CHE'): [
        ("In a face-centred cubic unit cell, the number of atoms is:", "C", "1", "2", "4", "6", "FCC: 8 corners × 1/8 + 6 faces × 1/2 = 1 + 3 = 4.", "MEDIUM"),
        ("Raoult's law is applicable to:", "A", "Ideal solutions", "Non-ideal solutions", "Electrolytic solutions", "Colloidal solutions", "Raoult's law: P = x₁P₁° + x₂P₂° for ideal solutions.", "EASY"),
        ("The unit of rate constant for first order reaction is:", "B", "mol L⁻¹ s⁻¹", "s⁻¹", "L mol⁻¹ s⁻¹", "L² mol⁻² s⁻¹", "First order: rate = k[A], k units = s⁻¹.", "MEDIUM"),
        ("In a galvanic cell, oxidation occurs at:", "A", "Anode", "Cathode", "Salt bridge", "Both electrodes", "Anode = oxidation, Cathode = reduction (An Ox, Red Cat).", "EASY"),
        ("The molar conductivity at infinite dilution of NaCl is:", "B", "Cannot be measured directly", "Obtained by Kohlrausch's law", "Zero", "Infinite", "Strong electrolytes: extrapolate or use Kohlrausch's law Λ°m = λ°+ + λ°-.", "MEDIUM"),
        ("Which of the following is a paramagnetic substance?", "C", "Zn", "Cu", "Fe²⁺", "Ag", "Fe²⁺ has unpaired electrons → paramagnetic.", "MEDIUM"),
        ("Lanthanoid contraction is due to:", "A", "Poor shielding by 4f electrons", "Good shielding by 5d electrons", "Increase in atomic number", "Decrease in nuclear charge", "4f electrons shield poorly → Zeff ↑ → radius ↓ across lanthanoids.", "HARD"),
        ("The order of reaction can be:", "D", "Positive integer only", "Negative only", "Zero only", "Zero, positive, negative, or fractional", "Order can be 0, 1, 2, fractional, or negative — determined experimentally.", "MEDIUM"),
        ("Elevation in boiling point is a:", "B", "Extensive property", "Colligative property", "Intensive property", "Chemical property", "ΔTb depends only on number of solute particles → colligative.", "EASY"),
        ("The standard electrode potential of SHE is:", "A", "0.00 V", "1.00 V", "-1.00 V", "0.76 V", "Standard Hydrogen Electrode is the reference: E° = 0.00 V by definition.", "EASY"),
    ],
    ('12', 'MAT'): [
        ("If f: R → R, f(x) = x³, then f is:", "C", "One-one but not onto", "Onto but not one-one", "Both one-one and onto (bijective)", "Neither", "f(x) = x³ is strictly increasing, passes through all reals → bijective.", "MEDIUM"),
        ("sin⁻¹(1/2) =", "A", "π/6", "π/4", "π/3", "π/2", "sin(π/6) = 1/2, so sin⁻¹(1/2) = π/6.", "EASY"),
        ("If A is a 3×3 matrix with |A| = 5, then |adj(A)| =", "B", "5", "25", "125", "1/5", "|adj(A)| = |A|^(n-1) = 5² = 25 for n=3.", "HARD"),
        ("∫ e^x dx =", "A", "e^x + C", "xe^x + C", "e^x / x + C", "ln(e^x) + C", "Standard integral: ∫eˣ dx = eˣ + C.", "EASY"),
        ("d/dx (sin x) =", "A", "cos x", "-cos x", "sin x", "-sin x", "Basic derivative: (sin x)' = cos x.", "EASY"),
        ("The value of ∫₀¹ x² dx is:", "C", "1", "1/2", "1/3", "1/4", "∫₀¹ x² dx = [x³/3]₀¹ = 1/3.", "EASY"),
        ("If y = ln(sin x), then dy/dx =", "B", "1/sin x", "cot x", "tan x", "cos x", "dy/dx = cos x / sin x = cot x (chain rule).", "MEDIUM"),
        ("The determinant |[1,2],[3,4]| =", "B", "10", "-2", "2", "-10", "|A| = 1×4 - 2×3 = 4 - 6 = -2.", "EASY"),
        ("A function f is continuous at x = a if:", "A", "lim(x→a) f(x) = f(a)", "f(a) exists", "lim exists", "f is differentiable", "Continuity requires: limit exists, f(a) exists, AND they are equal.", "MEDIUM"),
        ("The area under y = x from 0 to 2 is:", "B", "4", "2", "1", "8", "∫₀² x dx = [x²/2]₀² = 2.", "EASY"),
    ],
}

# Also add biology and English for 11 and 12
QUESTION_BANK[('11', 'BIO')] = [
    ("The powerhouse of the cell is:", "B", "Nucleus", "Mitochondria", "Ribosome", "Golgi body", "Mitochondria produce ATP through cellular respiration.", "EASY"),
    ("Photosynthesis occurs in:", "A", "Chloroplast", "Mitochondria", "Nucleus", "Ribosome", "Chloroplasts contain chlorophyll for photosynthesis.", "EASY"),
    ("The light reaction of photosynthesis occurs in:", "B", "Stroma", "Thylakoid membrane", "Cytoplasm", "Cell wall", "Light reactions occur in thylakoid membranes of chloroplasts.", "MEDIUM"),
    ("DNA replication is:", "A", "Semi-conservative", "Conservative", "Dispersive", "Random", "Meselson-Stahl experiment proved semi-conservative replication.", "MEDIUM"),
    ("The cell organelle involved in programmed cell death is:", "C", "Ribosome", "Peroxisome", "Lysosome", "Centriole", "Lysosomes release hydrolytic enzymes → \"suicide bags\" of the cell.", "MEDIUM"),
]
QUESTION_BANK[('12', 'BIO')] = [
    ("The process of formation of mRNA from DNA is called:", "B", "Replication", "Transcription", "Translation", "Transduction", "Transcription: DNA → mRNA by RNA polymerase.", "EASY"),
    ("Restriction enzymes are used in:", "A", "Genetic engineering", "PCR", "Gel electrophoresis", "Fermentation", "Restriction enzymes cut DNA at specific sites — molecular scissors.", "EASY"),
    ("The first transgenic animal was:", "C", "Sheep (Dolly)", "Cow", "Mouse", "Goat", "First transgenic mouse was created in the early 1980s.", "MEDIUM"),
    ("Mendel's law of segregation is also known as:", "A", "Law of purity of gametes", "Law of dominance", "Law of independent assortment", "Law of variation", "During gamete formation, alleles separate — gametes are pure.", "MEDIUM"),
    ("PCR stands for:", "B", "Protein Chain Reaction", "Polymerase Chain Reaction", "Partial Cell Replication", "Primary Carbon Reduction", "PCR amplifies DNA using thermostable DNA polymerase (Taq).", "EASY"),
]

# ============================================================
# 9. CREATE TESTS & QUESTIONS
# ============================================================
print("\n[9/10] Creating Tests & Exams...")

def get_teacher_for_subject(subj_code, cls_level):
    """Find a teacher assigned to this subject for the given class level."""
    for bcode, tlist in BATCH_TEACHER_MAP.items():
        if batches[bcode].class_level == cls_level:
            for tcode, scode in tlist:
                if scode == subj_code:
                    return teachers_obj[tcode]
    return list(teachers_obj.values())[0]

def get_batch_for_class(cls_level):
    """Get the first batch for a class level."""
    for bcode, b in batches.items():
        if b.class_level == cls_level:
            return b
    return list(batches.values())[0]

def create_test_with_questions(test_data, questions_data):
    """Create a test and populate it with questions."""
    test, _ = Test.objects.update_or_create(
        tenant=tenant, test_code=test_data['test_code'],
        defaults=test_data
    )
    # Create questions
    for idx, qdata in enumerate(questions_data, 1):
        q_text, correct, optA, optB, optC, optD, explanation, diff = qdata
        Question.objects.update_or_create(
            tenant=tenant, test=test, question_order=idx,
            defaults={
                'question_code': f'{test_data["test_code"]}-Q{idx:02d}',
                'question_text': q_text,
                'question_type': 'MCQ_SINGLE',
                'difficulty': diff,
                'option_a': optA, 'option_b': optB,
                'option_c': optC, 'option_d': optD,
                'correct_answer': correct,
                'answer_explanation': explanation,
                'positive_marks': test_data.get('positive_marks_per_question', Decimal('4')),
                'negative_marks': test_data.get('negative_marks_per_question', Decimal('-1')),
                'subject': test_data.get('subject'),
                'is_active': True,
            }
        )
    test.total_questions = len(questions_data)
    test.total_marks = len(questions_data) * test_data.get('positive_marks_per_question', Decimal('4'))
    test.passing_marks = test.total_marks * Decimal('0.33')
    test.save()
    return test

# --- LIVE EXAMS (happening RIGHT NOW) ---
print("  Creating LIVE exams (active now)...")
live_start = now - timedelta(minutes=15)
live_end = now + timedelta(hours=2, minutes=45)

LIVE_TESTS = []
for cls in ['9', '10', '11', '12']:
    for subj_code, subj_name in [('PHY', 'Physics'), ('CHE', 'Chemistry'), ('MAT', 'Mathematics')]:
        qbank_key = (cls, subj_code)
        if qbank_key not in QUESTION_BANK:
            continue

        batch = get_batch_for_class(cls)
        teacher = get_teacher_for_subject(subj_code, cls)
        chapter = None
        for key, ch in chapters_map.items():
            if key[0] == cls and key[1] == subj_code:
                chapter = ch
                break

        test_code = f'LIVE-{cls}-{subj_code}-APR2026'
        test_data = {
            'tenant': tenant,
            'test_code': test_code,
            'title': f'Class {cls} {subj_name} — Live Exam (April 2026)',
            'description': f'Live examination for Class {cls} {subj_name}. This exam is currently in progress.',
            'instructions': f'1. Total {len(QUESTION_BANK[qbank_key])} questions\n2. Each correct answer: +4 marks\n3. Each wrong answer: -1 mark\n4. Duration: 60 minutes\n5. No tab switching allowed',
            'test_type': 'MONTHLY',
            'exam_target': 'BOARDS' if cls in ['9', '10'] else ('JEE_MAINS' if batch.exam_target == 'JEE' else 'NEET'),
            'difficulty_level': 'MIXED',
            'subject': subjects[subj_code],
            'chapter': chapter,
            'batch': batch,
            'total_duration_minutes': 60,
            'start_datetime': live_start,
            'end_datetime': live_end,
            'show_timer': True,
            'positive_marks_per_question': Decimal('4'),
            'negative_marks_per_question': Decimal('-1'),
            'max_attempts': 1,
            'shuffle_questions': True,
            'shuffle_options': False,
            'allow_review': True,
            'allow_backward': True,
            'access_mode': 'BATCH_ONLY',
            'result_display_mode': 'IMMEDIATE',
            'show_correct_answers': True,
            'show_explanations': True,
            'show_rank': True,
            'show_percentile': True,
            'prevent_tab_switch': True,
            'max_tab_switches': 3,
            'prevent_copy_paste': True,
            'status': 'ACTIVE',
            'published_at': live_start - timedelta(hours=1),
            'teacher': teacher,
        }

        questions = QUESTION_BANK[qbank_key]
        test = create_test_with_questions(test_data, questions)
        LIVE_TESTS.append((test, cls, subj_code))
        print(f"    ✓ LIVE: {test.title} ({test.total_questions}Q, ends {live_end.strftime('%H:%M')})")

# --- SCHEDULED EXAMS (upcoming) ---
print("\n  Creating SCHEDULED (upcoming) exams...")
SCHEDULED_DATES = [
    (timedelta(days=1, hours=4), 'Unit Test — April Week 3'),
    (timedelta(days=3, hours=2), 'Chapter Test — April End'),
    (timedelta(days=7, hours=3), 'Weekly Assessment'),
    (timedelta(days=14, hours=5), 'Mid-Term Mock Exam'),
    (timedelta(days=30, hours=4), 'Monthly Grand Test'),
]

for cls in ['9', '10', '11', '12']:
    for delta, label in SCHEDULED_DATES:
        for subj_code, subj_name in [('PHY', 'Physics'), ('MAT', 'Mathematics')]:
            qbank_key = (cls, subj_code)
            if qbank_key not in QUESTION_BANK:
                continue

            batch = get_batch_for_class(cls)
            teacher = get_teacher_for_subject(subj_code, cls)
            sched_start = now + delta
            sched_end = sched_start + timedelta(hours=1, minutes=30)
            test_code = f'SCH-{cls}-{subj_code}-{delta.days:02d}D'
            ttype = 'WEEKLY' if 'Weekly' in label else ('UNIT_TEST' if 'Unit' in label else ('CHAPTER_TEST' if 'Chapter' in label else ('MOCK_EXAM' if 'Mock' in label else 'MONTHLY')))

            test_data = {
                'tenant': tenant,
                'test_code': test_code,
                'title': f'Class {cls} {subj_name} — {label}',
                'description': f'{label} for Class {cls} {subj_name}. Scheduled for {sched_start.strftime("%d %b %Y %H:%M")}.',
                'instructions': f'1. Duration: 90 minutes\n2. +4 for correct, -1 for wrong\n3. Attempt all questions',
                'test_type': ttype,
                'exam_target': 'BOARDS' if cls in ['9', '10'] else 'GENERAL',
                'difficulty_level': 'MIXED',
                'subject': subjects[subj_code],
                'batch': batch,
                'total_duration_minutes': 90,
                'start_datetime': sched_start,
                'end_datetime': sched_end,
                'positive_marks_per_question': Decimal('4'),
                'negative_marks_per_question': Decimal('-1'),
                'max_attempts': 1,
                'shuffle_questions': True,
                'access_mode': 'SCHEDULED',
                'result_display_mode': 'IMMEDIATE',
                'show_correct_answers': True,
                'show_explanations': True,
                'status': 'PUBLISHED',
                'published_at': now,
                'teacher': teacher,
            }
            questions = QUESTION_BANK[qbank_key][:6]  # Subset of questions
            test = create_test_with_questions(test_data, questions)
            print(f"    ✓ SCHEDULED: {test.title} — {sched_start.strftime('%d %b %H:%M')}")

# --- COMPLETED EXAMS (past with results) ---
print("\n  Creating COMPLETED exams with student results...")
PAST_DATES = [
    (timedelta(days=5), 'Weekly Test — April Week 1'),
    (timedelta(days=12), 'Unit Test — March End'),
    (timedelta(days=20), 'Mid-Term Examination'),
]

for cls in ['9', '10', '11', '12']:
    batch_code = [bc for bc, b in batches.items() if b.class_level == cls][0]
    batch_students = students_by_batch.get(batch_code, [])

    for delta, label in PAST_DATES:
        for subj_code, subj_name in [('PHY', 'Physics'), ('CHE', 'Chemistry'), ('MAT', 'Mathematics')]:
            qbank_key = (cls, subj_code)
            if qbank_key not in QUESTION_BANK:
                continue

            batch = batches[batch_code]
            teacher = get_teacher_for_subject(subj_code, cls)
            past_start = now - delta
            past_end = past_start + timedelta(hours=1)
            test_code = f'PAST-{cls}-{subj_code}-{delta.days:02d}D'

            test_data = {
                'tenant': tenant,
                'test_code': test_code,
                'title': f'Class {cls} {subj_name} — {label}',
                'description': f'{label} for Class {cls} {subj_name}.',
                'instructions': 'Standard exam instructions apply.',
                'test_type': 'WEEKLY' if 'Weekly' in label else ('UNIT_TEST' if 'Unit' in label else 'MOCK_EXAM'),
                'exam_target': 'BOARDS' if cls in ['9', '10'] else 'GENERAL',
                'difficulty_level': 'MIXED',
                'subject': subjects[subj_code],
                'batch': batch,
                'total_duration_minutes': 60,
                'start_datetime': past_start,
                'end_datetime': past_end,
                'positive_marks_per_question': Decimal('4'),
                'negative_marks_per_question': Decimal('-1'),
                'max_attempts': 1,
                'access_mode': 'BATCH_ONLY',
                'result_display_mode': 'IMMEDIATE',
                'show_correct_answers': True,
                'show_explanations': True,
                'show_rank': True,
                'status': 'COMPLETED',
                'published_at': past_start - timedelta(days=1),
                'teacher': teacher,
            }

            questions = QUESTION_BANK[qbank_key]
            test = create_test_with_questions(test_data, questions)

            # Create student attempts with results
            rank = 0
            for student in batch_students:
                rank += 1
                # Simulate realistic performance
                num_q = len(questions)
                correct = random.randint(max(2, num_q // 3), num_q)
                incorrect = random.randint(0, num_q - correct)
                skipped = num_q - correct - incorrect
                score = Decimal(str(correct * 4 + incorrect * (-1)))
                total_marks = Decimal(str(num_q * 4))
                pct = max(Decimal('0'), score / total_marks * 100)

                attempt, _ = TestAttempt.objects.update_or_create(
                    test=test, student=student, attempt_number=1,
                    defaults={
                        'tenant': tenant,
                        'started_at': past_start + timedelta(minutes=random.randint(0, 5)),
                        'submitted_at': past_start + timedelta(minutes=random.randint(35, 58)),
                        'time_taken_seconds': random.randint(2100, 3500),
                        'total_questions': num_q,
                        'attempted': correct + incorrect,
                        'correct': correct,
                        'incorrect': incorrect,
                        'skipped': skipped,
                        'raw_score': score,
                        'total_marks': total_marks,
                        'percentage': pct,
                        'rank': rank,
                        'result': 'PASS' if pct >= 33 else 'FAIL',
                        'status': 'EVALUATED',
                    }
                )

                # Create per-question answers
                for q_idx, qdata in enumerate(questions):
                    q_obj = Question.objects.get(tenant=tenant, test=test, question_order=q_idx + 1)
                    if q_idx < correct:
                        # Correct
                        ans_val = qdata[1]
                        is_correct = True
                        marks = Decimal('4')
                        status = 'ANSWERED'
                    elif q_idx < correct + incorrect:
                        # Incorrect
                        wrong_options = ['A', 'B', 'C', 'D']
                        wrong_options.remove(qdata[1])
                        ans_val = random.choice(wrong_options)
                        is_correct = False
                        marks = Decimal('-1')
                        status = 'ANSWERED'
                    else:
                        # Skipped
                        ans_val = None
                        is_correct = None
                        marks = Decimal('0')
                        status = 'SKIPPED'

                    TestAttemptAnswer.objects.update_or_create(
                        attempt=attempt, question=q_obj,
                        defaults={
                            'tenant': tenant,
                            'student_answer': ans_val,
                            'status': status,
                            'is_correct': is_correct,
                            'marks_awarded': marks,
                            'time_spent_seconds': random.randint(30, 180),
                            'visit_count': random.randint(1, 3),
                        }
                    )

            print(f"    ✓ COMPLETED: {test.title} — {len(batch_students)} attempts graded")

# --- PRACTICE TESTS (always available) ---
print("\n  Creating PRACTICE tests (always open)...")
for cls in ['9', '10', '11', '12']:
    for subj_code, subj_name in [('PHY', 'Physics'), ('CHE', 'Chemistry'), ('MAT', 'Mathematics')]:
        qbank_key = (cls, subj_code)
        if qbank_key not in QUESTION_BANK:
            continue

        batch = get_batch_for_class(cls)
        teacher = get_teacher_for_subject(subj_code, cls)
        test_code = f'PRAC-{cls}-{subj_code}-001'

        test_data = {
            'tenant': tenant,
            'test_code': test_code,
            'title': f'Class {cls} {subj_name} — Practice Questions',
            'description': f'Practice MCQs for Class {cls} {subj_name}. Unlimited attempts.',
            'instructions': 'Practice mode — take as many attempts as you like. Answers shown immediately.',
            'test_type': 'PRACTICE',
            'exam_target': 'GENERAL',
            'difficulty_level': 'MIXED',
            'subject': subjects[subj_code],
            'batch': batch,
            'total_duration_minutes': 120,
            'start_datetime': now - timedelta(days=30),
            'end_datetime': now + timedelta(days=365),
            'positive_marks_per_question': Decimal('4'),
            'negative_marks_per_question': Decimal('0'),
            'max_attempts': 99,
            'shuffle_questions': True,
            'shuffle_options': True,
            'allow_review': True,
            'access_mode': 'OPEN',
            'result_display_mode': 'IMMEDIATE',
            'show_correct_answers': True,
            'show_explanations': True,
            'status': 'ACTIVE',
            'published_at': now - timedelta(days=30),
            'teacher': teacher,
        }
        questions = QUESTION_BANK[qbank_key]
        test = create_test_with_questions(test_data, questions)
        print(f"    ✓ PRACTICE: {test.title} ({test.total_questions}Q)")

# ============================================================
# 10. SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("  POPULATION COMPLETE — SUMMARY")
print("=" * 70)

test_count = Test.objects.filter(tenant=tenant).count()
q_count = Question.objects.filter(tenant=tenant).count()
attempt_count = TestAttempt.objects.filter(tenant=tenant).count()
student_count = Student.objects.filter(tenant=tenant).count()
teacher_count = Teacher.objects.filter(tenant=tenant).count()
batch_count = Batch.objects.filter(tenant=tenant).count()
live_count = Test.objects.filter(tenant=tenant, status='ACTIVE').count()
sched_count = Test.objects.filter(tenant=tenant, status='PUBLISHED').count()
comp_count = Test.objects.filter(tenant=tenant, status='COMPLETED').count()

print(f"""
  Academic Session : 2025-2026 (current)
  Subjects         : {Subject.objects.filter(tenant=tenant).count()}
  Chapters         : {Chapter.objects.filter(tenant=tenant).count()}
  Topics           : {Topic.objects.filter(tenant=tenant).count()}
  Batches          : {batch_count} (Class 9A, 9B, 10A, 10B, 11-JEE, 11-NEET, 12-JEE, 12-NEET)
  Teachers         : {teacher_count}
  Students         : {student_count} (10 per batch)

  Total Tests      : {test_count}
  Total Questions  : {q_count}
  ─────────────────────────
  🔴 LIVE NOW       : {live_count} exams (students can take RIGHT NOW)
  📅 Scheduled      : {sched_count} exams (upcoming)
  ✅ Completed      : {comp_count} exams (with results/grades)
  📝 Practice       : {Test.objects.filter(tenant=tenant, test_type='PRACTICE').count()} tests (unlimited attempts)
  ─────────────────────────
  Student Attempts : {attempt_count} (graded)

  LOGIN CREDENTIALS:
  ─────────────────
  Students : email pattern = firstname.lastnameN@lms.com / password = student123
  Teachers : email pattern = firstname.lastname@lms.com  / password = teacher123
  Admin    : Admin@lms.com / Admin@123
""")

print("Done! Students can now log in and take their live exams.")
