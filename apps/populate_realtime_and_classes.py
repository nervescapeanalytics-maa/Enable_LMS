"""
Populate Real-Time Events and Live Classes & YouTube with realistic demo data.
"""
import os, sys, uuid, secrets, random
from datetime import datetime, timedelta, date, time
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')

import django
django.setup()

from django.utils import timezone
from tenants.models import Tenant
from accounts.models import Teacher, Student
from academics.models import Batch, Chapter, Topic
from realtime.models import RealtimeEvent
from classes.models import YouTubeChannel, ScheduledClass, ClassAccessToken, ClassWatchTime
from sessions_tracking.models import UserDevice

tenant = Tenant.objects.first()

# Real teachers
teachers = list(Teacher.objects.all())
students = list(Student.objects.all())
batches = list(Batch.objects.all())
devices = list(UserDevice.objects.all())
chapter = Chapter.objects.first()
topic = Topic.objects.first()

teacher_map = {t.email.split('@')[0].replace('.', '_'): t for t in teachers}

print(f"Tenant: {tenant.name}")
print(f"Teachers: {len(teachers)}, Students: {len(students)}, Batches: {len(batches)}, Devices: {len(devices)}")

# ============================================================
# 1. YOUTUBE CHANNELS - Real Indian educational channels
# ============================================================
print("\n--- Creating YouTube Channels ---")

yt_channels_data = [
    {
        'channel_id': 'UC6RJ7-PaM23UmLY0V3g2dHg',
        'channel_name': 'Enable Program Physics',
        'channel_url': 'https://www.youtube.com/@EnableProgramPhysics',
        'status': 'ACTIVE',
        'verification_status': 'VERIFIED',
        'primary_channel': True,
        'daily_quota_limit': 10000,
        'quota_used_today': 3245,
        'assigned_teacher': teachers[0],  # Dr. Kavita Reddy
        'scopes': ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.force-ssl'],
        'channel_meta': {
            'subscriber_count': 15420,
            'video_count': 342,
            'total_views': 2890000,
            'category': 'Education',
            'language': 'Hindi',
            'description': 'Physics lectures for JEE/NEET by Dr. Kavita Reddy'
        },
    },
    {
        'channel_id': 'UC8butISFwT-Wl7EV0hUK0BQ',
        'channel_name': 'Enable Program Chemistry',
        'channel_url': 'https://www.youtube.com/@EnableProgramChemistry',
        'status': 'ACTIVE',
        'verification_status': 'VERIFIED',
        'primary_channel': False,
        'daily_quota_limit': 10000,
        'quota_used_today': 1580,
        'assigned_teacher': teachers[1],  # Mr. Manoj Tiwari
        'scopes': ['https://www.googleapis.com/auth/youtube'],
        'channel_meta': {
            'subscriber_count': 9870,
            'video_count': 218,
            'total_views': 1540000,
            'category': 'Education',
            'language': 'Hindi',
            'description': 'Chemistry lectures for JEE/NEET by Mr. Manoj Tiwari'
        },
    },
    {
        'channel_id': 'UCXv1JCOwgl2SCbB3tN9dS3A',
        'channel_name': 'Enable Program Maths',
        'channel_url': 'https://www.youtube.com/@EnableProgramMaths',
        'status': 'ACTIVE',
        'verification_status': 'VERIFIED',
        'primary_channel': False,
        'daily_quota_limit': 10000,
        'quota_used_today': 890,
        'assigned_teacher': teachers[2],  # Ms. Pallavi Saxena
        'scopes': ['https://www.googleapis.com/auth/youtube'],
        'channel_meta': {
            'subscriber_count': 12300,
            'video_count': 290,
            'total_views': 2100000,
            'category': 'Education',
            'language': 'Hindi/English',
            'description': 'Mathematics for JEE preparation by Ms. Pallavi Saxena'
        },
    },
    {
        'channel_id': 'UCcsTcfMoG5q2K_WIQd_MBIQ',
        'channel_name': 'Enable Program Biology',
        'channel_url': 'https://www.youtube.com/@EnableProgramBiology',
        'status': 'ACTIVE',
        'verification_status': 'PENDING',
        'primary_channel': False,
        'daily_quota_limit': 10000,
        'quota_used_today': 0,
        'assigned_teacher': teachers[3],  # Dr. Ramesh Yadav
        'scopes': ['https://www.googleapis.com/auth/youtube'],
        'channel_meta': {
            'subscriber_count': 7650,
            'video_count': 175,
            'total_views': 980000,
            'category': 'Education',
            'language': 'Hindi',
            'description': 'Biology lectures for NEET by Dr. Ramesh Yadav'
        },
    },
    {
        'channel_id': 'UCr8AOW1yWkRECUDCxYq6lOw',
        'channel_name': 'Enable Program Doubt Sessions',
        'channel_url': 'https://www.youtube.com/@EnableProgramDoubts',
        'status': 'INACTIVE',
        'verification_status': 'FAILED',
        'primary_channel': False,
        'daily_quota_limit': 5000,
        'quota_used_today': 0,
        'assigned_teacher': teachers[4],  # Mrs. Shalini Dubey
        'scopes': [],
        'channel_meta': {
            'subscriber_count': 3200,
            'video_count': 89,
            'total_views': 420000,
            'category': 'Education',
            'language': 'Hindi',
            'description': 'Doubt clearing sessions (channel re-verification needed)'
        },
    },
]

yt_channels = []
for data in yt_channels_data:
    ch = YouTubeChannel.objects.create(
        tenant=tenant,
        channel_id=data['channel_id'],
        channel_name=data['channel_name'],
        channel_url=data['channel_url'],
        status=data['status'],
        verification_status=data['verification_status'],
        primary_channel=data['primary_channel'],
        daily_quota_limit=data['daily_quota_limit'],
        quota_used_today=data['quota_used_today'],
        assigned_teacher=data['assigned_teacher'],
        scopes=data['scopes'],
        channel_meta=data['channel_meta'],
        owned_by_tenant=True,
        last_verified_at=timezone.now() - timedelta(days=random.randint(1, 30)) if data['verification_status'] == 'VERIFIED' else None,
        quota_reset_at=timezone.now().replace(hour=0, minute=0, second=0) + timedelta(days=1),
    )
    yt_channels.append(ch)
    status_icon = '✅' if data['status'] == 'ACTIVE' else '⏸️'
    print(f"  {status_icon} {ch.channel_name} ({ch.status})")

print(f"Created {len(yt_channels)} YouTube Channels")

# ============================================================
# 2. SCHEDULED CLASSES - Mix of past, today, and upcoming
# ============================================================
print("\n--- Creating Scheduled Classes ---")

today = date.today()

classes_data = [
    # Past completed classes
    {
        'class_code': 'PHY-NL-001',
        'title': "Newton's Laws of Motion - Part 1",
        'description': 'Introduction to Newton\'s three laws, inertial frames, and free body diagrams',
        'subject': 'PHYSICS',
        'scheduled_date': today - timedelta(days=5),
        'start_time': time(10, 0),
        'end_time': time(11, 30),
        'duration_minutes': 90,
        'teacher': teachers[0],  # Dr. Kavita Reddy
        'batch': batches[0],     # Foundation Batch 2025
        'status': 'COMPLETED',
        'youtube_channel': yt_channels[0],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'peak_live_viewers': 45,
        'total_unique_viewers': 52,
        'average_watch_duration_seconds': 4800,
        'total_chat_messages': 127,
        'topics_covered': ["Newton's First Law", "Newton's Second Law", "Free Body Diagrams"],
        'learning_objectives': ['Understand inertial frames', 'Draw FBD for simple systems', 'Apply F=ma to 1D problems'],
    },
    {
        'class_code': 'PHY-NL-002',
        'title': "Newton's Laws of Motion - Part 2",
        'description': 'Application of Newton\'s laws: pulleys, inclined planes, friction',
        'subject': 'PHYSICS',
        'scheduled_date': today - timedelta(days=3),
        'start_time': time(10, 0),
        'end_time': time(11, 30),
        'duration_minutes': 90,
        'teacher': teachers[0],
        'batch': batches[0],
        'status': 'COMPLETED',
        'youtube_channel': yt_channels[0],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'peak_live_viewers': 48,
        'total_unique_viewers': 55,
        'average_watch_duration_seconds': 5100,
        'total_chat_messages': 98,
        'topics_covered': ['Pulley Systems', 'Inclined Planes', 'Friction - Static & Kinetic'],
        'learning_objectives': ['Solve pulley problems', 'Analyze motion on inclined planes', 'Calculate friction forces'],
    },
    {
        'class_code': 'CHM-OC-001',
        'title': 'Organic Chemistry - IUPAC Nomenclature',
        'description': 'Rules of IUPAC naming for alkanes, alkenes, alkynes and functional groups',
        'subject': 'CHEMISTRY',
        'scheduled_date': today - timedelta(days=4),
        'start_time': time(14, 0),
        'end_time': time(15, 30),
        'duration_minutes': 90,
        'teacher': teachers[1],  # Mr. Manoj Tiwari
        'batch': batches[1],     # NEET 2025 Batch B
        'status': 'COMPLETED',
        'youtube_channel': yt_channels[1],
        'privacy_status': 'UNLISTED',
        'access_type': 'MULTI_BATCH',
        'attendance_mode': 'AUTO',
        'peak_live_viewers': 62,
        'total_unique_viewers': 70,
        'average_watch_duration_seconds': 4500,
        'total_chat_messages': 156,
        'topics_covered': ['IUPAC Rules', 'Alkanes Naming', 'Functional Group Priority'],
        'learning_objectives': ['Name organic compounds correctly', 'Identify parent chain', 'Order functional group priorities'],
        'allowed_batches': [str(batches[1].id), str(batches[2].id)],
    },
    {
        'class_code': 'MAT-CAL-001',
        'title': 'Calculus - Limits and Continuity',
        'description': 'Concept of limits, left-right limits, continuity at a point, types of discontinuities',
        'subject': 'MATHEMATICS',
        'scheduled_date': today - timedelta(days=2),
        'start_time': time(16, 0),
        'end_time': time(17, 30),
        'duration_minutes': 90,
        'teacher': teachers[2],  # Ms. Pallavi Saxena
        'batch': batches[4],     # JEE 2025 Batch C
        'status': 'COMPLETED',
        'youtube_channel': yt_channels[2],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'HYBRID',
        'peak_live_viewers': 38,
        'total_unique_viewers': 42,
        'average_watch_duration_seconds': 5400,
        'total_chat_messages': 89,
        'topics_covered': ['Limits Definition', 'Left-Right Limits', 'Continuity Tests', 'Types of Discontinuities'],
        'learning_objectives': ['Evaluate limits algebraically', 'Check continuity at a point', 'Classify discontinuities'],
    },
    {
        'class_code': 'BIO-GEN-001',
        'title': 'Genetics - Mendel\'s Laws of Inheritance',
        'description': 'Monohybrid cross, dihybrid cross, law of dominance, law of segregation',
        'subject': 'BIOLOGY',
        'scheduled_date': today - timedelta(days=1),
        'start_time': time(11, 0),
        'end_time': time(12, 30),
        'duration_minutes': 90,
        'teacher': teachers[3],  # Dr. Ramesh Yadav
        'batch': batches[1],     # NEET 2025 Batch B
        'status': 'COMPLETED',
        'youtube_channel': yt_channels[3],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'peak_live_viewers': 55,
        'total_unique_viewers': 61,
        'average_watch_duration_seconds': 4200,
        'total_chat_messages': 145,
        'topics_covered': ["Mendel's First Law", "Mendel's Second Law", 'Monohybrid Cross', 'Punnett Square'],
        'learning_objectives': ['Explain law of dominance', 'Solve monohybrid cross problems', 'Predict genotypic ratios'],
    },
    # TODAY - Live / Scheduled
    {
        'class_code': 'PHY-WEP-001',
        'title': 'Work, Energy & Power - Live Session',
        'description': 'Work done by constant and variable forces, kinetic energy theorem',
        'subject': 'PHYSICS',
        'scheduled_date': today,
        'start_time': time(10, 0),
        'end_time': time(11, 30),
        'duration_minutes': 90,
        'teacher': teachers[0],  # Dr. Kavita Reddy
        'batch': batches[0],
        'status': 'LIVE',
        'youtube_channel': yt_channels[0],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'peak_live_viewers': 42,
        'total_unique_viewers': 42,
        'total_chat_messages': 35,
        'topics_covered': ['Work by Constant Force', 'Work-Energy Theorem'],
        'learning_objectives': ['Calculate work done', 'Apply work-energy theorem'],
        'youtube_broadcast_id': 'live_abc123xyz',
        'youtube_watch_url': 'https://www.youtube.com/watch?v=live_abc123xyz',
        'youtube_embed_url': 'https://www.youtube.com/embed/live_abc123xyz',
    },
    {
        'class_code': 'CHM-EQ-001',
        'title': 'Chemical Equilibrium - Afternoon Session',
        'description': 'Le Chatelier\'s principle, equilibrium constant, Kp vs Kc',
        'subject': 'CHEMISTRY',
        'scheduled_date': today,
        'start_time': time(14, 0),
        'end_time': time(15, 30),
        'duration_minutes': 90,
        'teacher': teachers[1],  # Mr. Manoj Tiwari
        'batch': batches[2],     # NEET 2025 Batch A
        'status': 'SCHEDULED',
        'youtube_channel': yt_channels[1],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'expected_students': 65,
        'topics_covered': ["Le Chatelier's Principle", 'Equilibrium Constant', 'Kp vs Kc'],
        'learning_objectives': ['Predict shift in equilibrium', 'Calculate Kc and Kp', 'Relate Kp and Kc'],
    },
    # UPCOMING classes
    {
        'class_code': 'MAT-INT-001',
        'title': 'Integration - Definite Integrals',
        'description': 'Properties of definite integrals, Fundamental Theorem of Calculus, area under curves',
        'subject': 'MATHEMATICS',
        'scheduled_date': today + timedelta(days=1),
        'start_time': time(10, 0),
        'end_time': time(11, 30),
        'duration_minutes': 90,
        'teacher': teachers[2],
        'batch': batches[3],  # JEE 2025 Batch D
        'status': 'SCHEDULED',
        'youtube_channel': yt_channels[2],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'expected_students': 50,
        'topics_covered': ['Definite Integrals', 'Properties', 'Area Under Curves'],
        'learning_objectives': ['Evaluate definite integrals', 'Apply fundamental theorem', 'Find area between curves'],
    },
    {
        'class_code': 'BIO-ECO-001',
        'title': 'Ecology - Ecosystem & Food Chains',
        'description': 'Producers, consumers, decomposers, food chains, food webs, ecological pyramids',
        'subject': 'BIOLOGY',
        'scheduled_date': today + timedelta(days=2),
        'start_time': time(11, 0),
        'end_time': time(12, 30),
        'duration_minutes': 90,
        'teacher': teachers[3],
        'batch': batches[1],
        'status': 'SCHEDULED',
        'youtube_channel': yt_channels[3],
        'privacy_status': 'UNLISTED',
        'access_type': 'MULTI_BATCH',
        'attendance_mode': 'AUTO',
        'expected_students': 80,
        'topics_covered': ['Ecosystem Components', 'Food Chains', 'Ecological Pyramids'],
        'learning_objectives': ['Classify organisms by trophic level', 'Construct food webs', 'Interpret ecological pyramids'],
        'allowed_batches': [str(batches[1].id), str(batches[2].id)],
    },
    {
        'class_code': 'PHY-NL-003',
        'title': "Newton's Laws - Doubt Clearing Session",
        'description': 'Open doubt session for Newton\'s Laws topics. Bring your unsolved problems!',
        'subject': 'PHYSICS',
        'scheduled_date': today + timedelta(days=3),
        'start_time': time(18, 0),
        'end_time': time(19, 0),
        'duration_minutes': 60,
        'teacher': teachers[4],  # Mrs. Shalini Dubey
        'batch': batches[0],
        'status': 'DRAFT',
        'youtube_channel': None,
        'privacy_status': 'PRIVATE',
        'access_type': 'ALL_STUDENTS',
        'attendance_mode': 'MANUAL',
        'expected_students': 100,
        'topics_covered': ["Newton's Laws Doubts"],
        'learning_objectives': ['Clear conceptual doubts', 'Practice numerical problems'],
    },
    # Cancelled class example
    {
        'class_code': 'CHM-TH-001',
        'title': 'Thermodynamics - First Law (CANCELLED)',
        'description': 'Cancelled due to teacher unavailability',
        'subject': 'CHEMISTRY',
        'scheduled_date': today - timedelta(days=6),
        'start_time': time(14, 0),
        'end_time': time(15, 30),
        'duration_minutes': 90,
        'teacher': teachers[1],
        'batch': batches[4],
        'status': 'CANCELLED',
        'youtube_channel': yt_channels[1],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'topics_covered': ['First Law of Thermodynamics'],
        'learning_objectives': [],
        'cancellation_reason': 'Teacher unwell - rescheduled to next week',
    },
    # Rescheduled class
    {
        'class_code': 'MAT-VEC-001',
        'title': 'Vectors - Dot & Cross Product (Rescheduled)',
        'description': 'Rescheduled from last Friday. Dot product, cross product, and applications',
        'subject': 'MATHEMATICS',
        'scheduled_date': today + timedelta(days=4),
        'start_time': time(16, 0),
        'end_time': time(17, 30),
        'duration_minutes': 90,
        'teacher': teachers[2],
        'batch': batches[3],
        'status': 'RESCHEDULED',
        'youtube_channel': yt_channels[2],
        'privacy_status': 'UNLISTED',
        'access_type': 'BATCH_ONLY',
        'attendance_mode': 'AUTO',
        'expected_students': 48,
        'reschedule_count': 1,
        'topics_covered': ['Dot Product', 'Cross Product', 'Vector Applications'],
        'learning_objectives': ['Compute dot and cross products', 'Find angle between vectors', 'Calculate area of parallelogram'],
    },
]

scheduled_classes = []
for data in classes_data:
    actual_start = None
    actual_end = None
    if data['status'] in ('COMPLETED', 'LIVE'):
        dt = datetime.combine(data['scheduled_date'], data['start_time'])
        actual_start = timezone.make_aware(dt)
        if data['status'] == 'COMPLETED':
            actual_end = timezone.make_aware(datetime.combine(data['scheduled_date'], data['end_time']))

    youtube_watch = data.get('youtube_watch_url')
    youtube_embed = data.get('youtube_embed_url')
    youtube_broadcast = data.get('youtube_broadcast_id')
    if data['status'] == 'COMPLETED' and not youtube_watch:
        vid_id = f"rec_{secrets.token_hex(6)}"
        youtube_watch = f"https://www.youtube.com/watch?v={vid_id}"
        youtube_embed = f"https://www.youtube.com/embed/{vid_id}"

    sc = ScheduledClass.objects.create(
        tenant=tenant,
        class_code=data['class_code'],
        title=data['title'],
        description=data['description'],
        subject=data.get('subject'),
        scheduled_date=data['scheduled_date'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        duration_minutes=data.get('duration_minutes'),
        class_timezone='Asia/Kolkata',
        teacher=data['teacher'],
        batch=data.get('batch'),
        chapter=chapter,
        topic=topic,
        youtube_channel=data.get('youtube_channel'),
        youtube_broadcast_id=youtube_broadcast,
        youtube_watch_url=youtube_watch,
        youtube_embed_url=youtube_embed,
        youtube_recording_url=youtube_watch if data['status'] == 'COMPLETED' else None,
        privacy_status=data.get('privacy_status', 'UNLISTED'),
        access_type=data.get('access_type', 'BATCH_ONLY'),
        allowed_batches=data.get('allowed_batches', []),
        requires_enrollment_check=True,
        attendance_mode=data.get('attendance_mode', 'AUTO'),
        auto_attendance_threshold_minutes=15,
        min_watch_percent_for_present=70,
        status=data['status'],
        actual_start_time=actual_start,
        actual_end_time=actual_end,
        started_by=data['teacher'] if data['status'] in ('COMPLETED', 'LIVE') else None,
        ended_by=data['teacher'] if data['status'] == 'COMPLETED' else None,
        expected_students=data.get('expected_students'),
        peak_live_viewers=data.get('peak_live_viewers'),
        total_unique_viewers=data.get('total_unique_viewers'),
        average_watch_duration_seconds=data.get('average_watch_duration_seconds'),
        total_chat_messages=data.get('total_chat_messages'),
        cancelled_at=timezone.now() - timedelta(days=6) if data['status'] == 'CANCELLED' else None,
        cancellation_reason=data.get('cancellation_reason'),
        reschedule_count=data.get('reschedule_count', 0),
        topics_covered=data.get('topics_covered', []),
        learning_objectives=data.get('learning_objectives', []),
        created_by_id=data['teacher'].id,
        created_by_type='TEACHER',
    )
    scheduled_classes.append(sc)
    status_labels = {'COMPLETED': '✅', 'LIVE': '🔴', 'SCHEDULED': '📅', 'DRAFT': '📝', 'CANCELLED': '❌', 'RESCHEDULED': '🔄'}
    print(f"  {status_labels.get(sc.status, '❓')} [{sc.class_code}] {sc.title} ({sc.status})")

print(f"Created {len(scheduled_classes)} Scheduled Classes")

# ============================================================
# 3. CLASS ACCESS TOKENS - for completed and live classes
# ============================================================
print("\n--- Creating Class Access Tokens ---")

token_count = 0
completed_live = [sc for sc in scheduled_classes if sc.status in ('COMPLETED', 'LIVE')]

for sc in completed_live:
    # Give tokens to 6 random students per class
    selected_students = random.sample(students, min(6, len(students)))
    for student in selected_students:
        student_devices = [d for d in devices if str(d.user_id) == str(student.id)]
        used = sc.status == 'COMPLETED' or random.random() > 0.3
        token = ClassAccessToken.objects.create(
            tenant=tenant,
            scheduled_class=sc,
            student=student,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.make_aware(datetime.combine(sc.scheduled_date, sc.end_time)) + timedelta(hours=2),
            used=used,
            used_at=timezone.make_aware(datetime.combine(sc.scheduled_date, sc.start_time)) + timedelta(minutes=random.randint(0, 10)) if used else None,
            used_device=random.choice(student_devices) if used and student_devices else None,
            used_ip=f"49.{random.randint(30, 50)}.{random.randint(1, 254)}.{random.randint(1, 254)}" if used else None,
            revoked=False,
        )
        token_count += 1

# Add a couple revoked tokens
revoked_students = random.sample(students, 2)
for student in revoked_students:
    ClassAccessToken.objects.create(
        tenant=tenant,
        scheduled_class=completed_live[0],
        student=student,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() - timedelta(hours=1),
        used=False,
        revoked=True,
        revoked_at=timezone.now() - timedelta(hours=3),
        revoked_reason='Student not enrolled in this batch',
    )
    token_count += 1

print(f"Created {token_count} Class Access Tokens")

# ============================================================
# 4. CLASS WATCH TIMES - detailed watch analytics
# ============================================================
print("\n--- Creating Class Watch Times ---")

watch_count = 0
completed_classes = [sc for sc in scheduled_classes if sc.status == 'COMPLETED']

for sc in completed_classes:
    selected_students = random.sample(students, min(7, len(students)))
    for student in selected_students:
        student_devices = [d for d in devices if str(d.user_id) == str(student.id)]
        device = random.choice(student_devices) if student_devices else None

        # Realistic watch patterns
        watch_seconds = random.randint(2400, 5400)  # 40-90 min
        progress = min(Decimal(str(round(watch_seconds / (sc.duration_minutes * 60) * 100, 2))), Decimal('100.00'))
        engagement = Decimal(str(round(random.uniform(40.0, 98.0), 2)))

        if progress >= 70:
            completion = 'COMPLETED'
        elif progress >= 30:
            completion = 'PARTIAL'
        else:
            completion = 'MINIMAL'

        joined = timezone.make_aware(datetime.combine(sc.scheduled_date, sc.start_time)) + timedelta(minutes=random.randint(0, 5))
        left = joined + timedelta(seconds=watch_seconds)

        cwt = ClassWatchTime.objects.create(
            tenant=tenant,
            scheduled_class=sc,
            student=student,
            watch_session_id=f"ws_{sc.class_code}_{student.id.hex[:8]}_{secrets.token_hex(4)}",
            joined_at=joined,
            left_at=left,
            total_watch_seconds=watch_seconds,
            video_progress_percent=progress,
            max_timestamp_reached=watch_seconds,
            rewind_count=random.randint(0, 12),
            forward_count=random.randint(0, 8),
            pause_count=random.randint(0, 15),
            playback_speed=Decimal(random.choice(['1.0', '1.0', '1.0', '1.25', '1.5', '1.75'])),
            average_quality=random.choice(['1080p', '720p', '720p', '480p', 'auto']),
            buffering_count=random.randint(0, 5),
            buffering_duration_seconds=random.randint(0, 30),
            chat_messages_sent=random.randint(0, 15),
            questions_asked=random.randint(0, 3),
            polls_participated=random.randint(0, 2),
            tab_switches=random.randint(0, 10),
            idle_periods=random.randint(0, 3),
            device=device,
            device_type=device.device_type if device else 'DESKTOP',
            is_live_watch=True,
            completion_status=completion,
            engagement_score=engagement,
        )
        watch_count += 1

print(f"Created {watch_count} Class Watch Time records")

# ============================================================
# 5. REALTIME EVENTS - various event types
# ============================================================
print("\n--- Creating Realtime Events ---")

events_data = []

# CLASS_STARTED events for completed + live
for sc in [s for s in scheduled_classes if s.status in ('COMPLETED', 'LIVE')]:
    events_data.append({
        'event_type': 'CLASS_STARTED',
        'event_key': f'class_started_{sc.class_code}',
        'target_type': 'BATCH',
        'target_id': sc.batch.id if sc.batch else None,
        'target_channel': f'batch_{sc.batch.id}' if sc.batch else f'tenant_{tenant.id}',
        'payload': {
            'class_id': str(sc.id),
            'class_code': sc.class_code,
            'title': sc.title,
            'teacher': f'{sc.teacher.first_name} {sc.teacher.last_name}',
            'youtube_url': sc.youtube_watch_url or '',
            'subject': sc.subject,
        },
        'priority': 8,
        'is_delivered': True,
        'created_at': sc.actual_start_time,
    })

# CLASS_ENDED for completed
for sc in [s for s in scheduled_classes if s.status == 'COMPLETED']:
    events_data.append({
        'event_type': 'CLASS_ENDED',
        'event_key': f'class_ended_{sc.class_code}',
        'target_type': 'BATCH',
        'target_id': sc.batch.id if sc.batch else None,
        'target_channel': f'batch_{sc.batch.id}' if sc.batch else f'tenant_{tenant.id}',
        'payload': {
            'class_id': str(sc.id),
            'class_code': sc.class_code,
            'title': sc.title,
            'duration_minutes': sc.duration_minutes,
            'viewers': sc.total_unique_viewers,
            'recording_url': sc.youtube_recording_url or '',
        },
        'priority': 5,
        'is_delivered': True,
        'created_at': sc.actual_end_time,
    })

# TEST_PUBLISHED events
test_events = [
    {
        'event_type': 'TEST_PUBLISHED',
        'event_key': 'test_physics_weekly_w10',
        'target_type': 'BATCH',
        'target_id': batches[0].id,
        'target_channel': f'batch_{batches[0].id}',
        'payload': {
            'test_name': 'Physics Weekly Test - Week 10',
            'subject': 'Physics',
            'total_marks': 40,
            'duration_minutes': 60,
            'deadline': str(today + timedelta(days=2)),
        },
        'priority': 7,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(hours=6),
    },
    {
        'event_type': 'TEST_PUBLISHED',
        'event_key': 'test_chemistry_chapter5',
        'target_type': 'BATCH',
        'target_id': batches[1].id,
        'target_channel': f'batch_{batches[1].id}',
        'payload': {
            'test_name': 'Chemistry Chapter Test - Organic Chemistry',
            'subject': 'Chemistry',
            'total_marks': 30,
            'duration_minutes': 45,
            'deadline': str(today + timedelta(days=3)),
        },
        'priority': 7,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(hours=4),
    },
]
events_data.extend(test_events)

# TEST_RESULT events
for student in students[:4]:
    events_data.append({
        'event_type': 'TEST_RESULT',
        'event_key': f'result_{student.id.hex[:8]}_physics_weekly',
        'target_type': 'USER',
        'target_id': student.id,
        'target_channel': f'user_{student.id}',
        'payload': {
            'test_name': 'Physics Weekly Test - Week 9',
            'score': random.randint(22, 38),
            'total': 40,
            'rank': random.randint(1, 50),
            'percentage': round(random.uniform(55, 95), 1),
        },
        'priority': 6,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(hours=random.randint(12, 48)),
    })

# ANNOUNCEMENT events
announcements = [
    {
        'title': 'Holiday Notice - Holi Celebration',
        'message': 'No classes on March 14 (Holi). Classes resume March 15.',
        'posted_by': 'Admin',
    },
    {
        'title': 'Parent-Teacher Meeting Scheduled',
        'message': 'PTM scheduled for March 20. Attendance compulsory for all parents.',
        'posted_by': 'Admin',
    },
    {
        'title': 'NEET Mock Test Series Starting',
        'message': 'Full-length NEET mock tests every Sunday starting March 16.',
        'posted_by': 'Dr. Ramesh Yadav',
    },
]
for ann in announcements:
    events_data.append({
        'event_type': 'ANNOUNCEMENT',
        'event_key': f'announcement_{secrets.token_hex(4)}',
        'target_type': 'BROADCAST',
        'target_id': None,
        'target_channel': f'tenant_{tenant.id}',
        'payload': ann,
        'priority': 9,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(hours=random.randint(1, 72)),
    })

# ATTENDANCE_MARKED events
for sc in completed_classes[:3]:
    for student in random.sample(students, 3):
        events_data.append({
            'event_type': 'ATTENDANCE_MARKED',
            'event_key': f'attendance_{sc.class_code}_{student.id.hex[:8]}',
            'target_type': 'USER',
            'target_id': student.id,
            'target_channel': f'user_{student.id}',
            'payload': {
                'class_code': sc.class_code,
                'class_title': sc.title,
                'status': random.choice(['PRESENT', 'PRESENT', 'PRESENT', 'LATE']),
                'watch_percent': random.randint(65, 100),
            },
            'priority': 3,
            'is_delivered': True,
            'created_at': sc.actual_end_time + timedelta(minutes=5) if sc.actual_end_time else timezone.now(),
        })

# NOTIFICATION events
notifications = [
    {'msg': 'Your assignment "Mechanics Practice Set" is due tomorrow', 'user_idx': 0},
    {'msg': 'New study material uploaded: Organic Chemistry Notes Ch.5', 'user_idx': 1},
    {'msg': 'Your doubt has been answered by Dr. Kavita Reddy', 'user_idx': 2},
    {'msg': 'Congratulations! You scored highest in the Physics test', 'user_idx': 3},
    {'msg': 'Reminder: Chemistry class starts in 30 minutes', 'user_idx': 4},
]
for notif in notifications:
    student = students[notif['user_idx']]
    events_data.append({
        'event_type': 'NOTIFICATION',
        'event_key': f'notif_{secrets.token_hex(4)}',
        'target_type': 'USER',
        'target_id': student.id,
        'target_channel': f'user_{student.id}',
        'payload': {'message': notif['msg'], 'type': 'info'},
        'priority': 4,
        'is_delivered': random.choice([True, True, False]),
        'created_at': timezone.now() - timedelta(minutes=random.randint(10, 600)),
    })

# SESSION_TERMINATED events
events_data.append({
    'event_type': 'SESSION_TERMINATED',
    'event_key': f'session_term_{secrets.token_hex(4)}',
    'target_type': 'USER',
    'target_id': students[5].id,
    'target_channel': f'user_{students[5].id}',
    'payload': {
        'reason': 'Multiple active sessions detected',
        'terminated_device': 'Chrome on Windows',
        'action': 'Oldest session terminated automatically',
    },
    'priority': 7,
    'is_delivered': True,
    'created_at': timezone.now() - timedelta(hours=5),
})

# SYSTEM_ALERT events
system_alerts = [
    {'alert': 'YouTube API quota at 85% — streaming may be affected', 'severity': 'WARNING'},
    {'alert': 'Server memory usage above 80%', 'severity': 'WARNING'},
    {'alert': 'All systems operational — daily health check passed', 'severity': 'INFO'},
]
for alert in system_alerts:
    events_data.append({
        'event_type': 'SYSTEM_ALERT',
        'event_key': f'sysalert_{secrets.token_hex(4)}',
        'target_type': 'BROADCAST',
        'target_id': None,
        'target_channel': f'admin_{tenant.id}',
        'payload': alert,
        'priority': 9 if alert['severity'] == 'WARNING' else 3,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(hours=random.randint(1, 24)),
    })

# CHAT_MESSAGE events
for i in range(5):
    student = random.choice(students)
    events_data.append({
        'event_type': 'CHAT_MESSAGE',
        'event_key': f'chat_{secrets.token_hex(4)}',
        'target_type': 'BATCH',
        'target_id': batches[0].id,
        'target_channel': f'class_{scheduled_classes[5].id}',  # Live class
        'payload': {
            'sender': f'{student.first_name} {student.last_name}',
            'message': random.choice([
                'Sir, can you explain this formula again?',
                'What is the unit of work?',
                'Is this coming in the exam?',
                'Can you solve one more example?',
                'Thank you sir, very clear explanation!',
            ]),
        },
        'priority': 2,
        'is_delivered': True,
        'created_at': timezone.now() - timedelta(minutes=random.randint(1, 30)),
    })

# Undelivered events (pending)
for i in range(3):
    student = random.choice(students)
    events_data.append({
        'event_type': 'NOTIFICATION',
        'event_key': f'notif_pending_{secrets.token_hex(4)}',
        'target_type': 'USER',
        'target_id': student.id,
        'target_channel': f'user_{student.id}',
        'payload': {
            'message': random.choice([
                'New practice questions available for Chapter 5',
                'Your weekly progress report is ready',
                'Upcoming test reminder: Biology Chapter Test',
            ]),
        },
        'priority': 5,
        'is_delivered': False,
        'delivery_attempts': random.randint(1, 3),
        'created_at': timezone.now() - timedelta(minutes=random.randint(5, 120)),
    })

# Create all events
event_count = 0
for data in events_data:
    evt = RealtimeEvent.objects.create(
        tenant=tenant,
        event_type=data['event_type'],
        event_key=data.get('event_key'),
        target_type=data.get('target_type'),
        target_id=data.get('target_id'),
        target_channel=data.get('target_channel'),
        payload=data.get('payload', {}),
        priority=data.get('priority', 5),
        is_delivered=data.get('is_delivered', False),
        delivered_at=data['created_at'] + timedelta(seconds=random.randint(1, 30)) if data.get('is_delivered') else None,
        delivery_attempts=data.get('delivery_attempts', 1 if data.get('is_delivered') else 0),
        created_at=data.get('created_at', timezone.now()),
        expires_at=data.get('created_at', timezone.now()) + timedelta(hours=24),
    )
    event_count += 1

# Print event type summary
from collections import Counter
type_counts = Counter(d['event_type'] for d in events_data)
delivered = sum(1 for d in events_data if d.get('is_delivered'))
pending = sum(1 for d in events_data if not d.get('is_delivered'))

print(f"Created {event_count} Realtime Events:")
for etype, cnt in sorted(type_counts.items()):
    print(f"  {etype}: {cnt}")
print(f"  Delivered: {delivered}, Pending: {pending}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*60)
print("POPULATION SUMMARY")
print("="*60)
print(f"  YouTube Channels:    {len(yt_channels)}")
print(f"  Scheduled Classes:   {len(scheduled_classes)}")
print(f"  Class Access Tokens: {token_count}")
print(f"  Class Watch Times:   {watch_count}")
print(f"  Realtime Events:     {event_count}")
print(f"  TOTAL RECORDS:       {len(yt_channels) + len(scheduled_classes) + token_count + watch_count + event_count}")
print("="*60)
