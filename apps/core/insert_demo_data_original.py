#!/usr/bin/env python
"""Insert medium-sized demo data for LMS"""
import psycopg2
from psycopg2 import sql
import uuid
from datetime import datetime, timedelta
import random

TENANT_ID = 'f883ed57-6f3a-40fa-b7f8-f0eebcd7e04c'
PWD_HASH = "pbkdf2_sha256$600000$sFGj3LiXISAA0j60UiVmqw$oYaczbFfPH06ho8c/xp7o3XcLrneA5zsQQDkG37EHo0="
PASSWORD_HASH = "pbkdf2_sha256$600000$8nefTaZhBKnDQUNJU0JA9f$9Pvjn6B5kape49PvznkQ3nUJrv3wF7XacJq6aI7wH5o="
SESSION_ID = '2b1d610e-028a-4ffa-adbe-97a6a3b19746'
LANG_EN = '60cbc76b-afdb-43c2-b4ca-82cf18093ba0'

conn = psycopg2.connect(dbname='LMS_PROD_DB', user='lms_app_user', password='LmsSecure@2024!', host='localhost')
conn.autocommit = False
cur = conn.cursor()

try:
    # 1. STATES (10 states)
    print("1. Inserting States...")
    states = [
        ('Uttar Pradesh', 'UP'), ('Maharashtra', 'MH'), ('Delhi', 'DL'), ('Tamil Nadu', 'TN'),
        ('Karnataka', 'KA'), ('Andhra Pradesh', 'AP'), ('West Bengal', 'WB'), ('Gujarat', 'GJ'),
        ('Rajasthan', 'RJ'), ('Bihar', 'BR')
    ]
    state_ids = {}
    for name, code in states:
        sid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO states(id, name, code) VALUES(%s, %s, %s) ON CONFLICT DO NOTHING",
            (sid, name, code)
        )
        state_ids[name] = sid
    conn.commit()
    print(f"   ✓ Inserted {len(states)} states")

    # 2. CITIES (15 cities)
    print("2. Inserting Cities...")
    cities_data = [
        ('Mumbai', 'Maharashtra'),
        ('Delhi', 'Delhi'),
        ('Bangalore', 'Karnataka'),
        ('Chennai', 'Tamil Nadu'),
        ('Lucknow', 'Uttar Pradesh'),
        ('Hyderabad', 'Andhra Pradesh'),
        ('Kolkata', 'West Bengal'),
        ('Pune', 'Maharashtra'),
        ('Ahmedabad', 'Gujarat'),
        ('Jaipur', 'Rajasthan'),
        ('Patna', 'Bihar'),
        ('Chandigarh', 'Delhi'),
        ('Varanasi', 'Uttar Pradesh'),
        ('Cochin', 'Tamil Nadu'),
        ('Nagpur', 'Maharashtra'),
    ]
    city_ids = {}
    for city_name, state_name in cities_data:
        cid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO cities(id, name, state_id) VALUES(%s, %s, %s) ON CONFLICT DO NOTHING",
            (cid, city_name, state_ids[state_name])
        )
        city_ids[city_name] = cid
    conn.commit()
    print(f"   ✓ Inserted {len(cities_data)} cities")

    # 3. RELIGIONS
    print("3. Inserting Religions...")
    religions = ['Hindu', 'Muslim', 'Christian', 'Sikh', 'Buddhist', 'Jain']
    religion_ids = {}
    for name in religions:
        rid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO religions(id, name, status) VALUES(%s, %s, %s) ON CONFLICT DO NOTHING",
            (rid, name, 'Y')
        )
        religion_ids[name] = rid
    conn.commit()
    print(f"   ✓ Inserted {len(religions)} religions")

    # 4. SCHOOLS (8 schools)
    print("4. Inserting Schools...")
    schools = [
        ('JNV Lucknow', 'Lucknow', 'JNV'),
        ('JNV Varanasi', 'Varanasi', 'JNV'),
        ('Delhi Public School', 'Delhi', 'CBSE'),
        ('Bangalore International School', 'Bangalore', 'CBSE'),
        ('Chennai High School', 'Chennai', 'State'),
        ('Pune Academy', 'Pune', 'CBSE'),
        ('Mumbai Central School', 'Mumbai', 'CBSE'),
        ('Rajkot Education Institute', 'Jaipur', 'State'),
    ]
    school_ids = {}
    for name, city_name, stype in schools:
        scid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO schools(id, name, city_name, school_type, status, created_at, tenant_id) VALUES(%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (scid, name, city_name, stype, 'Y', datetime.now(), TENANT_ID)
        )
        school_ids[name] = scid
    conn.commit()
    print(f"   ✓ Inserted {len(schools)} schools")

    # 5. GROUPS (4 groups)
    print("5. Inserting Groups...")
    groups = ['Science Stream', 'Commerce Stream', 'Foundation', 'Advanced']
    group_ids = {}
    for name in groups:
        gid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO groups(id, name, status, created_at, updated_at, meta_data, tenant_id) VALUES(%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (gid, name, True, datetime.now(), datetime.now(), '{}', TENANT_ID)
        )
        group_ids[name] = gid
    conn.commit()
    print(f"   ✓ Inserted {len(groups)} groups")

    # 6. SUBJECTS (5 subjects)
    print("6. Inserting Subjects...")
    subjects = [
        ('Physics', 'PHY', 'Classical and Modern Physics'),
        ('Chemistry', 'CHM', 'Organic and Inorganic Chemistry'),
        ('Mathematics', 'MTH', 'Algebra and Calculus'),
        ('Biology', 'BIO', 'Zoology and Botany'),
        ('English', 'ENG', 'English Language and Literature'),
    ]
    subject_ids = {}
    for name, code, desc in subjects:
        sid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO subjects(id, name, code, description, subject_type, status, display_order, created_at, updated_at, meta_data, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (sid, name, code, desc, 'core', 'active', len(subject_ids)+1, datetime.now(), datetime.now(), '{}', TENANT_ID)
        )
        subject_ids[name] = sid
    conn.commit()
    print(f"   ✓ Inserted {len(subjects)} subjects")

    # 7. BATCHES (5 batches)
    print("7. Inserting Batches...")
    batches = [
        ('JEE-2025-A', 'JEE 2025 Batch A', '12', 'JEE'),
        ('JEE-2025-B', 'JEE 2025 Batch B', '12', 'JEE'),
        ('NEET-2025', 'NEET 2025 Batch', '12', 'NEET'),
        ('Foundation-11', 'Foundation Class 11', '11', 'Board'),
        ('Advanced-12', 'Advanced Class 12', '12', 'Board'),
    ]
    batch_ids = {}
    today = datetime.now().date()
    for code, name, level, target in batches:
        bid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO batches(id, code, name, description, class_level, exam_target, max_students, start_date, end_date, status, created_at, updated_at, meta_data, session_id, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (bid, code, name, name, level, target, 60, today, today + timedelta(days=365), 'active', datetime.now(), datetime.now(), '{}', SESSION_ID, TENANT_ID)
        )
        batch_ids[code] = bid
    conn.commit()
    print(f"   ✓ Inserted {len(batches)} batches")

    # 8. CHAPTERS (10 chapters - 2 per subject for 5 subjects)
    print("8. Inserting Chapters...")
    chapters_data = [
        ('Mechanics', 'PHY', 'Physics', 1, subject_ids['Physics']),
        ('Thermodynamics', 'PHY', 'Physics', 2, subject_ids['Physics']),
        ('Organic Chemistry', 'CHM', 'Chemistry', 1, subject_ids['Chemistry']),
        ('Inorganic Chemistry', 'CHM', 'Chemistry', 2, subject_ids['Chemistry']),
        ('Algebra', 'MTH', 'Mathematics', 1, subject_ids['Mathematics']),
        ('Calculus', 'MTH', 'Mathematics', 2, subject_ids['Mathematics']),
        ('Zoology', 'BIO', 'Biology', 1, subject_ids['Biology']),
        ('Botany', 'BIO', 'Biology', 2, subject_ids['Biology']),
        ('Grammar', 'ENG', 'English', 1, subject_ids['English']),
        ('Literature', 'ENG', 'English', 2, subject_ids['English']),
    ]
    chapter_ids = {}
    for name, code, desc, order, subj_id in chapters_data:
        chid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO chapters(id, name, code, description, display_order, status, class_level, estimated_hours, created_at, updated_at, meta_data, subject_id, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (chid, name, code, desc, order, True, '12', 20, datetime.now(), datetime.now(), '{}', subj_id, TENANT_ID)
        )
        chapter_ids[name] = chid
    conn.commit()
    print(f"   ✓ Inserted {len(chapters_data)} chapters")

    # 9. TOPICS (20 topics - 2 per chapter)
    print("9. Inserting Topics...")
    topics_data = [
        ('Newton\'s Laws', 'Mechanics', 1),
        ('Friction', 'Mechanics', 2),
        ('Heat Transfer', 'Thermodynamics', 1),
        ('Entropy', 'Thermodynamics', 2),
        ('Hydrocarbons', 'Organic Chemistry', 1),
        ('Alcohols', 'Organic Chemistry', 2),
        ('Periodic Table', 'Inorganic Chemistry', 1),
        ('Bonding', 'Inorganic Chemistry', 2),
        ('Linear Equations', 'Algebra', 1),
        ('Quadratic Equations', 'Algebra', 2),
        ('Derivatives', 'Calculus', 1),
        ('Integration', 'Calculus', 2),
        ('Animal Kingdom', 'Zoology', 1),
        ('Human Physiology', 'Zoology', 2),
        ('Plant Physiology', 'Botany', 1),
        ('Plant Anatomy', 'Botany', 2),
        ('Verbs and Tenses', 'Grammar', 1),
        ('Sentence Structure', 'Grammar', 2),
        ('Shakespeare', 'Literature', 1),
        ('Modern Poetry', 'Literature', 2),
    ]
    topic_ids = {}
    for name, chapter_name, order in topics_data:
        tid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO topics(id, name, code, description, display_order, status, created_at, updated_at, meta_data, chapter_id, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (tid, name, f'{chapter_name[0:3].upper()}{order}', name, order, True, datetime.now(), datetime.now(), '{}', chapter_ids[chapter_name], TENANT_ID)
        )
        topic_ids[name] = tid
    conn.commit()
    print(f"   ✓ Inserted {len(topics_data)} topics")

    # 10. TEACHERS (5 new teachers)
    print("10. Inserting Teachers...")
    teachers = [
        ('Dr. Amit Verma', 'amit.verma@lms.com', '919876543210', 'Physics'),
        ('Mrs. Sunita Mathur', 'sunita.mathur@lms.com', '919876543211', 'Chemistry'),
        ('Mr. Ravi Shankar', 'ravi.shankar@lms.com', '919876543212', 'Mathematics'),
        ('Dr. Priya Singh', 'priya.singh@lms.com', '919876543213', 'Biology'),
        ('Ms. Anjali Sharma', 'anjali.sharma@lms.com', '919876543214', 'English'),
    ]
    teacher_ids = {}
    for i, (name, email, phone, subject) in enumerate(teachers, 1):
        tid = str(uuid.uuid4())
        fname, lname = name.split(' ', 1)
        cur.execute(
            "INSERT INTO teachers(id, email, phone, password_hash, force_password_change, mfa_enabled, mfa_enforced_by_admin, "
            "first_name, last_name, display_name, status, email_verified, phone_verified, created_at, updated_at, meta_data, "
            "teacher_code, subjects, specialization, certifications, youtube_channel_verified, can_create_streams, "
            "can_edit_student_profile, can_override_attendance, can_override_scores, city, state, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (tid, email, phone, PASSWORD_HASH, False, False, False, fname, lname, name, 'active', True, True,
             datetime.now(), datetime.now(), '{}', f'TCH00{i}', f'["{subject}"]', '[]', '[]', False, True, False, False, False,
             'Lucknow', 'Uttar Pradesh', TENANT_ID)
        )
        teacher_ids[subject] = tid
    conn.commit()
    print(f"   ✓ Inserted {len(teachers)} teachers")

    # 11. STUDENTS (20 students)
    print("11. Inserting Students...")
    first_names = ['Aarav', 'Priya', 'Vikram', 'Ananya', 'Rohan', 'Nisha', 'Arjun', 'Diya', 'Rahul', 'Pooja',
                   'Aditya', 'Shruti', 'Karan', 'Zara', 'Sanjay', 'Riya', 'Nikhil', 'Kavya', 'Varun', 'Shreya']
    last_names = ['Sharma', 'Patel', 'Singh', 'Gupta', 'Khan', 'Verma', 'Rao', 'Nair', 'Joshi', 'Desai',
                  'Kulkarni', 'Srivastava', 'Bhat', 'Iyer', 'Reddy', 'Das', 'Mishra', 'Saxena', 'Chopra', 'Bansal']
    student_ids = []
    for i in range(20):
        fname = first_names[i]
        lname = last_names[i]
        email = f"{fname.lower()}.{lname.lower()}@lms.com"
        phone = f'9198765432{i:02d}'
        
        sid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO students(id, email, phone, password_hash, force_password_change, mfa_enabled, mfa_enforced_by_admin, "
            "first_name, last_name, display_name, status, email_verified, phone_verified, created_at, updated_at, meta_data, "
            "student_code, class_level, exam_target, medium, city, state, pin_code, country, gender, "
            "subscription_type, fee_status, preferred_language, notification_email, notification_sms, notification_push, "
            "notification_whatsapp, profile_editable_by_self, batch_id, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (sid, email, phone, PASSWORD_HASH, False, False, False, fname, lname, f"{fname} {lname}", 'active', True, True,
             datetime.now(), datetime.now(), '{}', f'STU{i+1:03d}', '12', 'JEE' if i % 2 == 0 else 'NEET', 'English',
             random.choice(list(city_ids.keys())), 'Uttar Pradesh', '226001', 'India', random.choice(['male', 'female']),
             'premium', 'paid', 'en', True, True, True, False, True, None, TENANT_ID)
        )
        student_ids.append(sid)
    conn.commit()
    print(f"   ✓ Inserted 20 students")

    # 12. BATCH_STUDENTS (link students to batches)
    print("12. Linking Students to Batches...")
    # Get actual student IDs from database
    cur.execute("SELECT id FROM students WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 20", (TENANT_ID,))
    actual_students = [row[0] for row in cur.fetchall()]
    # Get actual batches from database  
    cur.execute("SELECT id FROM batches WHERE tenant_id=%s", (TENANT_ID,))
    existing_batches = [row[0] for row in cur.fetchall()]
    
    if not actual_students:
        actual_students = student_ids
    
    if actual_students and existing_batches:
        for i, sid in enumerate(actual_students):
            bid = existing_batches[i % len(existing_batches)]
            bsid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO batch_students(id, batch_id, student_id, enrolled_at, is_active, tenant_id) "
                "VALUES(%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (bsid, bid, sid, datetime.now(), True, TENANT_ID)
            )
        conn.commit()
        print(f"   ✓ Linked {len(actual_students)} students to batches")
    else:
        print("   ! No batches or students found")

    # 13. BATCH_TEACHERS (link teachers to batches and subjects)
    print("13. Linking Teachers to Batches...")
    cur.execute("SELECT id FROM batches WHERE tenant_id=%s", (TENANT_ID,))
    existing_batches = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM teachers WHERE tenant_id=%s", (TENANT_ID,))
    actual_teachers = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM subjects WHERE tenant_id=%s", (TENANT_ID,))
    actual_subjects = [row[0] for row in cur.fetchall()]
    
    if existing_batches and actual_teachers and actual_subjects:
        for t_idx, tid in enumerate(actual_teachers):
            subj_id = actual_subjects[t_idx % len(actual_subjects)]
            for bid in existing_batches:
                btid = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO batch_teachers(id, batch_id, teacher_id, subject_id, is_primary, assigned_at, tenant_id) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (btid, bid, tid, subj_id, True, datetime.now(), TENANT_ID)
                )
        conn.commit()
        print(f"   ✓ Linked teachers to batches")
    else:
        print("   ! No batches, teachers, or subjects found")

    # 14. TESTS (8 tests)
    print("14. Inserting Tests...")
    cur.execute("SELECT id FROM batches WHERE tenant_id=%s", (TENANT_ID,))
    existing_batches = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM subjects WHERE tenant_id=%s", (TENANT_ID,))
    actual_subjects = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM teachers WHERE tenant_id=%s", (TENANT_ID,))
    actual_teachers = [row[0] for row in cur.fetchall()]
    
    tests = [
        ('Physics Mock 1', 'Practice test on Mechanics', 'JEE', 'medium', 60, 100),
        ('Chemistry Chapter Test', 'Organic Chemistry chapter test', 'JEE', 'medium', 45, 75),
        ('Math Full Length', 'Complete algebra and calculus', 'JEE', 'hard', 120, 200),
        ('Biology Practice', 'NEET style biology questions', 'NEET', 'medium', 60, 100),
        ('Physics Chapter Quiz', 'Quick quiz on Thermodynamics', 'JEE', 'easy', 30, 50),
        ('Chemistry Mock 2', 'Full chemistry mock test', 'JEE', 'hard', 90, 150),
        ('Math Chapter Test', 'Calculus chapter test', 'JEE', 'medium', 45, 75),
        ('NEET Full Length', 'Complete NEET style test', 'NEET', 'hard', 180, 360),
    ]
    test_ids = []
    if actual_teachers and actual_subjects and existing_batches:
        for i, (title, desc, target, diff, duration, marks) in enumerate(tests, 1):
            tid = str(uuid.uuid4())
            passing_marks = marks * 0.4
            bid = existing_batches[i % len(existing_batches)]
            cur.execute(
                "INSERT INTO tests(id, test_code, title, description, instructions, test_type, exam_target, difficulty_level, "
                "total_duration_minutes, start_datetime, end_datetime, late_submission_allowed, late_submission_penalty_percent, "
                "buffer_time_minutes, show_timer, total_marks, passing_marks, passing_percent, positive_marks_per_question, "
                "negative_marks_per_question, partial_marking, max_attempts, shuffle_questions, shuffle_options, allow_review, "
                "allow_backward, access_mode, result_display_mode, show_correct_answers, show_explanations, show_rank, show_percentile, "
                "enable_proctoring, prevent_tab_switch, max_tab_switches, prevent_copy_paste, prevent_screenshot, webcam_required, "
                "full_screen_required, status, is_deleted, total_questions, created_at, updated_at, subject_id, teacher_id, batch_id, tenant_id) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (tid, f'TST{i:03d}', title, desc, 'Answer all questions carefully.', 'mock',
                 target, diff, duration, datetime.now(), datetime.now() + timedelta(days=30), False, 0, 5, True,
                 marks, passing_marks, 40, 4, 1, False, 2, True, True, True, True, 'batch', 'after_submit',
                 True, True, True, True, False, True, 3, True, False, False, False, 'published', False, 30,
                 datetime.now(), datetime.now(), actual_subjects[i % len(actual_subjects)],
                 actual_teachers[i % len(actual_teachers)], bid, TENANT_ID)
            )
            test_ids.append(tid)
        conn.commit()
        print(f"   ✓ Inserted {len(tests)} tests")
    else:
        print("   ! No teachers, subjects, or batches found")

    # 15. QUESTIONS (32 questions - 4 per test for first 8 tests)
    print("15. Inserting Questions...")
    cur.execute("SELECT id FROM tests WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 8", (TENANT_ID,))
    existing_tests = [row[0] for row in cur.fetchall()]
    
    questions = [
        ('What is Newton\'s first law?', 'An object in motion stays in motion', 'Force can change motion', 'Energy is conserved', 'Momentum is lost', 'A'),
        ('Define velocity', 'Speed with direction', 'Only magnitude', 'Acceleration rate', 'Distance covered', 'A'),
        ('What is kinetic energy?', '0.5*m*v^2', 'm*g*h', 'F*d', 'p/t', 'A'),
        ('State Ohm\'s law', 'V=I*R', 'F=m*a', 'E=m*c^2', 'P=V*I', 'A'),
    ]
    q_offset = 0
    if existing_tests:
        for test_idx, tid in enumerate(existing_tests[:8]):
            for q_idx in range(4):
                qid = str(uuid.uuid4())
                q = questions[q_offset + q_idx]
                cur.execute(
                    "INSERT INTO questions(id, question_code, question_text, question_type, difficulty, "
                    "option_a, option_b, option_c, option_d, correct_answer, answer_explanation, "
                    "positive_marks, negative_marks, tags, question_order, total_attempts, correct_attempts, "
                    "is_active, is_deleted, created_at, updated_at, test_id, subject_id, tenant_id) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (qid, f'QST{test_idx}{q_idx}', q[0], 'mcq', 'medium', q[1], q[2], q[3], q[4], q[5],
                     'This is the correct explanation.', 4, 1, '[]', q_idx + 1, 0, 0, True, False,
                     datetime.now(), datetime.now(), tid, list(subject_ids.values())[test_idx % len(subject_ids)], TENANT_ID)
                )
            q_offset = (q_offset + 4) % len(questions)
        conn.commit()
        print(f"   ✓ Inserted 32 questions")
    else:
        print("   ! No tests found")

    # 16. TEST_ATTEMPTS (30 attempts)
    print("16. Inserting Test Attempts...")
    cur.execute("SELECT id FROM tests WHERE tenant_id=%s", (TENANT_ID,))
    existing_tests = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM students WHERE tenant_id=%s", (TENANT_ID,))
    actual_students = [row[0] for row in cur.fetchall()]
    
    if existing_tests and actual_students:
        for i in range(min(30, len(actual_students) * len(existing_tests))):
            sid = actual_students[i % len(actual_students)]
            tid = existing_tests[i % len(existing_tests)]
            
            taid = str(uuid.uuid4())
            correct = random.randint(10, 25)
            incorrect = random.randint(5, 15)
            raw_score = correct * 4 - incorrect * 1
            total_marks = 100
            percentage = (raw_score / total_marks) * 100
            
            cur.execute(
                "INSERT INTO test_attempts(id, attempt_number, started_at, submitted_at, time_taken_seconds, "
                "total_questions, attempted, correct, incorrect, skipped, marked_for_review, raw_score, total_marks, "
                "percentage, result, section_scores, status, tab_switch_count, copy_paste_attempts, proctoring_violations, "
                "auto_terminated, time_limit_reached, student_id, test_id, tenant_id) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (taid, 1, datetime.now() - timedelta(days=random.randint(0, 30)), datetime.now() - timedelta(days=random.randint(0, 30)),
                 random.randint(1800, 3600), 30, correct + incorrect, correct, incorrect, 30 - correct - incorrect, 0,
                 raw_score, total_marks, percentage, 'pass' if percentage >= 40 else 'fail', '[]', 'completed',
                 random.randint(0, 3), random.randint(0, 2), '[]', False, False, sid, tid, TENANT_ID)
            )
        conn.commit()
        print(f"   ✓ Inserted {min(30, len(actual_students) * len(existing_tests))} test attempts")
    else:
        print("   ! No tests or students found")

    # 17. ATTENDANCE (50 records)
    print("17. Inserting Attendance...")
    cur.execute("SELECT id FROM batches WHERE tenant_id=%s", (TENANT_ID,))
    existing_batches = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM students WHERE tenant_id=%s", (TENANT_ID,))
    actual_students = [row[0] for row in cur.fetchall()]
    
    if actual_students and existing_batches:
        for i in range(min(50, len(actual_students) * 5)):
            sid = actual_students[i % len(actual_students)]
            att_date = (datetime.now() - timedelta(days=random.randint(1, 30))).date()
            
            attid = str(uuid.uuid4())
            bid = existing_batches[i % len(existing_batches)]
            cur.execute(
                "INSERT INTO attendance(id, user_type, user_id, attendance_date, month, year, status, check_in_time, "
                "source, marked_at, is_corrected, academic_session_id, batch_id, tenant_id) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (attid, 'student', sid, att_date, att_date.month, att_date.year,
                 random.choice(['present', 'absent', 'late']), None, 'manual', datetime.now(), False,
                 SESSION_ID, bid, TENANT_ID)
            )
        conn.commit()
        print(f"   ✓ Inserted {min(50, len(actual_students) * 5)} attendance records")
    else:
        print("   ! No students or batches found")

    # 18. STUDY_MATERIALS (8 materials)
    print("18. Inserting Study Materials...")
    materials = [
        ('Physics Mechanics Complete Notes', 'Comprehensive notes on mechanics', 'pdf'),
        ('Chemistry Organic Reactions Video', 'Video lecture on organic reactions', 'video'),
        ('Mathematics Problem Solving', 'Solution set for algebra problems', 'pdf'),
        ('Biology Diagrams and Charts', 'Visual learning materials', 'presentation'),
        ('English Grammar Guide', 'Complete grammar reference', 'pdf'),
        ('Physics Thermodynamics Notes', 'Detailed thermodynamics concepts', 'pdf'),
        ('Chemistry Lab Procedures Video', 'Practical lab techniques', 'video'),
        ('Mathematics Calculus Examples', 'Solved calculus problems', 'pdf'),
    ]
    for name, desc, mtype in materials:
        mid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO study_materials(id, material_code, title, description, material_type, file_url, "
            "tags, target_audience, difficulty_level, is_free, is_downloadable, requires_enrollment, "
            "allowed_batches, view_count, download_count, rating, rating_count, is_published, is_active, "
            "is_deleted, created_at, updated_at, subject_id, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (mid, f'MAT{len(materials):03d}', name, desc, mtype, '/media/materials/sample.pdf', '[]', 'all',
             'medium', False, True, True, '[]', random.randint(50, 500), random.randint(10, 200),
             random.uniform(3.5, 5.0), random.randint(5, 50), True, True, False, datetime.now(), datetime.now(),
             list(subject_ids.values())[random.randint(0, len(subject_ids)-1)], TENANT_ID)
        )
    conn.commit()
    print(f"   ✓ Inserted 8 study materials")

    # 19. ANNOUNCEMENTS (5 announcements)
    print("19. Inserting Announcements...")
    announcements = [
        ('JEE Exam Date Announced', 'The JEE Main exam will be held on April 15-16, 2025', 'exam'),
        ('New Study Materials Available', 'Download the latest physics notes and video lectures', 'general'),
        ('Class Schedule Updated', 'Check your dashboard for the revised class timings', 'schedule'),
        ('Scholarship Results Out', 'Merit-based scholarships have been awarded. Check portal.', 'general'),
        ('Monthly Test Reminder', 'Monthly tests start from next Monday. Be prepared!', 'exam'),
    ]
    admin_id = 'c1e84db8-b496-43f6-a96d-7b08054a6acb'
    for i, (title, content, atype) in enumerate(announcements):
        aid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO announcements(id, title, content, announcement_type, target_audience, target_batches, "
            "target_user_ids, is_pinned, is_published, published_at, created_by_id, created_by_type, created_by_name, "
            "attachments, view_count, acknowledgement_required, created_at, updated_at, is_deleted, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (aid, title, content, atype, 'all', '[]', '[]', i < 2, True, datetime.now(),
             admin_id, 'admin', 'Admin', '[]', random.randint(10, 100), False, datetime.now(), datetime.now(), False, TENANT_ID)
        )
    conn.commit()
    print(f"   ✓ Inserted 5 announcements")

    # 20. ENQUIRY_FORMS (8 enquiries)
    print("20. Inserting Enquiry Forms...")
    for i in range(8):
        eid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO enquiry_forms(id, name, email, phone, subject, message, source, status, created_at, updated_at, tenant_id) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (eid, f'Student {i+1}', f'student{i}@email.com', f'98765432{i:02d}', 'Course Inquiry',
             'I want to know more about the JEE preparation program.', 'website', 'new', datetime.now(), datetime.now(), TENANT_ID)
        )
    conn.commit()
    print(f"   ✓ Inserted 8 enquiry forms")

    # 21. SCHOLARSHIPS (SKIPPED - schema mismatch)
    print("21. Skipping Scholarships...")

    # 22. FOUNDER_INFO (SKIPPED)
    print("22. Skipping Founder Info...")
    
    # 23. TOPPER_STUDENTS (SKIPPED) 
    print("23. Skipping Topper Students...")

    conn.commit()
    print("\n✅ Demo data insertion completed successfully!")
    
    # Print summary
    print("\n📊 Data Summary:")
    cur.execute("SELECT COUNT(*) FROM states")
    print(f"   States: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM cities")
    print(f"   Cities: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM students WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Students: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM teachers WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Teachers: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM batches WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Batches: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM tests WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Tests: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM questions WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Questions: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM test_attempts WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Test Attempts: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM attendance WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Attendance Records: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM announcements WHERE tenant_id=%s", (TENANT_ID,))
    print(f"   Announcements: {cur.fetchone()[0]}")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    cur.close()
    conn.close()
