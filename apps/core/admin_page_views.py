"""
Admin Staff Page Views — Full CRUD-capable management pages
Each sidebar item gets its own view rendering data from the database.
"""
from datetime import datetime, timedelta, date
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F, Max, Min

from accounts.models import Teacher, Admin
from academics.models import Users
from tenants.models import Tenant
from audit.models import AuditLog


def _require_admin(request):
    """Check admin session, return redirect if not admin, else None"""
    if request.session.get('user_type') != 'ADMIN':
        return redirect('/login/?role=admin')
    return None


def _admin_ctx(request, active_page, page_title, breadcrumb_parent=None, breadcrumb_parent_url=None):
    """Build base context for all admin pages"""
    from academics.models import Batch
    from communication.models import SupportTicket
    from assessments.models import Test

    ctx = {
        'user_name': request.session.get('user_name', 'User'),
        'user_type': request.session.get('user_type', ''),
        'user_id': request.session.get('user_id', ''),
        'user_email': request.session.get('user_email', ''),
        'user_initials': ''.join(w[0].upper() for w in request.session.get('user_name', 'U').split()[:2]),
        'active_page': active_page,
        'page_title': page_title,
        'breadcrumb_active': page_title,
        'breadcrumb_parent': breadcrumb_parent,
        'breadcrumb_parent_url': breadcrumb_parent_url or '/staff/dashboard/',
    }

    # Sidebar badge counts
    try:
        from classes.models import ScheduledClass
        live_count = ScheduledClass.objects.filter(status='LIVE').count()
    except Exception:
        live_count = 0

    open_tickets = SupportTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS', 'PENDING']).count()

    ctx['sidebar_counts'] = {
        'students': Users.objects.filter(is_active=True).count(),
        'teachers': Teacher.objects.count(),
        'tests': Test.objects.count(),
        'live_classes': live_count,
        'open_tickets': open_tickets,
    }

    # Notifications for topbar
    try:
        from communication.models import Notification
        notifs = Notification.objects.filter(
            user_type='ADMIN',
            is_read=False
        ).order_by('-created_at')[:5]
        ctx['notifications'] = [{
            'title': n.title,
            'time': _time_ago(n.created_at),
            'icon': 'fa-bell',
            'color': 'blue',
            'url': n.action_url or '#',
        } for n in notifs]
        ctx['notifications_count'] = Notification.objects.filter(user_type='ADMIN', is_read=False).count()
    except Exception:
        ctx['notifications'] = []
        ctx['notifications_count'] = open_tickets  # Fallback: use ticket count

    return ctx


def _time_ago(dt, now=None):
    if not dt:
        return ''
    if now is None:
        now = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        return f'{seconds // 60} min ago'
    elif seconds < 86400:
        return f'{seconds // 3600} hr ago'
    else:
        days = seconds // 86400
        return f'{days} day{"s" if days > 1 else ""} ago'


# ═══════════════════════════════════════════════════════════════
# 1. ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════════
class AnalyticsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'analytics', 'Analytics')

        from academics.models import Batch, Users
        from sessions_tracking.models import LoginHistory

        now = timezone.now()
        today = now.date()

        # Daily logins for last 7 days
        daily_logins = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = LoginHistory.objects.filter(attempted_at__date=d, result='SUCCESS').count()
            daily_logins.append({'date': d.strftime('%a %d'), 'count': count})

        # Student growth last 7 days
        daily_students = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = Users.objects.filter(enrolled_at__date__lte=d).count()
            daily_students.append({'date': d.strftime('%a %d'), 'count': count})

        max_logins = max((d['count'] for d in daily_logins), default=1) or 1
        max_students = max((d['count'] for d in daily_students), default=1) or 1
        for d in daily_logins:
            d['pct'] = int(d['count'] / max_logins * 100)
        for d in daily_students:
            d['pct'] = int(d['count'] / max_students * 100)

        # Enrollment by batch
        enrollment_by_batch = []
        for b in Batch.objects.filter(status='ACTIVE').order_by('name')[:10]:
            enrolled = Users.objects.filter(batch=b, is_active=True).count()
            enrollment_by_batch.append({'name': b.name, 'count': enrolled})
        max_enroll = max((e['count'] for e in enrollment_by_batch), default=1) or 1
        for e in enrollment_by_batch:
            e['pct'] = int(e['count'] / max_enroll * 100)

        # Students by tenant
        students_by_tenant = []
        for t in Tenant.objects.all():
            c = Users.objects.filter(tenant=t, is_active=True).count()
            students_by_tenant.append({'name': t.name, 'count': c})

        # Summary stats
        ctx.update({
            'total_students': Users.objects.filter(is_active=True).count(),
            'total_teachers': Teacher.objects.count(),
            'today_logins': LoginHistory.objects.filter(attempted_at__date=today, result='SUCCESS').count(),
            'new_students_week': Users.objects.filter(enrolled_at__date__gte=today - timedelta(days=7)).count(),
            'daily_logins': daily_logins,
            'daily_students': daily_students,
            'enrollment_by_batch': enrollment_by_batch,
            'students_by_tenant': students_by_tenant,
        })
        return render(request, 'dashboards/admin_analytics.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 2. MONITORING CENTER
# ═══════════════════════════════════════════════════════════════
class MonitoringView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'monitoring', 'Monitoring Center')

        from sessions_tracking.models import UserSession, LoginHistory, UserDevice
        from django.db import connection

        now = timezone.now()
        fifteen_min_ago = now - timedelta(minutes=15)

        # Active sessions
        active_sessions = UserSession.objects.filter(
            status='ACTIVE', last_activity_at__gte=fifteen_min_ago
        ).select_related('device')[:50]

        session_list = []
        for s in active_sessions:
            session_list.append({
                'user_id': str(s.user_id)[:8],
                'user_type': s.user_type,
                'ip': s.ip_address or 'N/A',
                'device': s.device.device_type if s.device else 'Unknown',
                'browser': (s.device.browser_name if s.device else 'Unknown'),
                'last_active': _time_ago(s.last_activity_at, now),
                'started': s.started_at.strftime('%H:%M') if s.started_at else '',
            })

        # Recent logins
        recent_logins = LoginHistory.objects.order_by('-attempted_at')[:20]
        login_list = []
        for l in recent_logins:
            login_list.append({
                'user_type': l.user_type,
                'username': l.username_attempted or 'N/A',
                'result': l.result,
                'ip': l.ip_address or 'N/A',
                'time': _time_ago(l.attempted_at, now),
                'suspicious': l.is_suspicious,
            })

        # Database check
        db_ok = True
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
        except Exception:
            db_ok = False

        ctx.update({
            'active_session_count': UserSession.objects.filter(status='ACTIVE', last_activity_at__gte=fifteen_min_ago).count(),
            'total_sessions_today': UserSession.objects.filter(started_at__date=now.date()).count(),
            'failed_logins_today': LoginHistory.objects.filter(attempted_at__date=now.date(), result='FAILED').count(),
            'suspicious_logins': LoginHistory.objects.filter(attempted_at__date=now.date(), is_suspicious=True).count(),
            'sessions': session_list,
            'recent_logins': login_list,
            'db_ok': db_ok,
            'server_ok': True,
        })
        return render(request, 'dashboards/admin_monitoring.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 3. SUBJECTS / SUBJECT SECTION
# ═══════════════════════════════════════════════════════════════
class SubjectsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'subjects', 'Subject Section', 'Master')

        from academics.models import Subject, SubjectSection, Chapter

        subjects = Subject.objects.all().order_by('display_order', 'name')
        subject_list = []
        for s in subjects:
            chapters = Chapter.objects.filter(subject=s).count()
            sections = SubjectSection.objects.filter(subject=s).count()
            subject_list.append({
                'id': str(s.id),
                'name': s.name,
                'code': s.code or '',
                'type': s.subject_type or 'General',
                'chapters': chapters,
                'sections': sections,
                'status': s.status,
                'color': s.color or '#3b82f6',
            })

        ctx.update({
            'subjects': subject_list,
            'total_subjects': len(subject_list),
            'active_subjects': sum(1 for s in subject_list if s['status'] == 'ACTIVE'),
        })
        return render(request, 'dashboards/admin_subjects.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 4. BATCHES
# ═══════════════════════════════════════════════════════════════
class BatchesView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'batches', 'Batches', 'Master')

        from academics.models import Batch, Users, BatchTeacher

        batches = Batch.objects.all().order_by('-created_at')
        batch_list = []
        for b in batches:
            enrolled = Users.objects.filter(batch=b, is_active=True).count()
            teachers = BatchTeacher.objects.filter(batch=b).count()
            batch_list.append({
                'id': str(b.id),
                'name': b.name,
                'code': b.code or '',
                'class_level': b.class_level or '',
                'enrolled': enrolled,
                'max_students': b.max_students or '-',
                'teachers': teachers,
                'start_date': b.start_date.strftime('%d %b %Y') if b.start_date else '',
                'end_date': b.end_date.strftime('%d %b %Y') if b.end_date else '',
                'status': b.status,
            })

        ctx.update({
            'batches': batch_list,
            'total_batches': len(batch_list),
            'active_batches': sum(1 for b in batch_list if b['status'] == 'ACTIVE'),
        })
        return render(request, 'dashboards/admin_batches.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 5. PROGRAMS (Groups/Categories)
# ═══════════════════════════════════════════════════════════════
class ProgramsAdminView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'programs', 'Programs', 'Master')

        from academics.models import Group, Category

        groups = Group.objects.all().order_by('name')
        group_list = []
        for g in groups:
            cats = Category.objects.filter(group=g).count()
            group_list.append({
                'id': str(g.id),
                'name': g.name,
                'description': (g.description or '')[:100],
                'categories': cats,
                'status': 'Active' if g.status else 'Inactive',
            })

        ctx.update({
            'groups': group_list,
            'total_groups': len(group_list),
        })
        return render(request, 'dashboards/admin_programs.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 6. ACADEMIC SESSIONS
# ═══════════════════════════════════════════════════════════════
class AcademicSessionsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'sessions', 'Academic Sessions', 'Master')

        from academics.models import AcademicSession

        sessions = AcademicSession.objects.all().order_by('-start_date')
        session_list = []
        for s in sessions:
            session_list.append({
                'id': str(s.id),
                'name': s.session_name,
                'start_date': s.start_date.strftime('%d %b %Y') if s.start_date else '',
                'end_date': s.end_date.strftime('%d %b %Y') if s.end_date else '',
                'is_current': s.is_current,
                'status': 'Active' if s.status else 'Inactive',
            })

        ctx.update({
            'sessions': session_list,
            'total_sessions': len(session_list),
        })
        return render(request, 'dashboards/admin_sessions.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 7. TESTS
# ═══════════════════════════════════════════════════════════════
class TestsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'tests', 'Tests', 'Test & Questions')

        from assessments.models import Test, TestAttempt

        tests = Test.objects.filter(is_deleted=False).order_by('-created_at')
        test_list = []
        for t in tests:
            attempts = TestAttempt.objects.filter(test=t).count()
            test_list.append({
                'id': str(t.id),
                'title': t.title,
                'code': t.test_code or '',
                'type': t.test_type or '',
                'subject': str(t.subject) if t.subject else 'N/A',
                'duration': t.total_duration_minutes or 0,
                'total_marks': t.total_marks or 0,
                'total_questions': t.total_questions or 0,
                'attempts': attempts,
                'status': t.status,
                'created': t.created_at.strftime('%d %b %Y') if t.created_at else '',
            })

        ctx.update({
            'tests': test_list,
            'total_tests': len(test_list),
            'published_tests': sum(1 for t in test_list if t['status'] == 'PUBLISHED'),
            'draft_tests': sum(1 for t in test_list if t['status'] == 'DRAFT'),
        })
        return render(request, 'dashboards/admin_tests.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 8. QUESTIONS
# ═══════════════════════════════════════════════════════════════
class QuestionsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'questions', 'Questions', 'Test & Questions')

        from assessments.models import Question

        questions = Question.objects.filter(is_deleted=False).order_by('-created_at')[:100]
        q_list = []
        for q in questions:
            q_list.append({
                'id': str(q.id),
                'text': (q.question_text or '')[:80],
                'code': q.question_code or '',
                'type': q.question_type or '',
                'difficulty': q.difficulty or '',
                'subject': str(q.subject) if q.subject else 'N/A',
                'chapter': str(q.chapter) if q.chapter else 'N/A',
                'positive_marks': q.positive_marks or 0,
                'negative_marks': q.negative_marks or 0,
                'success_rate': q.success_rate or 0,
                'status': 'Active' if q.is_active else 'Inactive',
            })

        ctx.update({
            'questions': q_list,
            'total_questions': Question.objects.filter(is_deleted=False).count(),
            'active_questions': Question.objects.filter(is_deleted=False, is_active=True).count(),
        })
        return render(request, 'dashboards/admin_questions.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 9. TEST REPORTS
# ═══════════════════════════════════════════════════════════════
class TestReportsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'test-reports', 'Test Reports', 'Test & Questions')

        from assessments.models import Test, TestAttempt

        tests = Test.objects.filter(is_deleted=False).order_by('-created_at')[:20]
        report_list = []
        for t in tests:
            attempts = TestAttempt.objects.filter(test=t)
            total = attempts.count()
            passed = attempts.filter(result='PASS').count()
            failed = attempts.filter(result='FAIL').count()
            avg_score = attempts.aggregate(avg=Avg('percentage'))['avg'] or 0
            avg_time = attempts.aggregate(avg=Avg('time_taken_seconds'))['avg'] or 0

            report_list.append({
                'test_title': t.title,
                'test_code': t.test_code or '',
                'type': t.test_type or '',
                'total_attempts': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(passed / total * 100, 1) if total > 0 else 0,
                'avg_score': round(avg_score, 1),
                'avg_time_min': round(avg_time / 60, 1) if avg_time else 0,
                'status': t.status,
            })

        ctx.update({
            'reports': report_list,
            'total_attempts': TestAttempt.objects.count(),
            'avg_pass_rate': round(
                TestAttempt.objects.filter(result='PASS').count() /
                max(TestAttempt.objects.count(), 1) * 100, 1
            ),
        })
        return render(request, 'dashboards/admin_test_reports.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 10. SCHOOLS / CENTERS (Tenants)
# ═══════════════════════════════════════════════════════════════
class SchoolsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'schools', 'Schools / Centers', 'School / Centers')

        tenants = Tenant.objects.all().order_by('name')
        school_list = []
        for t in tenants:
            students = Users.objects.filter(tenant=t).count()
            active = Users.objects.filter(tenant=t, is_active=True).count()
            teachers = Teacher.objects.filter(tenant=t).count()
            school_list.append({
                'id': str(t.id),
                'name': t.name,
                'code': t.code,
                'total_students': students,
                'active_students': active,
                'inactive_students': students - active,
                'total_teachers': teachers,
            })

        ctx.update({
            'schools': school_list,
            'total_schools': len(school_list),
        })
        return render(request, 'dashboards/admin_schools.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 11. TEACHERS
# ═══════════════════════════════════════════════════════════════
class TeachersView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'teachers', 'Teachers', 'School / Centers')

        from academics.models import BatchTeacher

        teachers = Teacher.objects.all().order_by('first_name')
        teacher_list = []
        for t in teachers:
            batch_count = BatchTeacher.objects.filter(teacher=t).count()
            subjects = t.subjects if isinstance(t.subjects, list) else []
            teacher_list.append({
                'id': str(t.id),
                'name': f"{t.first_name} {t.last_name}",
                'code': t.teacher_code or '',
                'email': t.email,
                'phone': t.phone or '',
                'subjects': ', '.join(subjects[:3]) if subjects else 'N/A',
                'batches': batch_count,
                'status': t.status,
                'joined': t.created_at.strftime('%d %b %Y') if t.created_at else '',
            })

        ctx.update({
            'teachers': teacher_list,
            'total_teachers': len(teacher_list),
            'active_teachers': sum(1 for t in teacher_list if t['status'] == 'ACTIVE'),
        })
        return render(request, 'dashboards/admin_teachers.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 12. TEACHER ATTENDANCE
# ═══════════════════════════════════════════════════════════════
class TeacherAttendanceView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'teacher-attendance', 'Teacher Attendance', 'School / Centers')

        from attendance.models import Attendance

        today = timezone.now().date()
        teachers = Teacher.objects.filter(status='ACTIVE').order_by('first_name')
        att_list = []
        for t in teachers:
            today_att = Attendance.objects.filter(
                user_type='TEACHER', user_id=t.id, attendance_date=today
            ).first()
            total_present = Attendance.objects.filter(
                user_type='TEACHER', user_id=t.id, status='PRESENT'
            ).count()
            total_absent = Attendance.objects.filter(
                user_type='TEACHER', user_id=t.id, status='ABSENT'
            ).count()
            att_list.append({
                'name': f"{t.first_name} {t.last_name}",
                'code': t.teacher_code or '',
                'today_status': today_att.status if today_att else 'Not Marked',
                'today_checkin': today_att.check_in_time.strftime('%I:%M %p') if today_att and today_att.check_in_time else '-',
                'total_present': total_present,
                'total_absent': total_absent,
            })

        ctx.update({
            'attendance': att_list,
            'today_date': today.strftime('%A, %d %B %Y'),
            'marked_today': sum(1 for a in att_list if a['today_status'] != 'Not Marked'),
        })
        return render(request, 'dashboards/admin_teacher_attendance.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 13. ALL STUDENTS
# ═══════════════════════════════════════════════════════════════
class StudentsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'students', 'All Students', 'Students')

        students = Users.objects.select_related('tenant', 'batch').order_by('-enrolled_at')[:200]
        student_list = []
        for s in students:
            student_list.append({
                'id': str(s.student_id or s.id),
                'name': s.full_name,
                'code': s.userid or '',
                'email': s.email or '',
                'phone': s.phone or '',
                'tenant': s.tenant.name if s.tenant else 'N/A',
                'status': 'ACTIVE' if s.is_active else 'INACTIVE',
                'joined': s.enrolled_at.strftime('%d %b %Y') if s.enrolled_at else '',
            })

        ctx.update({
            'students': student_list,
            'total_students': Users.objects.count(),
            'active_students': Users.objects.filter(is_active=True).count(),
            'inactive_students': Users.objects.filter(is_active=False).count(),
        })
        return render(request, 'dashboards/admin_students.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 14. STUDENT ATTENDANCE
# ═══════════════════════════════════════════════════════════════
class StudentAttendanceView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'student-attendance', 'Student Attendance', 'Students')

        from attendance.models import Attendance
        from academics.models import Batch

        today = timezone.now().date()

        # Today's attendance summary by batch
        batches = Batch.objects.filter(status='ACTIVE').order_by('name')
        batch_att = []
        for b in batches:
            present = Attendance.objects.filter(
                user_type='STUDENT', attendance_date=today,
                batch=b, status='PRESENT'
            ).count()
            absent = Attendance.objects.filter(
                user_type='STUDENT', attendance_date=today,
                batch=b, status='ABSENT'
            ).count()
            total = present + absent
            batch_att.append({
                'batch_name': b.name,
                'batch_code': b.code or '',
                'present': present,
                'absent': absent,
                'total': total,
                'pct': round(present / total * 100, 1) if total > 0 else 0,
            })

        # Recent individual records
        recent = Attendance.objects.filter(
            user_type='STUDENT'
        ).order_by('-attendance_date', '-marked_at')[:50]
        records = []
        for a in recent:
            # Resolve student name
            try:
                u = Users.objects.get(Q(student_id=a.user_id) | Q(id=a.user_id))
                name = u.full_name
            except (Users.DoesNotExist, Users.MultipleObjectsReturned):
                name = str(a.user_id)[:8]
            records.append({
                'student': name,
                'date': a.attendance_date.strftime('%d %b %Y') if a.attendance_date else '',
                'batch': a.batch.name if a.batch else 'N/A',
                'status': a.status,
                'source': a.source or '',
            })

        ctx.update({
            'batch_attendance': batch_att,
            'recent_records': records,
            'today_date': today.strftime('%A, %d %B %Y'),
        })
        return render(request, 'dashboards/admin_student_attendance.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 15. LIVE CLASSES
# ═══════════════════════════════════════════════════════════════
class LiveClassesView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'live-classes', 'Live Classes', 'Study Material')

        from classes.models import ScheduledClass

        classes = ScheduledClass.objects.all().order_by('-scheduled_date', '-start_time')[:50]
        class_list = []
        for c in classes:
            class_list.append({
                'id': str(c.id),
                'title': c.title,
                'code': c.class_code or '',
                'teacher': f"{c.teacher.first_name} {c.teacher.last_name}" if c.teacher else 'N/A',
                'batch': c.batch.name if c.batch else 'N/A',
                'date': c.scheduled_date.strftime('%d %b %Y') if c.scheduled_date else '',
                'start_time': c.start_time.strftime('%I:%M %p') if c.start_time else '',
                'end_time': c.end_time.strftime('%I:%M %p') if c.end_time else '',
                'duration': c.duration_minutes or 0,
                'viewers': c.total_unique_viewers or 0,
                'status': c.status,
                'youtube_url': c.youtube_watch_url or '',
            })

        live_now = [c for c in class_list if c['status'] == 'LIVE']
        scheduled = [c for c in class_list if c['status'] == 'SCHEDULED']

        ctx.update({
            'classes': class_list,
            'live_count': len(live_now),
            'scheduled_count': len(scheduled),
            'total_classes': len(class_list),
        })
        return render(request, 'dashboards/admin_live_classes.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 16. STUDY MATERIALS
# ═══════════════════════════════════════════════════════════════
class StudyMaterialsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'study-materials', 'Study Materials', 'Study Material')

        from materials.models import StudyMaterial

        materials = StudyMaterial.objects.filter(is_deleted=False).order_by('-created_at')[:100]
        mat_list = []
        for m in materials:
            mat_list.append({
                'id': str(m.id),
                'title': m.title,
                'code': m.material_code or '',
                'type': m.material_type or '',
                'subject': str(m.subject) if m.subject else 'N/A',
                'views': m.view_count or 0,
                'downloads': m.download_count or 0,
                'is_published': m.is_published,
                'created': m.created_at.strftime('%d %b %Y') if m.created_at else '',
            })

        ctx.update({
            'materials': mat_list,
            'total_materials': StudyMaterial.objects.filter(is_deleted=False).count(),
            'published_materials': StudyMaterial.objects.filter(is_deleted=False, is_published=True).count(),
        })
        return render(request, 'dashboards/admin_study_materials.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 17. ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════
class AnnouncementsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'announcements', 'Announcements', 'Communication')

        from communication.models import Announcement

        announcements = Announcement.objects.filter(is_deleted=False).order_by('-created_at')
        ann_list = []
        for a in announcements:
            ann_list.append({
                'id': str(a.id),
                'title': a.title,
                'type': a.announcement_type or 'General',
                'audience': a.target_audience or 'All',
                'is_published': a.is_published,
                'is_pinned': a.is_pinned,
                'views': a.view_count or 0,
                'date': a.published_at.strftime('%d %b %Y') if a.published_at else (a.created_at.strftime('%d %b %Y') if a.created_at else ''),
            })

        ctx.update({
            'announcements': ann_list,
            'total_announcements': len(ann_list),
            'published_count': sum(1 for a in ann_list if a['is_published']),
        })
        return render(request, 'dashboards/admin_announcements.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 18. SUPPORT TICKETS
# ═══════════════════════════════════════════════════════════════
class TicketsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'tickets', 'Support Tickets', 'Communication')

        from communication.models import SupportTicket

        tickets = SupportTicket.objects.all().order_by('-created_at')
        ticket_list = []
        for t in tickets:
            ticket_list.append({
                'id': str(t.id),
                'number': t.ticket_number or '',
                'title': t.title,
                'category': t.category or '',
                'priority': t.priority or 'MEDIUM',
                'status': t.status,
                'submitted_by': t.submitted_by_name or 'Unknown',
                'assigned_to': str(t.assigned_to_id)[:8] if t.assigned_to_id else 'Unassigned',
                'created': t.created_at.strftime('%d %b %Y') if t.created_at else '',
            })

        ctx.update({
            'tickets': ticket_list,
            'total_tickets': len(ticket_list),
            'open_tickets': sum(1 for t in ticket_list if t['status'] in ['OPEN', 'IN_PROGRESS', 'PENDING']),
            'resolved_tickets': sum(1 for t in ticket_list if t['status'] in ['RESOLVED', 'CLOSED']),
        })
        return render(request, 'dashboards/admin_tickets.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 19. TENANTS / CENTERS
# ═══════════════════════════════════════════════════════════════
class TenantsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'tenants', 'Tenants / Centers', 'System')

        tenants = Tenant.objects.all().order_by('name')
        tenant_list = []
        for t in tenants:
            students = Users.objects.filter(tenant=t).count()
            teachers = Teacher.objects.filter(tenant=t).count()
            tenant_list.append({
                'id': str(t.id),
                'name': t.name,
                'code': t.code,
                'students': students,
                'teachers': teachers,
            })

        ctx.update({
            'tenants': tenant_list,
            'total_tenants': len(tenant_list),
        })
        return render(request, 'dashboards/admin_tenants.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 20. SETTINGS
# ═══════════════════════════════════════════════════════════════
class SettingsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'settings', 'Settings', 'System')

        from system_config.models import SystemSetting, FeatureFlag

        settings_list = SystemSetting.objects.filter(is_editable=True).order_by('category', 'setting_key')
        setting_items = []
        for s in settings_list:
            setting_items.append({
                'id': str(s.id),
                'key': s.setting_key,
                'value': s.setting_value or '',
                'category': s.category or 'General',
                'type': s.value_type or 'string',
                'description': (s.description or '')[:100],
                'is_secret': s.is_secret,
            })

        flags = FeatureFlag.objects.all().order_by('flag_key')
        flag_list = []
        for f in flags:
            flag_list.append({
                'id': str(f.id),
                'key': f.flag_key,
                'name': f.flag_name or f.flag_key,
                'description': (f.description or '')[:100],
                'enabled': f.is_enabled,
                'rollout': f.rollout_percentage or 100,
            })

        ctx.update({
            'settings': setting_items,
            'feature_flags': flag_list,
            'total_settings': len(setting_items),
            'total_flags': len(flag_list),
        })
        return render(request, 'dashboards/admin_settings.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 21. AUDIT & GOVERNANCE
# ═══════════════════════════════════════════════════════════════
class AuditView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'audit', 'Audit & Governance', 'System')

        now = timezone.now()
        audits = AuditLog.objects.all().order_by('-created_at')[:100]
        audit_list = []
        for a in audits:
            audit_list.append({
                'id': str(a.id),
                'user': a.username or a.user_type or 'System',
                'user_type': a.user_type or '',
                'action': a.action,
                'description': (a.action_description or '')[:100],
                'resource_type': a.resource_type or '',
                'resource_name': a.resource_name or '',
                'severity': a.severity or 'INFO',
                'ip': a.ip_address or '',
                'time': _time_ago(a.created_at, now),
                'timestamp': a.created_at.strftime('%d %b %Y %H:%M') if a.created_at else '',
            })

        today = now.date()
        ctx.update({
            'audits': audit_list,
            'total_audits': AuditLog.objects.count(),
            'today_audits': AuditLog.objects.filter(created_at__date=today).count(),
            'security_events': AuditLog.objects.filter(is_security_event=True).count(),
        })
        return render(request, 'dashboards/admin_audit.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 22. PROFILE
# ═══════════════════════════════════════════════════════════════
class ProfileView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'profile', 'My Profile')

        user_id = request.session.get('user_id')
        try:
            admin = Admin.objects.get(id=user_id)
            ctx['profile'] = {
                'name': f"{admin.first_name} {admin.last_name}",
                'email': admin.email,
                'phone': admin.phone or '',
                'role': admin.role or 'SUPER_ADMIN',
                'status': admin.status,
                'joined': admin.created_at.strftime('%d %b %Y') if admin.created_at else '',
                'last_login': admin.last_login_at.strftime('%d %b %Y %H:%M') if admin.last_login_at else 'N/A',
            }
        except Admin.DoesNotExist:
            ctx['profile'] = {
                'name': request.session.get('user_name', 'Admin'),
                'email': request.session.get('user_email', ''),
                'phone': '', 'role': 'ADMIN', 'status': 'ACTIVE',
                'joined': '', 'last_login': '',
            }

        return render(request, 'dashboards/admin_profile.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 23. NOTIFICATIONS (full page)
# ═══════════════════════════════════════════════════════════════
class NotificationsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'notifications', 'Notifications')

        try:
            from communication.models import Notification
            notif_list = Notification.objects.filter(
                user_type='ADMIN'
            ).order_by('-created_at')[:50]
            items = []
            now = timezone.now()
            for n in notif_list:
                items.append({
                    'id': str(n.id),
                    'title': n.title,
                    'message': (n.message or '')[:150],
                    'type': n.notification_type or '',
                    'is_read': n.is_read,
                    'time': _time_ago(n.created_at, now),
                    'url': n.action_url or '#',
                })
            ctx['all_notifications'] = items
            ctx['unread_count'] = sum(1 for i in items if not i['is_read'])
        except Exception:
            ctx['all_notifications'] = []
            ctx['unread_count'] = 0

        return render(request, 'dashboards/admin_notifications.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 24. STAFF ROLES MANAGEMENT
# ═══════════════════════════════════════════════════════════════
class StaffRolesView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'staff_roles', 'Staff Roles & Permissions')

        from accounts.models import StaffRole

        roles = StaffRole.objects.all().order_by('level', 'name')
        role_list = []
        perm_fields = [
            'can_manage_students', 'can_manage_teachers', 'can_manage_exams',
            'can_manage_attendance', 'can_manage_content', 'can_manage_finance',
            'can_manage_settings', 'can_manage_integrations', 'can_view_reports',
            'can_export_data', 'can_manage_roles', 'can_view_audit',
            'can_manage_website', 'can_manage_ai',
        ]
        for r in roles:
            granted = [f.replace('can_', '').replace('_', ' ').title() for f in perm_fields if getattr(r, f, False)]
            role_list.append({
                'id': str(r.id),
                'name': r.name,
                'level': r.level,
                'level_label': r.get_level_display(),
                'description': r.description or '',
                'permissions_count': len(granted),
                'permissions': granted,
                'staff_count': r.staff_admins.count(),
                'is_active': r.is_active,
                'created': r.created_at.strftime('%d %b %Y') if r.created_at else '',
            })

        # Staff assignments
        admins = Admin.objects.select_related('staff_role').all()
        staff_list = []
        for a in admins:
            staff_list.append({
                'id': str(a.id),
                'name': f'{a.first_name} {a.last_name}'.strip() or a.email,
                'email': a.email,
                'role_name': a.staff_role.name if a.staff_role else 'Unassigned',
                'role_level': a.staff_role.level if a.staff_role else '',
                'status': a.status,
            })

        ctx.update({
            'roles': role_list,
            'staff_list': staff_list,
            'total_roles': len(role_list),
            'level_counts': {
                'super_admin': sum(1 for r in role_list if r['level'] == 'SUPER_ADMIN'),
                'admin': sum(1 for r in role_list if r['level'] == 'ADMIN'),
                'operator': sum(1 for r in role_list if r['level'] == 'OPERATOR'),
            },
        })
        return render(request, 'dashboards/admin_staff_roles.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 25. INTEGRATIONS / CONFIGURATION
# ═══════════════════════════════════════════════════════════════
class IntegrationsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'integrations', 'Integrations & Configuration')

        from system_config.models import IntegrationConfig

        configs = IntegrationConfig.objects.all().order_by('integration_type', 'name')
        integrations = []
        for c in configs:
            integrations.append({
                'id': str(c.id),
                'name': c.name,
                'type': c.integration_type,
                'type_label': c.get_integration_type_display(),
                'provider': c.provider or '',
                'is_active': c.is_active,
                'health': c.health_status,
                'health_label': c.get_health_status_display(),
                'endpoint': c.api_endpoint or '',
                'model_name': c.model_name or '',
                'max_tokens': c.max_tokens,
                'temperature': float(c.temperature) if c.temperature else 0.7,
                'rate_limit': c.max_requests_per_hour or 0,
                'daily_budget': float(c.daily_budget_limit) if c.daily_budget_limit else 0,
                'monthly_budget': float(c.monthly_budget_limit) if c.monthly_budget_limit else 0,
                'channel_name': c.channel_name or '',
                'auto_sync': c.auto_sync_videos,
                'updated': c.updated_at.strftime('%d %b %Y %H:%M') if c.updated_at else '',
            })

        # Group by type
        type_groups = {}
        for i in integrations:
            tg = type_groups.setdefault(i['type_label'], [])
            tg.append(i)

        ctx.update({
            'integrations': integrations,
            'type_groups': type_groups,
            'total_integrations': len(integrations),
            'enabled_count': sum(1 for i in integrations if i['is_active']),
            'healthy_count': sum(1 for i in integrations if i['health'] == 'HEALTHY'),
            'degraded_count': sum(1 for i in integrations if i['health'] == 'DEGRADED'),
            'down_count': sum(1 for i in integrations if i['health'] == 'DOWN'),
        })
        return render(request, 'dashboards/admin_integrations.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 26. REPORTS CENTER
# ═══════════════════════════════════════════════════════════════
class ReportsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'reports', 'Reports Center')

        from system_config.models import ReportTemplate
        from assessments.models import Test, TestAttempt
        from attendance.models import Attendance

        # Report templates
        templates = ReportTemplate.objects.filter(is_active=True).order_by('report_type', 'name')
        template_list = []
        for t in templates:
            template_list.append({
                'id': str(t.id),
                'name': t.name,
                'type': t.report_type,
                'type_label': t.get_report_type_display(),
                'format': t.default_format,
                'format_label': t.get_default_format_display(),
                'is_scheduled': t.is_scheduled,
                'schedule': t.schedule_cron or '',
                'description': t.description or '',
            })

        now = timezone.now()
        today = now.date()

        # Quick stats for report dashboard
        ctx.update({
            'templates': template_list,
            'total_templates': len(template_list),
            'total_students': Users.objects.filter(is_active=True).count(),
            'total_teachers': Teacher.objects.count(),
            'total_tests': Test.objects.count(),
            'total_attempts': TestAttempt.objects.count(),
            'total_attendance': Attendance.objects.count(),
            'today_attendance': Attendance.objects.filter(attendance_date=today).count(),
            'report_types': [
                {'value': 'STUDENT', 'label': 'Student Report', 'icon': 'fa-user-graduate', 'color': '#8b5cf6'},
                {'value': 'TEACHER', 'label': 'Teacher Report', 'icon': 'fa-chalkboard-teacher', 'color': '#2563eb'},
                {'value': 'ATTENDANCE', 'label': 'Attendance Report', 'icon': 'fa-calendar-check', 'color': '#f59e0b'},
                {'value': 'EXAM', 'label': 'Exam Report', 'icon': 'fa-file-alt', 'color': '#ef4444'},
                {'value': 'CENTER', 'label': 'Center Report', 'icon': 'fa-building', 'color': '#16a34a'},
                {'value': 'FINANCIAL', 'label': 'Financial Report', 'icon': 'fa-rupee-sign', 'color': '#ec4899'},
                {'value': 'COMBINED', 'label': 'Combined Report', 'icon': 'fa-layer-group', 'color': '#0891b2'},
            ],
        })

        # ── Handle report generation request ──
        report_type = request.GET.get('report_type')
        fmt = request.GET.get('format', 'excel')
        if report_type:
            return self._generate_report(request, report_type, fmt)

        return render(request, 'dashboards/admin_reports.html', ctx)

    def _generate_report(self, request, report_type, fmt):
        """Generate and return a report as a downloadable file."""
        import csv
        import io
        import json as json_mod
        from django.http import HttpResponse

        report_type = report_type.lower()
        rows = []
        headers = []

        if report_type == 'attendance':
            from attendance.models import Attendance
            headers = ['Date', 'User Type', 'User ID', 'Status', 'Source', 'Check In', 'Check Out']
            qs = Attendance.objects.all().order_by('-attendance_date')
            date_range = request.GET.get('date_range', 'month')
            user_type = request.GET.get('user_type', 'all')
            batch_id = request.GET.get('batch')
            today = date.today()
            if date_range == 'today':
                qs = qs.filter(attendance_date=today)
            elif date_range == 'week':
                qs = qs.filter(attendance_date__gte=today - timedelta(days=7))
            elif date_range == 'month':
                qs = qs.filter(attendance_date__gte=today - timedelta(days=30))
            elif date_range == 'quarter':
                qs = qs.filter(attendance_date__gte=today - timedelta(days=90))
            if user_type and user_type != 'all':
                qs = qs.filter(user_type=user_type.upper())
            if batch_id:
                qs = qs.filter(batch_id=batch_id)
            for a in qs[:5000]:
                rows.append([
                    str(a.attendance_date), a.user_type, str(a.user_id),
                    a.status, a.source,
                    str(a.check_in_time or ''), str(a.check_out_time or ''),
                ])

        elif report_type == 'students':
            headers = ['Code', 'Name', 'Email', 'Phone', 'Class', 'Status', 'Fee Status', 'Exam Target']
            qs = Users.objects.all().order_by('first_name')
            status = request.GET.get('status', 'all')
            cls = request.GET.get('class', '')
            fee = request.GET.get('fee_status', '')
            if status and status != 'all':
                qs = qs.filter(status=status)
            if cls:
                qs = qs.filter(student_class=cls.replace('CLASS_', ''))
            if fee:
                qs = qs.filter(fee_status=fee)
            for s in qs[:5000]:
                rows.append([
                    s.student_code, f"{s.first_name} {s.last_name}", s.email, s.phone,
                    s.student_class, s.status,
                    getattr(s, 'fee_status', ''), s.exam_target,
                ])

        elif report_type == 'teachers':
            headers = ['Code', 'Name', 'Email', 'Phone', 'Department', 'Employment Type', 'Status']
            qs = Teacher.objects.all().order_by('first_name')
            status = request.GET.get('status', 'all')
            if status and status != 'all':
                qs = qs.filter(status=status)
            emp_type = request.GET.get('employment_type', '')
            if emp_type:
                qs = qs.filter(employment_type=emp_type)
            for t in qs[:5000]:
                rows.append([
                    t.teacher_code, f"{t.first_name} {t.last_name}", t.email, t.phone,
                    getattr(t, 'department', ''), getattr(t, 'employment_type', ''), t.status,
                ])
        else:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest(f"Unknown report type: {report_type}")

        # Format output
        fmt = fmt.lower()
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_type}_report_{timestamp}"

        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response

        elif fmt == 'json':
            data = [dict(zip(headers, row)) for row in rows]
            response = HttpResponse(
                json_mod.dumps(data, indent=2, default=str),
                content_type='application/json',
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
            return response

        elif fmt == 'excel':
            try:
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = report_type.title()
                ws.append(headers)
                for row in rows:
                    ws.append(row)
                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                response = HttpResponse(
                    buf.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
                return response
            except ImportError:
                # Fallback to CSV if openpyxl not installed
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
                writer = csv.writer(response)
                writer.writerow(headers)
                writer.writerows(rows)
                return response

        elif fmt == 'pdf':
            # Simple text-based PDF fallback
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response

        # Default: CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response


# ═══════════════════════════════════════════════════════════════
# 26b. REPORT RUN — Execute saved report template
# ═══════════════════════════════════════════════════════════════
class ReportRunView(View):
    """Run a saved ReportTemplate and download the results."""
    def get(self, request, template_id):
        auth = _require_admin(request)
        if auth:
            return auth

        from system_config.models import ReportTemplate
        try:
            template = ReportTemplate.objects.get(id=template_id, is_active=True)
        except ReportTemplate.DoesNotExist:
            from django.http import Http404
            raise Http404("Report template not found.")

        # Build request params from template config
        params = request.GET.copy()
        params['report_type'] = template.report_type.lower()
        params['format'] = template.default_format.lower()

        # Apply stored filters
        if template.filters_json:
            for key, val in template.filters_json.items():
                if key not in params:
                    params[key] = val

        # Use ReportsView's generate method
        reports_view = ReportsView()
        return reports_view._generate_report(request, params.get('report_type', 'students'), params.get('format', 'csv'))


# ═══════════════════════════════════════════════════════════════
# 27. WEBSITE SETTINGS
# ═══════════════════════════════════════════════════════════════
class WebsiteSettingsView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'website_settings', 'Website & Frontend Settings')

        from system_config.models import WebsiteSetting

        settings_qs = WebsiteSetting.objects.filter(is_active=True).order_by('section', 'sort_order')
        sections = {}
        for s in settings_qs:
            section_label = s.get_section_display()
            sec = sections.setdefault(s.section, {
                'label': section_label,
                'key': s.section,
                'items': [],
            })
            sec['items'].append({
                'id': str(s.id),
                'key': s.setting_key,
                'value': s.setting_value or '',
                'json': s.setting_json,
                'media_url': s.media_url or '',
                'order': s.sort_order,
            })

        section_meta = {
            'HERO': {'icon': 'fa-desktop', 'color': '#8b5cf6', 'desc': 'Hero banner, headline, CTA'},
            'ABOUT': {'icon': 'fa-info-circle', 'color': '#2563eb', 'desc': 'About us section'},
            'PROGRAMS': {'icon': 'fa-graduation-cap', 'color': '#16a34a', 'desc': 'Programs & courses listing'},
            'TESTIMONIALS': {'icon': 'fa-quote-left', 'color': '#f59e0b', 'desc': 'Student testimonials'},
            'FOOTER': {'icon': 'fa-shoe-prints', 'color': '#64748b', 'desc': 'Footer links & info'},
            'SEO': {'icon': 'fa-search', 'color': '#0891b2', 'desc': 'SEO meta tags, titles'},
            'SOCIAL': {'icon': 'fa-share-alt', 'color': '#ec4899', 'desc': 'Social media links'},
            'BRANDING': {'icon': 'fa-palette', 'color': '#6366f1', 'desc': 'Logo, brand colors, fonts'},
            'CONTACT': {'icon': 'fa-envelope', 'color': '#ef4444', 'desc': 'Contact info & form'},
            'CUSTOM': {'icon': 'fa-cog', 'color': '#78716c', 'desc': 'Custom sections'},
        }

        ctx.update({
            'sections': sections,
            'section_meta': section_meta,
            'total_settings': settings_qs.count(),
            'active_sections': len(sections),
        })
        return render(request, 'dashboards/admin_website_settings.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 28. EXAM MANAGEMENT (auto-grading hub)
# ═══════════════════════════════════════════════════════════════
class ExamManagementView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'exam_management', 'Exam Management & Auto-Grading')

        from assessments.models import Test, TestAttempt, Question

        now = timezone.now()
        today = now.date()

        tests = Test.objects.all().order_by('-created_at')[:50]
        test_list = []
        for t in tests:
            q_count = Question.objects.filter(test_section__test=t).count()
            attempt_count = TestAttempt.objects.filter(test=t).count()
            evaluated = TestAttempt.objects.filter(test=t, status='EVALUATED').count()
            pending = TestAttempt.objects.filter(test=t, status='SUBMITTED').count()
            pass_count = TestAttempt.objects.filter(test=t, result='PASS').count()
            avg_score = TestAttempt.objects.filter(test=t, status='EVALUATED').aggregate(
                avg=Avg('percentage'))['avg']

            test_list.append({
                'id': str(t.id),
                'title': t.title,
                'test_type': t.test_type,
                'status': t.status,
                'total_marks': t.total_marks,
                'passing_marks': t.passing_marks,
                'duration': t.duration_minutes,
                'questions': q_count,
                'attempts': attempt_count,
                'evaluated': evaluated,
                'pending_eval': pending,
                'pass_count': pass_count,
                'pass_rate': round(pass_count / attempt_count * 100, 1) if attempt_count else 0,
                'avg_score': round(avg_score, 1) if avg_score else 0,
                'start_time': t.start_time.strftime('%d %b %Y %H:%M') if t.start_time else '',
                'end_time': t.end_time.strftime('%d %b %Y %H:%M') if t.end_time else '',
                'created': t.created_at.strftime('%d %b %Y') if t.created_at else '',
            })

        # Summary
        total_tests = Test.objects.count()
        active_tests = Test.objects.filter(status='ACTIVE').count()
        total_attempts = TestAttempt.objects.count()
        pending_grading = TestAttempt.objects.filter(status='SUBMITTED').count()
        auto_graded = TestAttempt.objects.filter(status='EVALUATED').count()

        ctx.update({
            'tests': test_list,
            'total_tests': total_tests,
            'active_tests': active_tests,
            'total_attempts': total_attempts,
            'pending_grading': pending_grading,
            'auto_graded': auto_graded,
            'overall_pass_rate': round(
                TestAttempt.objects.filter(result='PASS').count() / total_attempts * 100, 1
            ) if total_attempts else 0,
        })
        return render(request, 'dashboards/admin_exam_management.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 29. COMPLIANCE & SESSION TRACKING (consolidated)
# ═══════════════════════════════════════════════════════════════
class ComplianceView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'compliance', 'Audit, Compliance & Sessions')

        from audit.models import AuditLog
        from sessions_tracking.models import UserSession, LoginHistory, UserDevice

        now = timezone.now()
        today = now.date()

        # Recent audit logs
        recent_logs = AuditLog.objects.all().order_by('-created_at')[:50]
        audit_list = []
        for log in recent_logs:
            audit_list.append({
                'id': str(log.id),
                'action': log.action,
                'entity_type': log.entity_type or '',
                'entity_id': str(log.entity_id)[:8] if log.entity_id else '',
                'user_type': log.user_type or '',
                'user_id': str(log.user_id)[:8] if log.user_id else '',
                'ip': log.ip_address or '',
                'details': (str(log.details) or '')[:100] if log.details else '',
                'time': _time_ago(log.created_at, now),
                'timestamp': log.created_at.strftime('%d %b %Y %H:%M') if log.created_at else '',
            })

        # Session stats
        active_sessions = UserSession.objects.filter(status='ACTIVE').count()
        total_sessions_today = UserSession.objects.filter(started_at__date=today).count()

        # Login history
        logins_today = LoginHistory.objects.filter(attempted_at__date=today).count()
        failed_logins = LoginHistory.objects.filter(attempted_at__date=today, result='FAILED').count()
        successful_logins = LoginHistory.objects.filter(attempted_at__date=today, result='SUCCESS').count()

        # Login trend (7 days)
        login_trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            success = LoginHistory.objects.filter(attempted_at__date=d, result='SUCCESS').count()
            failed = LoginHistory.objects.filter(attempted_at__date=d, result='FAILED').count()
            login_trend.append({
                'date': d.strftime('%a %d'),
                'success': success,
                'failed': failed,
                'total': success + failed,
            })

        # Device stats
        device_stats = UserDevice.objects.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # Audit action breakdown
        action_breakdown = AuditLog.objects.filter(
            created_at__date__gte=today - timedelta(days=7)
        ).values('action').annotate(count=Count('id')).order_by('-count')[:10]

        ctx.update({
            'audit_logs': audit_list,
            'total_logs': AuditLog.objects.count(),
            'active_sessions': active_sessions,
            'total_sessions_today': total_sessions_today,
            'logins_today': logins_today,
            'failed_logins': failed_logins,
            'successful_logins': successful_logins,
            'login_trend': login_trend,
            'device_stats': list(device_stats),
            'action_breakdown': list(action_breakdown),
        })
        return render(request, 'dashboards/admin_compliance.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 30. AI FEATURES MANAGEMENT
# ═══════════════════════════════════════════════════════════════
class AIFeaturesView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'ai_features', 'AI Features & Configuration')

        from system_config.models import AIFeatureConfig, IntegrationConfig

        # AI Feature configs
        ai_configs = AIFeatureConfig.objects.all().order_by('feature_name')
        features = []
        for c in ai_configs:
            features.append({
                'id': str(c.id),
                'name': c.feature_name,
                'description': c.description or '',
                'is_enabled': c.is_enabled,
                'model_provider': c.model_provider or '',
                'model_name': c.model_name or '',
                'max_tokens': c.max_tokens_per_request,
                'daily_limit': c.daily_request_limit,
                'temperature': float(c.temperature) if c.temperature else 0.7,
                'updated': c.updated_at.strftime('%d %b %Y') if c.updated_at else '',
            })

        # LLM integrations
        llm_integrations = IntegrationConfig.objects.filter(
            integration_type='LLM'
        ).order_by('name')
        llm_list = []
        for i in llm_integrations:
            llm_list.append({
                'id': str(i.id),
                'name': i.name,
                'provider': i.provider or '',
                'model': i.model_name or '',
                'health': i.health_status,
                'is_active': i.is_active,
                'max_tokens': i.max_tokens,
                'temperature': float(i.temperature) if i.temperature else 0,
                'rate_limit': i.max_requests_per_hour or 0,
            })

        ai_capabilities = [
            {'name': 'Test Analysis', 'desc': 'AI-powered test performance analysis with radar charts', 'icon': 'fa-chart-radar', 'status': 'active'},
            {'name': 'Study Recommendations', 'desc': 'Personalized study plans based on performance data', 'icon': 'fa-brain', 'status': 'active'},
            {'name': 'Question Generation', 'desc': 'Auto-generate questions from study materials', 'icon': 'fa-magic', 'status': 'beta'},
            {'name': 'Answer Evaluation', 'desc': 'AI-assisted subjective answer evaluation', 'icon': 'fa-check-double', 'status': 'beta'},
            {'name': 'Doubt Resolution', 'desc': 'Chatbot for answering student doubts', 'icon': 'fa-robot', 'status': 'planned'},
            {'name': 'Content Summarization', 'desc': 'Auto-summarize study materials and lectures', 'icon': 'fa-compress-alt', 'status': 'planned'},
        ]

        ctx.update({
            'features': features,
            'llm_integrations': llm_list,
            'ai_capabilities': ai_capabilities,
            'total_features': len(features),
            'enabled_features': sum(1 for f in features if f['is_enabled']),
            'total_llm': len(llm_list),
        })
        return render(request, 'dashboards/admin_ai_features.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 31. DASHBOARD INTEGRATION (links to Student/Teacher SPAs)
# ═══════════════════════════════════════════════════════════════
class DashboardIntegrationView(View):
    def get(self, request):
        auth = _require_admin(request)
        if auth:
            return auth
        ctx = _admin_ctx(request, 'dashboard_integration', 'Dashboard Integration')

        now = timezone.now()
        today = now.date()

        # Student dashboard stats
        total_students = Users.objects.count()
        active_students = Users.objects.filter(is_active=True).count()

        # Teacher dashboard stats
        total_teachers = Teacher.objects.count()
        active_teachers = Teacher.objects.filter(status='ACTIVE').count()

        # Recent activity
        from sessions_tracking.models import LoginHistory
        student_logins_today = LoginHistory.objects.filter(
            attempted_at__date=today, user_type='STUDENT', result='SUCCESS'
        ).count()
        teacher_logins_today = LoginHistory.objects.filter(
            attempted_at__date=today, user_type='TEACHER', result='SUCCESS'
        ).count()

        ctx.update({
            'dashboards': [
                {
                    'name': 'Student Dashboard',
                    'url': '/student/dashboard/',
                    'icon': 'fa-user-graduate',
                    'color': '#8b5cf6',
                    'total_users': total_students,
                    'active_users': active_students,
                    'logins_today': student_logins_today,
                    'features': ['AI Test Analysis', 'Study Materials', 'Attendance', 'Exam Results', 'Help & Support'],
                    'status': 'live',
                },
                {
                    'name': 'Teacher Dashboard',
                    'url': '/teacher/dashboard/',
                    'icon': 'fa-chalkboard-teacher',
                    'color': '#2563eb',
                    'total_users': total_teachers,
                    'active_users': active_teachers,
                    'logins_today': teacher_logins_today,
                    'features': ['Class Management', 'Test Creation', 'Grading', 'Attendance', 'Analytics'],
                    'status': 'live',
                },
            ],
            'student_dashboard_url': '/student/dashboard/',
            'teacher_dashboard_url': '/teacher/dashboard/',
        })
        return render(request, 'dashboards/admin_dashboard_integration.html', ctx)


# ═══════════════════════════════════════════════════════════════
# 32. AUTO-GRADE ENDPOINT (POST)
# ═══════════════════════════════════════════════════════════════
class AutoGradeView(View):
    """Trigger auto-grading for a specific test."""
    def post(self, request, test_id):
        auth = _require_admin(request)
        if auth:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        from assessments.models import Test
        from assessments.services import auto_grade_test

        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            return JsonResponse({'error': 'Test not found'}, status=404)

        results = auto_grade_test(test)
        return JsonResponse({
            'success': True,
            'test': test.title,
            'graded_count': len([r for r in results if 'error' not in r]),
            'error_count': len([r for r in results if 'error' in r]),
            'results': results,
        })

    def get(self, request, test_id):
        """Grade and show results page."""
        auth = _require_admin(request)
        if auth:
            return auth

        from assessments.models import Test, TestAttempt
        from assessments.services import auto_grade_test, generate_test_report

        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            return redirect('/staff/exam-management/')

        # Auto-grade pending
        pending = TestAttempt.objects.filter(
            test=test, status__in=['SUBMITTED', 'AUTO_SUBMITTED']
        ).count()

        grading_results = []
        if pending > 0:
            grading_results = auto_grade_test(test)

        report = generate_test_report(test)

        ctx = _admin_ctx(request, 'exam_management', f'Grading: {test.title}',
                        breadcrumb_parent='Exam Management',
                        breadcrumb_parent_url='/staff/exam-management/')
        ctx.update({
            'test': {
                'id': str(test.id),
                'title': test.title,
                'total_marks': test.total_marks,
                'passing_marks': test.passing_marks,
            },
            'grading_results': grading_results,
            'report': report,
            'pending_count': pending,
        })
        return render(request, 'dashboards/admin_grade_results.html', ctx)
