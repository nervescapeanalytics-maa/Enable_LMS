"""
Populate demo data for Session & Activity Tracking
Run: python populate_session_tracking_demo.py
"""
import os, sys, uuid, random
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')

import django
django.setup()

from django.utils import timezone
from sessions_tracking.models import UserDevice, UserSession, LoginHistory, UserActivity
from tenants.models import Tenant

tenant = Tenant.objects.first()
now = timezone.now()

# ── Real user IDs from the database ──
USERS = [
    # (user_id, user_type, name, email)
    ('c998006b-9d1f-4c41-9892-c7697639c678', 'STUDENT',  'Preeti Bansal',         'preeti.bansal49@lms.com'),
    ('dbb32cbc-d0a8-44b6-a074-1f0877bfe131', 'STUDENT',  'Swati Das',             'swati.das48@lms.com'),
    ('2d287a26-9e4b-462a-81d6-0aa203dfcf9a', 'STUDENT',  'Zoya Pillai',           'zoya.pillai47@lms.com'),
    ('0cdded58-d8fe-4be6-9c4b-78c4ca6e39ec', 'STUDENT',  'Yamini Iyer',           'yamini.iyer46@lms.com'),
    ('66eb0317-8ae8-43e0-a2bb-301956835b87', 'STUDENT',  'Wriddhika Deshmukh',    'wriddhika.deshmukh45@lms.com'),
    ('53d7a19a-64b2-4af3-9445-6c75de474a54', 'STUDENT',  'Vandana Bhat',          'vandana.bhat44@lms.com'),
    ('09bd14d5-55a6-45b7-90fe-d62ad0387d41', 'STUDENT',  'Uma Kulkarni',          'uma.kulkarni43@lms.com'),
    ('705b4be7-e31d-4e51-94a5-ff85cfcf0a85', 'STUDENT',  'Tanvi Tripathi',        'tanvi.tripathi42@lms.com'),
    ('16427673-b5b6-40be-8e7a-02cce0244cb9', 'TEACHER',  'Dr. Kavita Reddy',      'kavita.reddy@lms.com'),
    ('7e8d8af4-8be5-407f-9360-91928ac0fce8', 'TEACHER',  'Mr. Manoj Tiwari',      'manoj.tiwari@lms.com'),
    ('47c90738-d2c8-4bae-9c49-918379af47db', 'TEACHER',  'Ms. Pallavi Saxena',    'pallavi.saxena@lms.com'),
    ('de23ec6d-b256-4d8b-b383-8cb4eb4dafac', 'TEACHER',  'Dr. Ramesh Yadav',      'ramesh.yadav@lms.com'),
    ('f8fac938-400a-42a6-81ad-616090a5daae', 'TEACHER',  'Mrs. Shalini Dubey',    'shalini.dubey@lms.com'),
    ('c1e84db8-b496-43f6-a96d-7b08054a6acb', 'ADMIN',    'System Administrator',  'admin@lms.com'),
]

# ── Device definitions ──
DEVICE_DEFS = [
    ('DESKTOP', 'Windows', '11', 'Chrome', '122.0', '1920x1080',
     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'),
    ('DESKTOP', 'Windows', '10', 'Edge', '121.0', '1366x768',
     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/121.0.0.0'),
    ('LAPTOP', 'macOS', '14.3', 'Safari', '17.3', '2560x1600',
     'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 Safari/17.3'),
    ('LAPTOP', 'macOS', '14.2', 'Chrome', '122.0', '1440x900',
     'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 Chrome/122.0.0.0'),
    ('MOBILE', 'Android', '14', 'Chrome Mobile', '121.0', '393x873',
     'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 Chrome/121.0.0.0 Mobile Safari/537.36'),
    ('MOBILE', 'Android', '13', 'Chrome Mobile', '120.0', '412x915',
     'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36'),
    ('MOBILE', 'iOS', '17.3', 'Safari Mobile', '17.3', '390x844',
     'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'),
    ('TABLET', 'iPadOS', '17.3', 'Safari', '17.3', '1024x1366',
     'Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 Safari/17.3'),
    ('TABLET', 'Android', '14', 'Chrome', '122.0', '800x1280',
     'Mozilla/5.0 (Linux; Android 14; SM-X200) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'),
    ('LAPTOP', 'Linux', '6.5', 'Firefox', '123.0', '1920x1080',
     'Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0'),
]

CITIES = [
    ('Mumbai', 'Maharashtra', 'India', '19.0760,72.8777'),
    ('Delhi', 'Delhi', 'India', '28.7041,77.1025'),
    ('Bangalore', 'Karnataka', 'India', '12.9716,77.5946'),
    ('Hyderabad', 'Telangana', 'India', '17.3850,78.4867'),
    ('Chennai', 'Tamil Nadu', 'India', '13.0827,80.2707'),
    ('Pune', 'Maharashtra', 'India', '18.5204,73.8567'),
    ('Kolkata', 'West Bengal', 'India', '22.5726,88.3639'),
    ('Jaipur', 'Rajasthan', 'India', '26.9124,75.7873'),
    ('Lucknow', 'Uttar Pradesh', 'India', '26.8467,80.9462'),
    ('Bhopal', 'Madhya Pradesh', 'India', '23.2599,77.4126'),
]

IPS = [
    '103.21.124.{}'.format(random.randint(10, 250)),
    '182.73.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '49.36.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '157.49.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '223.226.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '59.89.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '117.195.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '106.51.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '14.139.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
    '43.251.{}.{}'.format(random.randint(10, 250), random.randint(10, 250)),
]

DEVICE_NAMES = [
    "Preeti's Laptop", "Swati's Phone", "Zoya's Desktop", "Yamini's iPad",
    "Wriddhika's PC", "Vandana's Mobile", "Uma's Laptop", "Tanvi's Desktop",
    "Kavita Ma'am Laptop", "Manoj Sir Desktop", "Pallavi Ma'am MacBook",
    "Ramesh Sir PC", "Shalini Ma'am Tablet", "Admin Workstation",
    "Lab PC - Room 201", "Library Desktop 3", "Staff Room PC",
    "Computer Lab 1 - PC5", "Principal Office PC", "Reception Desk"
]

print("=" * 60)
print("POPULATING SESSION & ACTIVITY TRACKING DEMO DATA")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# 1. USER DEVICES (20 devices)
# ══════════════════════════════════════════════════════════════
print("\n📱 Creating User Devices...")
devices = []
for i, (uid, utype, name, email) in enumerate(USERS):
    # Each user gets 1-2 devices
    devs_for_user = random.randint(1, 2)
    for d in range(devs_for_user):
        dd = DEVICE_DEFS[(i + d) % len(DEVICE_DEFS)]
        dev_name = DEVICE_NAMES[len(devices) % len(DEVICE_NAMES)]
        fingerprint = f"fp_{uuid.uuid4().hex[:24]}"

        device = UserDevice.objects.create(
            tenant=tenant,
            user_id=uid,
            user_type=utype,
            device_fingerprint=fingerprint,
            device_name=dev_name,
            device_type=dd[0],
            os_name=dd[1],
            os_version=dd[2],
            browser_name=dd[3],
            browser_version=dd[4],
            screen_resolution=dd[5],
            user_agent=dd[6],
            is_trusted=random.choice([True, True, True, False]),
            is_blocked=False,
            first_seen=now - timedelta(days=random.randint(15, 90)),
            total_sessions=random.randint(5, 80),
        )
        devices.append(device)
        if len(devices) >= 20:
            break
    if len(devices) >= 20:
        break

print(f"  ✅ Created {len(devices)} devices")

# ══════════════════════════════════════════════════════════════
# 2. USER SESSIONS (40 sessions — mix of active/expired/logged out)
# ══════════════════════════════════════════════════════════════
print("\n🔗 Creating User Sessions...")
sessions = []
SESSION_STATUSES = ['ACTIVE', 'ACTIVE', 'EXPIRED', 'LOGGED_OUT', 'LOGGED_OUT', 'EXPIRED']

for i in range(40):
    user = USERS[i % len(USERS)]
    uid, utype = user[0], user[1]
    city = random.choice(CITIES)
    ip = random.choice(IPS)
    device = random.choice(devices)
    status = random.choice(SESSION_STATUSES)

    if status == 'ACTIVE':
        started = now - timedelta(minutes=random.randint(5, 180))
        expires = now + timedelta(hours=random.randint(1, 8))
        ended = None
        active_secs = int((now - started).total_seconds())
    elif status == 'EXPIRED':
        started = now - timedelta(hours=random.randint(6, 72))
        expires = started + timedelta(hours=random.randint(2, 8))
        ended = expires
        active_secs = random.randint(1800, 14400)
    else:  # LOGGED_OUT
        started = now - timedelta(hours=random.randint(1, 48))
        expires = started + timedelta(hours=8)
        ended = started + timedelta(minutes=random.randint(30, 300))
        active_secs = int((ended - started).total_seconds())

    session = UserSession.objects.create(
        tenant=tenant,
        user_id=uid,
        user_type=utype,
        session_token=f"tok_{uuid.uuid4().hex}",
        refresh_token_hash=f"rth_{uuid.uuid4().hex[:32]}",
        device=device,
        ip_address=ip,
        geo_city=city[0],
        geo_state=city[1],
        geo_country=city[2],
        geo_coordinates=city[3],
        started_at=started,
        expires_at=expires,
        status=status,
        ended_at=ended,
        end_reason='User logged out' if status == 'LOGGED_OUT' else ('Session expired' if status == 'EXPIRED' else None),
        total_active_seconds=active_secs,
        concurrent_session_check=True,
        is_primary_session=(i % 3 != 2),
    )
    sessions.append(session)

print(f"  ✅ Created {len(sessions)} sessions")
active_count = len([s for s in sessions if s.status == 'ACTIVE'])
print(f"     Active: {active_count} | Expired: {len([s for s in sessions if s.status == 'EXPIRED'])} | Logged Out: {len([s for s in sessions if s.status == 'LOGGED_OUT'])}")

# ══════════════════════════════════════════════════════════════
# 3. LOGIN HISTORY (80 entries — over last 7 days)
# ══════════════════════════════════════════════════════════════
print("\n🔐 Creating Login History...")
login_count = 0

FAILURE_REASONS = [
    'Invalid password',
    'Account not found',
    'Password expired',
    'Too many attempts',
    'IP blocked by policy',
]

RISK_FACTORS_OPTIONS = [
    ['new_device', 'unusual_time'],
    ['new_location'],
    ['multiple_failed_attempts'],
    ['unusual_ip_range'],
    ['new_device', 'new_location', 'unusual_time'],
    ['impossible_travel'],
]

for day_offset in range(7):
    day_time = now - timedelta(days=day_offset)
    # More logins on recent days
    num_logins = random.randint(8, 16) if day_offset < 3 else random.randint(4, 10)

    for _ in range(num_logins):
        user = random.choice(USERS)
        uid, utype, name, email = user
        city = random.choice(CITIES)
        ip = random.choice(IPS)
        device = random.choice(devices)

        # Mostly successful, some failed, rare blocked/suspicious
        roll = random.random()
        if roll < 0.72:
            result = 'SUCCESS'
            failure_reason = None
            is_suspicious = False
            risk_score = Decimal(str(round(random.uniform(0, 15), 2)))
            risk_factors = []
            session_id = random.choice(sessions).id
        elif roll < 0.88:
            result = 'FAILED'
            failure_reason = random.choice(FAILURE_REASONS)
            is_suspicious = random.random() < 0.3
            risk_score = Decimal(str(round(random.uniform(20, 60), 2)))
            risk_factors = random.choice(RISK_FACTORS_OPTIONS) if is_suspicious else []
            session_id = None
        elif roll < 0.95:
            result = 'BLOCKED'
            failure_reason = 'IP blocked by security policy'
            is_suspicious = True
            risk_score = Decimal(str(round(random.uniform(70, 95), 2)))
            risk_factors = random.choice(RISK_FACTORS_OPTIONS)
            session_id = None
        else:
            result = random.choice(['MFA_REQUIRED', 'ACCOUNT_LOCKED', 'INACTIVE'])
            failure_reason = 'MFA verification pending' if result == 'MFA_REQUIRED' else 'Account locked after 5 failed attempts' if result == 'ACCOUNT_LOCKED' else 'Account deactivated by admin'
            is_suspicious = result == 'ACCOUNT_LOCKED'
            risk_score = Decimal(str(round(random.uniform(40, 80), 2)))
            risk_factors = ['multiple_failed_attempts'] if result == 'ACCOUNT_LOCKED' else []
            session_id = None

        attempted_at = day_time.replace(
            hour=random.randint(6, 22),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )

        LoginHistory.objects.create(
            tenant=tenant,
            user_id=uid if result == 'SUCCESS' else (uid if random.random() > 0.3 else None),
            user_type=utype,
            username_attempted=email,
            result=result,
            failure_reason=failure_reason,
            ip_address=ip,
            device=device,
            user_agent=device.user_agent,
            geo_city=city[0],
            geo_country=city[2],
            session_id=session_id,
            attempted_at=attempted_at,
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            risk_factors=risk_factors,
        )
        login_count += 1

print(f"  ✅ Created {login_count} login history entries")

# ══════════════════════════════════════════════════════════════
# 4. USER ACTIVITIES (150 entries — realistic LMS actions)
# ══════════════════════════════════════════════════════════════
print("\n📊 Creating User Activities...")
activity_count = 0

ACTIVITY_DEFS = [
    # (type, description_template, resource_type, resource_name_options, page_url_template, duration_range)
    ('PAGE_VIEW', 'Viewed {page}', 'page', ['Dashboard', 'My Profile', 'Test Results', 'Study Materials', 'Attendance Report', 'Notifications', 'Settings', 'Class Schedule'], '/student/{slug}/', (5, 120)),
    ('CLASS_JOIN', 'Joined live class: {page}', 'scheduled_class', ['Physics — Electromagnetic Induction', 'Chemistry — Organic Reactions', 'Maths — Integration by Parts', 'Biology — Human Physiology', 'Physics — Wave Optics', 'Chemistry — Chemical Bonding'], '/class/live/{id}/', (1800, 3600)),
    ('CLASS_LEAVE', 'Left class: {page}', 'scheduled_class', ['Physics — Electromagnetic Induction', 'Chemistry — Organic Reactions', 'Maths — Integration by Parts'], '/class/live/{id}/', (0, 5)),
    ('TEST_START', 'Started test: {page}', 'test', ['Weekly Physics Test #8', 'Monthly Chemistry Exam', 'JEE Mock Test — Feb 2026', 'NEET Practice Set #12', 'Unit Test — Thermodynamics'], '/test/attempt/{id}/', (0, 5)),
    ('TEST_SUBMIT', 'Submitted test: {page}', 'test', ['Weekly Physics Test #8', 'Monthly Chemistry Exam', 'JEE Mock Test — Feb 2026', 'NEET Practice Set #12'], '/test/result/{id}/', (1800, 7200)),
    ('MATERIAL_VIEW', 'Viewed material: {page}', 'study_material', ['NCERT Physics Ch.6 PDF', 'Organic Chemistry Notes', 'Integration Formula Sheet', 'JEE Previous Year Solutions', 'NEET Biology Diagrams', 'Thermodynamics Revision Notes'], '/materials/view/{id}/', (60, 1800)),
    ('MATERIAL_DOWNLOAD', 'Downloaded: {page}', 'study_material', ['NCERT Physics Ch.6 PDF', 'JEE Mock Paper — Set A', 'Chemistry Formula Sheet', 'Biology Diagrams Package'], '/materials/download/{id}/', (2, 10)),
    ('PROFILE_UPDATE', 'Updated profile: {page}', 'user_profile', ['Changed phone number', 'Updated profile photo', 'Changed address', 'Updated parent contact'], '/profile/edit/', (30, 120)),
    ('MESSAGE_SENT', 'Sent message to {page}', 'message', ['Dr. Kavita Reddy', 'Mr. Manoj Tiwari', 'Class Group', 'Support Team'], '/messages/compose/', (15, 60)),
    ('TICKET_CREATED', 'Created support ticket: {page}', 'support_ticket', ['Cannot access test', 'Video not loading', 'Login issue on mobile', 'Result not showing'], '/support/new/', (60, 300)),
    ('SETTINGS_CHANGE', 'Changed setting: {page}', 'settings', ['Notification preferences', 'Language changed to Hindi', 'Dark mode enabled', 'Email notifications enabled'], '/settings/', (15, 60)),
]

for day_offset in range(7):
    day_time = now - timedelta(days=day_offset)
    num_activities = random.randint(16, 28) if day_offset < 3 else random.randint(8, 16)

    for _ in range(num_activities):
        user = random.choice(USERS)
        uid, utype = user[0], user[1]
        act = random.choice(ACTIVITY_DEFS)
        act_type, desc_tpl, res_type, res_names, url_tpl, dur_range = act
        res_name = random.choice(res_names)

        occurred_at = day_time.replace(
            hour=random.randint(6, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )

        session = random.choice([s for s in sessions if s.user_id == uid] or sessions)
        ip = random.choice(IPS)
        fake_id = uuid.uuid4()

        UserActivity.objects.create(
            tenant=tenant,
            session=session,
            user_id=uid,
            user_type=utype,
            activity_type=act_type,
            activity_description=desc_tpl.replace('{page}', res_name),
            resource_type=res_type,
            resource_id=fake_id,
            resource_name=res_name,
            page_url=url_tpl.replace('{slug}', res_name.lower().replace(' ', '-')).replace('{id}', str(fake_id)[:8]),
            ip_address=ip,
            duration_seconds=random.randint(*dur_range) if act_type not in ('MATERIAL_DOWNLOAD',) else random.randint(2, 10),
            occurred_at=occurred_at,
            activity_data={
                'user_name': user[2],
                'user_email': user[3],
            },
        )
        activity_count += 1

print(f"  ✅ Created {activity_count} user activities")

# ── Summary ──
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  📱 User Devices:    {UserDevice.objects.count()}")
print(f"  🔗 User Sessions:   {UserSession.objects.count()}")
print(f"     ├ Active:        {UserSession.objects.filter(status='ACTIVE').count()}")
print(f"     ├ Expired:       {UserSession.objects.filter(status='EXPIRED').count()}")
print(f"     └ Logged Out:    {UserSession.objects.filter(status='LOGGED_OUT').count()}")
print(f"  🔐 Login History:   {LoginHistory.objects.count()}")
print(f"     ├ Successful:    {LoginHistory.objects.filter(result='SUCCESS').count()}")
print(f"     ├ Failed:        {LoginHistory.objects.filter(result='FAILED').count()}")
print(f"     ├ Blocked:       {LoginHistory.objects.filter(result='BLOCKED').count()}")
print(f"     └ Suspicious:    {LoginHistory.objects.filter(is_suspicious=True).count()}")
print(f"  📊 User Activities: {UserActivity.objects.count()}")
print("=" * 60)
print("✅ All done!")
