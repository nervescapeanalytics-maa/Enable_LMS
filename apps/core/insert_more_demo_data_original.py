#!/usr/bin/env python
"""Insert MORE demo data into LMS PostgreSQL database."""
import psycopg2
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
    # ── Helper: fetch existing IDs ──────────────────────────────────────
    def fetch_ids(table, extra_where=""):
        q = f"SELECT id FROM {table} WHERE tenant_id=%s {extra_where}"
        cur.execute(q, (TENANT_ID,))
        return [r[0] for r in cur.fetchall()]

    # ── 1. Ensure SUBJECTS exist ────────────────────────────────────────
    print("1. Ensuring Subjects exist...")
    subjects_spec = [
        ('Physics', 'PHY', 'Classical and Modern Physics', 'core'),
        ('Chemistry', 'CHM', 'Organic and Inorganic Chemistry', 'core'),
        ('Mathematics', 'MTH', 'Algebra and Calculus', 'core'),
        ('Biology', 'BIO', 'Zoology and Botany', 'core'),
        ('English', 'ENG', 'English Language and Literature', 'core'),
    ]
    for i, (name, code, desc, stype) in enumerate(subjects_spec, 1):
        cur.execute(
            "INSERT INTO subjects(id, name, code, description, subject_type, status, display_order, "
            "created_at, updated_at, meta_data, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (str(uuid.uuid4()), name, code, desc, stype, 'active', i,
             datetime.now(), datetime.now(), '{}', TENANT_ID)
        )
    conn.commit()

    # Map subject names → IDs from DB
    cur.execute("SELECT id, name FROM subjects WHERE tenant_id=%s", (TENANT_ID,))
    subject_map = {r[1]: str(r[0]) for r in cur.fetchall()}
    print(f"   ✓ Subjects ready: {list(subject_map.keys())}")

    # ── 2. Insert 5 NEW batches ─────────────────────────────────────────
    print("2. Inserting 5 new Batches...")
    today = datetime.now().date()
    new_batches = [
        ('JEE-2025-C', 'JEE 2025 Batch C', '12', 'JEE'),
        ('JEE-2025-D', 'JEE 2025 Batch D', '12', 'JEE'),
        ('NEET-2025-A', 'NEET 2025 Batch A', '12', 'NEET'),
        ('NEET-2025-B', 'NEET 2025 Batch B', '12', 'NEET'),
        ('FOUND-2025', 'Foundation Batch 2025', '11', 'Board'),
    ]
    new_batch_ids = []
    for code, name, level, target in new_batches:
        bid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO batches(id, code, name, description, class_level, exam_target, max_students, "
            "start_date, end_date, status, created_at, updated_at, meta_data, session_id, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (bid, code, name, name, level, target, 60,
             today, today + timedelta(days=365), 'active',
             datetime.now(), datetime.now(), '{}', SESSION_ID, TENANT_ID)
        )
        new_batch_ids.append(bid)
    conn.commit()
    print(f"   ✓ Inserted {len(new_batches)} batches")

    # Refresh all batch IDs
    all_batch_ids = fetch_ids('batches')

    # ── 3. Insert 15 MORE teachers ──────────────────────────────────────
    print("3. Inserting 15 new Teachers...")
    new_teachers = [
        ('Dr. Suresh', 'Kumar', 'suresh.kumar@lms.com', '919800000001', 'Physics', 'M.Sc Physics, PhD Mechanics', 'Professor', 8),
        ('Mrs. Lakshmi', 'Iyer', 'lakshmi.iyer@lms.com', '919800000002', 'Chemistry', 'M.Sc Organic Chemistry', 'Senior Lecturer', 12),
        ('Mr. Rajesh', 'Tripathi', 'rajesh.tripathi@lms.com', '919800000003', 'Mathematics', 'M.Sc Mathematics', 'Associate Professor', 10),
        ('Dr. Meena', 'Agarwal', 'meena.agarwal@lms.com', '919800000004', 'Biology', 'PhD Zoology', 'Professor', 15),
        ('Mr. Anil', 'Pandey', 'anil.pandey@lms.com', '919800000005', 'Physics', 'M.Tech Applied Physics', 'Lecturer', 6),
        ('Mrs. Geeta', 'Mishra', 'geeta.mishra@lms.com', '919800000006', 'Chemistry', 'M.Sc Inorganic Chemistry', 'Lecturer', 7),
        ('Dr. Prakash', 'Jha', 'prakash.jha@lms.com', '919800000007', 'Mathematics', 'PhD Applied Mathematics', 'Professor', 20),
        ('Ms. Deepa', 'Nair', 'deepa.nair@lms.com', '919800000008', 'Biology', 'M.Sc Botany', 'Senior Lecturer', 9),
        ('Mr. Vivek', 'Shukla', 'vivek.shukla@lms.com', '919800000009', 'Physics', 'M.Sc Nuclear Physics', 'Associate Professor', 11),
        ('Mrs. Shalini', 'Dubey', 'shalini.dubey@lms.com', '919800000010', 'Chemistry', 'M.Sc Physical Chemistry', 'Lecturer', 5),
        ('Dr. Ramesh', 'Yadav', 'ramesh.yadav@lms.com', '919800000011', 'Mathematics', 'PhD Statistics', 'Professor', 18),
        ('Ms. Pallavi', 'Saxena', 'pallavi.saxena@lms.com', '919800000012', 'Biology', 'M.Sc Genetics', 'Lecturer', 4),
        ('Mr. Manoj', 'Tiwari', 'manoj.tiwari@lms.com', '919800000013', 'English', 'M.A English Literature', 'Senior Lecturer', 13),
        ('Dr. Kavita', 'Reddy', 'kavita.reddy@lms.com', '919800000014', 'Physics', 'PhD Quantum Mechanics', 'Professor', 16),
        ('Mr. Santosh', 'Pillai', 'santosh.pillai@lms.com', '919800000015', 'Mathematics', 'M.Sc Pure Mathematics', 'Lecturer', 3),
    ]
    new_teacher_ids = []
    cities_list = ['Lucknow', 'Varanasi', 'Delhi', 'Mumbai', 'Patna', 'Jaipur', 'Bangalore', 'Chennai']
    states_list = ['Uttar Pradesh', 'Uttar Pradesh', 'Delhi', 'Maharashtra', 'Bihar', 'Rajasthan', 'Karnataka', 'Tamil Nadu']
    for i, (fname, lname, email, phone, subj, qual, desig, exp_yrs) in enumerate(new_teachers, 1):
        tid = str(uuid.uuid4())
        ci = i % len(cities_list)
        cur.execute(
            "INSERT INTO teachers(id, email, phone, password_hash, force_password_change, mfa_enabled, mfa_enforced_by_admin, "
            "first_name, last_name, display_name, status, email_verified, phone_verified, "
            "created_at, updated_at, meta_data, teacher_code, subjects, specialization, certifications, "
            "qualification, highest_degree, experience_years, designation, "
            "youtube_channel_verified, can_create_streams, can_edit_student_profile, "
            "can_override_attendance, can_override_scores, city, state, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (tid, email, phone, PASSWORD_HASH, False, False, False,
             fname, lname, f'{fname} {lname}', 'active', True, True,
             datetime.now(), datetime.now(), '{}',
             f'TCH{100+i:03d}', f'["{subj}"]', '[]', '[]',
             qual, qual.split()[0], exp_yrs, desig,
             False, True, False, False, False,
             cities_list[ci], states_list[ci], TENANT_ID)
        )
        new_teacher_ids.append(tid)
    conn.commit()
    print(f"   ✓ Inserted {len(new_teachers)} teachers")

    # ── 4. Insert 50 MORE students ──────────────────────────────────────
    print("4. Inserting 50 new Students...")
    first_names_m = [
        'Abhishek', 'Ajay', 'Akash', 'Amit', 'Ankur', 'Ashish', 'Deepak', 'Gaurav',
        'Harsh', 'Hemant', 'Jayant', 'Kunal', 'Manish', 'Mohit', 'Naveen',
        'Pankaj', 'Pranav', 'Rajat', 'Sachin', 'Saurabh', 'Shivam', 'Sumit',
        'Tushar', 'Utkarsh', 'Yash',
    ]
    first_names_f = [
        'Aditi', 'Ankita', 'Bhavna', 'Chhavi', 'Divya', 'Esha', 'Garima',
        'Harshita', 'Isha', 'Jyoti', 'Komal', 'Lakshmi', 'Megha', 'Neha',
        'Pallavi', 'Rashmi', 'Sakshi', 'Tanvi', 'Uma', 'Vandana',
        'Wriddhika', 'Yamini', 'Zoya', 'Swati', 'Preeti',
    ]
    last_names_pool = [
        'Sharma', 'Verma', 'Singh', 'Gupta', 'Yadav', 'Pandey', 'Mishra',
        'Tiwari', 'Dubey', 'Srivastava', 'Chauhan', 'Joshi', 'Agarwal',
        'Patel', 'Reddy', 'Nair', 'Saxena', 'Tripathi', 'Kulkarni', 'Bhat',
        'Deshmukh', 'Iyer', 'Pillai', 'Das', 'Bansal',
    ]
    student_cities = ['Lucknow', 'Varanasi', 'Delhi', 'Mumbai', 'Patna', 'Jaipur',
                      'Bangalore', 'Chennai', 'Pune', 'Kolkata', 'Hyderabad', 'Ahmedabad']
    student_states = ['Uttar Pradesh', 'Uttar Pradesh', 'Delhi', 'Maharashtra', 'Bihar',
                      'Rajasthan', 'Karnataka', 'Tamil Nadu', 'Maharashtra', 'West Bengal',
                      'Andhra Pradesh', 'Gujarat']
    school_names = ['JNV Lucknow', 'JNV Varanasi', 'JNV Patna', 'JNV Jaipur',
                    'ENF Academy Delhi', 'ENF Academy Mumbai', 'ENF Foundation School',
                    'Kendriya Vidyalaya', 'DPS Lucknow', 'DPS Varanasi']
    exam_targets = ['JEE', 'NEET', 'JEE', 'NEET', 'Board']

    new_student_ids = []
    for i in range(50):
        if i < 25:
            fname = first_names_m[i % len(first_names_m)]
            gender = 'male'
        else:
            fname = first_names_f[(i - 25) % len(first_names_f)]
            gender = 'female'
        lname = last_names_pool[i % len(last_names_pool)]
        email = f"{fname.lower()}.{lname.lower()}{i}@lms.com"
        phone = f'9199000{i:04d}'
        ci = i % len(student_cities)
        si = i % len(school_names)
        et = exam_targets[i % len(exam_targets)]
        class_lvl = '11' if et == 'Board' else '12'
        dob = datetime(2006, 1, 1) + timedelta(days=random.randint(0, 730))

        sid = str(uuid.uuid4())
        bid = all_batch_ids[i % len(all_batch_ids)] if all_batch_ids else None
        cur.execute(
            "INSERT INTO students(id, email, phone, password_hash, force_password_change, mfa_enabled, mfa_enforced_by_admin, "
            "first_name, last_name, display_name, status, email_verified, phone_verified, "
            "created_at, updated_at, meta_data, student_code, class_level, exam_target, medium, "
            "school_name, city, state, pin_code, country, gender, date_of_birth, "
            "parent_name, parent_phone, parent_relation, "
            "subscription_type, fee_status, preferred_language, "
            "notification_email, notification_sms, notification_push, notification_whatsapp, "
            "profile_editable_by_self, batch_id, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (sid, email, phone, PASSWORD_HASH, False, False, False,
             fname, lname, f'{fname} {lname}', 'active', True, True,
             datetime.now(), datetime.now(), '{}',
             f'STU{100+i:03d}', class_lvl, et, 'English',
             school_names[si],
             student_cities[ci], student_states[ci], f'2260{i%100:02d}', 'India', gender,
             dob.date(),
             f'Mr. {lname}', f'9198800{i:04d}', random.choice(['father', 'mother']),
             random.choice(['premium', 'basic', 'free']),
             random.choice(['paid', 'pending', 'partial']),
             'en', True, True, True, False, True, bid, TENANT_ID)
        )
        new_student_ids.append(sid)
    conn.commit()
    print(f"   ✓ Inserted 50 students")

    # ── 5. Link new students to batches (batch_students) ────────────────
    print("5. Linking new students to batches...")
    # Fetch actual student IDs from DB (the ones we just inserted)
    cur.execute("SELECT id FROM students WHERE tenant_id=%s AND student_code LIKE 'STU1%%' ORDER BY student_code", (TENANT_ID,))
    actual_new_student_ids = [str(r[0]) for r in cur.fetchall()]
    if all_batch_ids and actual_new_student_ids:
        linked = 0
        for i, sid in enumerate(actual_new_student_ids):
            bid = all_batch_ids[i % len(all_batch_ids)]
            bsid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO batch_students(id, batch_id, student_id, enrolled_at, is_active, tenant_id) "
                "VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (bsid, bid, sid, datetime.now(), True, TENANT_ID)
            )
            linked += 1
        conn.commit()
        print(f"   ✓ Linked {linked} students to batches")
    # Update new_student_ids to use actual DB IDs
    new_student_ids = actual_new_student_ids

    # ── 6. Link new teachers to batches (batch_teachers) ────────────────
    print("6. Linking new teachers to batches...")
    # Fetch actual new teacher IDs from DB
    cur.execute("SELECT id FROM teachers WHERE tenant_id=%s AND teacher_code LIKE 'TCH1%%' ORDER BY teacher_code", (TENANT_ID,))
    actual_new_teacher_ids = [str(r[0]) for r in cur.fetchall()]
    all_teacher_ids = fetch_ids('teachers')
    all_subject_ids = fetch_ids('subjects')
    if all_batch_ids and actual_new_teacher_ids and all_subject_ids:
        for t_idx, tid in enumerate(actual_new_teacher_ids):
            subj_id = all_subject_ids[t_idx % len(all_subject_ids)]
            for bid in all_batch_ids:
                btid = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO batch_teachers(id, batch_id, teacher_id, subject_id, is_primary, assigned_at, tenant_id) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (btid, bid, tid, subj_id, t_idx < 5, datetime.now(), TENANT_ID)
                )
        conn.commit()
        print(f"   ✓ Linked {len(actual_new_teacher_ids)} teachers to batches")

    # ── 7. Insert 15 MORE announcements ─────────────────────────────────
    print("7. Inserting 15 more Announcements...")
    admin_id = 'c1e84db8-b496-43f6-a96d-7b08054a6acb'
    extra_announcements = [
        ('NEET 2025 Registration Open', 'Register for NEET 2025 before the deadline. Visit the portal for details.', 'exam'),
        ('Physics Lab Session Scheduled', 'Hands-on physics lab sessions will begin from next week for all JEE batches.', 'schedule'),
        ('Holiday Notice - Republic Day', 'Institute will remain closed on 26th January. Online classes continue.', 'general'),
        ('Parent-Teacher Meeting', 'PTM scheduled for 15th February 2025. All parents are requested to attend.', 'general'),
        ('New Chemistry Video Lectures', 'Organic Chemistry video lecture series by Dr. Lakshmi Iyer is now available.', 'general'),
        ('Weekly Test Results Published', 'Check your results for Week 12 tests on the student dashboard.', 'exam'),
        ('Scholarship Exam Registration', 'ENF Merit Scholarship exam registration is now open. Apply before March 1st.', 'general'),
        ('Library Timing Extended', 'Library will now be open from 7 AM to 10 PM on weekdays.', 'schedule'),
        ('JEE Mock Test Series Launch', 'A new 10-part JEE mock test series has been launched. Start practicing now!', 'exam'),
        ('Biology Field Trip', 'Class 12 NEET students will go on a field trip to the Botanical Garden on March 5th.', 'schedule'),
        ('Fee Payment Reminder', 'Students with pending fees are requested to clear dues by February 28th.', 'general'),
        ('Summer Batch Admissions Open', 'Admissions for Summer Foundation Batch 2025 are now open.', 'general'),
        ('Mathematics Olympiad Selections', 'Top 10 students from Math batch will represent the institute at the State Olympiad.', 'exam'),
        ('Yoga and Meditation Session', 'Stress management yoga session on every Saturday at 6 AM in the auditorium.', 'general'),
        ('Campus Wi-Fi Upgraded', 'High-speed internet is now available in all classrooms and study halls.', 'general'),
    ]
    for i, (title, content, atype) in enumerate(extra_announcements):
        aid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO announcements(id, title, content, announcement_type, target_audience, target_batches, "
            "target_user_ids, is_pinned, is_published, published_at, created_by_id, created_by_type, created_by_name, "
            "attachments, view_count, acknowledgement_required, created_at, updated_at, is_deleted, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (aid, title, content, atype, 'all', '[]', '[]',
             i < 3, True, datetime.now() - timedelta(days=random.randint(0, 30)),
             admin_id, 'admin', 'Admin', '[]', random.randint(20, 200),
             False, datetime.now(), datetime.now(), False, TENANT_ID)
        )
    conn.commit()
    print(f"   ✓ Inserted {len(extra_announcements)} announcements")

    # ── 8. Insert 10 enquiry_forms entries ──────────────────────────────
    print("8. Inserting 10 enquiry forms...")
    enquiries = [
        ('Raghav Mehra', 'raghav.mehra@gmail.com', '9876500001', 'JEE Coaching',
         'I am looking for JEE coaching classes for my son studying in class 11.', 'website', 'new'),
        ('Sunita Devi', 'sunita.devi@yahoo.com', '9876500002', 'NEET Prep',
         'My daughter wants to join NEET preparation batch. Please share fee details.', 'referral', 'new'),
        ('Arun Prakash', 'arun.prakash@hotmail.com', '9876500003', 'Fee Info',
         'Kindly share the detailed fee structure for JEE 2025 batches.', 'website', 'contacted'),
        ('Kavita Sharma', 'kavita.s@gmail.com', '9876500004', 'Scholarship',
         'Are there any scholarships available for meritorious students from rural areas?', 'walk-in', 'new'),
        ('Manoj Kumar', 'manoj.k@gmail.com', '9876500005', 'Hostel',
         'Does the institute provide hostel facility for outstation students?', 'phone', 'contacted'),
        ('Priyanka Jain', 'priyanka.j@outlook.com', '9876500006', 'Foundation',
         'I want to enroll my child in the foundation course for class 9. Please guide.', 'website', 'new'),
        ('Dheeraj Singh', 'dheeraj.s@gmail.com', '9876500007', 'Duration',
         'What is the duration and timing for the NEET crash course?', 'website', 'contacted'),
        ('Neelam Gupta', 'neelam.g@yahoo.com', '9876500008', 'Online',
         'Are online classes available? We are based in a remote area with limited access.', 'website', 'new'),
        ('Vikrant Chauhan', 'vikrant.c@gmail.com', '9876500009', 'Demo Class',
         'Can my child attend a demo class before enrollment? Please schedule one.', 'referral', 'contacted'),
        ('Shobha Rani', 'shobha.r@gmail.com', '9876500010', 'Results',
         'What is the selection rate of your students in JEE Advanced last 3 years?', 'website', 'new'),
    ]
    for name, email, phone, subj, msg, source, status in enquiries:
        eid = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO enquiry_forms(id, name, email, phone, subject, message, source, status, "
            "created_at, updated_at, tenant_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (eid, name, email, phone, subj, msg, source, status,
             datetime.now() - timedelta(days=random.randint(0, 45)),
             datetime.now(), TENANT_ID)
        )
    conn.commit()
    print(f"   ✓ Inserted {len(enquiries)} enquiry forms")

    # ── 9. Insert more test attempts for new students ───────────────────
    print("9. Inserting more test attempts for new students...")
    existing_tests = fetch_ids('tests')
    if existing_tests and new_student_ids:
        attempt_count = 0
        for i in range(min(60, len(new_student_ids) * 2)):
            sid = new_student_ids[i % len(new_student_ids)]
            tid = existing_tests[i % len(existing_tests)]
            taid = str(uuid.uuid4())
            correct = random.randint(8, 28)
            incorrect = random.randint(2, 12)
            skipped = 30 - correct - incorrect
            raw_score = correct * 4 - incorrect * 1
            total_marks = 120
            percentage = round((raw_score / total_marks) * 100, 2)
            start_time = datetime.now() - timedelta(days=random.randint(1, 60))
            time_taken = random.randint(1200, 4200)
            cur.execute(
                "INSERT INTO test_attempts(id, attempt_number, started_at, submitted_at, time_taken_seconds, "
                "total_questions, attempted, correct, incorrect, skipped, marked_for_review, raw_score, total_marks, "
                "percentage, result, section_scores, status, tab_switch_count, copy_paste_attempts, proctoring_violations, "
                "auto_terminated, time_limit_reached, student_id, test_id, tenant_id) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT DO NOTHING",
                (taid, 1, start_time, start_time + timedelta(seconds=time_taken), time_taken,
                 30, correct + incorrect, correct, incorrect, skipped, 0,
                 raw_score, total_marks, percentage,
                 'pass' if percentage >= 33 else 'fail', '[]', 'completed',
                 random.randint(0, 2), 0, '[]', False, False,
                 sid, tid, TENANT_ID)
            )
            attempt_count += 1
        conn.commit()
        print(f"   ✓ Inserted {attempt_count} test attempts")

    # ── 10. Insert more attendance for new students ─────────────────────
    print("10. Inserting more attendance records...")
    if all_batch_ids and new_student_ids:
        att_count = 0
        for i in range(min(200, len(new_student_ids) * 5)):
            sid = new_student_ids[i % len(new_student_ids)]
            bid = all_batch_ids[i % len(all_batch_ids)]
            att_date = (datetime.now() - timedelta(days=random.randint(1, 60))).date()
            attid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO attendance(id, user_type, user_id, attendance_date, month, year, status, "
                "check_in_time, source, marked_at, is_corrected, academic_session_id, batch_id, tenant_id) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (attid, 'student', sid, att_date, att_date.month, att_date.year,
                 random.choice(['present', 'present', 'present', 'absent', 'late']),
                 None, 'manual', datetime.now(), False, SESSION_ID, bid, TENANT_ID)
            )
            att_count += 1
        conn.commit()
        print(f"   ✓ Inserted {att_count} attendance records")

    conn.commit()
    print("\n✅ Additional demo data insertion completed successfully!")

    # ── Final summary ───────────────────────────────────────────────────
    print("\n📊 Final Data Counts:")
    tables = [
        ('states', False), ('cities', False),
        ('students', True), ('teachers', True), ('batches', True),
        ('subjects', True), ('chapters', True), ('topics', True),
        ('tests', True), ('questions', True),
        ('test_attempts', True), ('attendance', True),
        ('announcements', True), ('enquiry_forms', True),
        ('study_materials', True),
        ('batch_students', True), ('batch_teachers', True),
    ]
    for tbl, use_tenant in tables:
        if use_tenant:
            cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE tenant_id=%s", (TENANT_ID,))
        else:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"   {tbl}: {cur.fetchone()[0]}")

except Exception as e:
    conn.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    cur.close()
    conn.close()
