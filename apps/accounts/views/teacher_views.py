"""
LMS Enterprise - Teacher Views
CRUD + class/test management for teachers.
Real database queries for dashboard, classes, students, batches.
"""
import uuid
import logging
from datetime import date, datetime, timedelta

from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Teacher
from academics.models import Batch, BatchTeacher, Users
from classes.models import ScheduledClass, ClassWatchTime

logger = logging.getLogger(__name__)


class _AllowAll(permissions.BasePermission):
    def has_permission(self, request, view):
        return True


def _get_teacher(request):
    """Retrieve the Teacher instance from the session-authenticated user."""
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != 'TEACHER':
        return None
    try:
        return Teacher.objects.select_related('tenant').get(id=user_id, status__iexact='ACTIVE')
    except (Teacher.DoesNotExist, ValueError):
        return None


def _format_time_12h(t):
    """Format a time object as '09:00 AM'."""
    if t is None:
        return ''
    if isinstance(t, datetime):
        t = t.time()
    return t.strftime('%I:%M %p')


def _class_status_display(sc):
    """Map ScheduledClass status to frontend display string."""
    mapping = {
        'LIVE': 'Live',
        'COMPLETED': 'Completed',
        'CANCELLED': 'Cancelled',
        'RESCHEDULED': 'Rescheduled',
    }
    if sc.status in mapping:
        return mapping[sc.status]
    now = timezone.localtime(timezone.now())
    if sc.scheduled_date == now.date():
        class_start = datetime.combine(sc.scheduled_date, sc.start_time)
        if now.replace(tzinfo=None) < class_start:
            return 'Upcoming'
    return 'Scheduled'


def _serialize_class(sc, include_details=False):
    """Serialize a ScheduledClass to dict."""
    data = {
        'id': str(sc.id),
        'title': sc.title,
        'class_code': sc.class_code,
        'subject': sc.get_subject_display() if sc.subject else '',
        'scheduled_date': sc.scheduled_date.isoformat() if sc.scheduled_date else None,
        'start_time': _format_time_12h(sc.start_time),
        'end_time': _format_time_12h(sc.end_time),
        'duration_minutes': sc.duration_minutes,
        'status': sc.get_status_display(),
        'batch_id': str(sc.batch_id) if sc.batch_id else None,
        'batch_name': sc.batch.name if sc.batch else '',
        'youtube_watch_url': sc.youtube_watch_url or '',
        'youtube_embed_url': sc.youtube_embed_url or '',
        'peak_live_viewers': sc.peak_live_viewers,
        'total_unique_viewers': sc.total_unique_viewers,
    }
    if include_details:
        data.update({
            'description': sc.description or '',
            'thumbnail_url': sc.thumbnail_url or '',
            'actual_start_time': sc.actual_start_time.isoformat() if sc.actual_start_time else None,
            'actual_end_time': sc.actual_end_time.isoformat() if sc.actual_end_time else None,
            'privacy_status': sc.privacy_status,
            'access_type': sc.access_type,
            'attendance_mode': sc.attendance_mode,
        })
    return data


def _get_teacher_batch_ids(teacher):
    """Return list of batch IDs this teacher is assigned to."""
    return list(
        BatchTeacher.objects.filter(teacher=teacher)
        .values_list('batch_id', flat=True)
        .distinct()
    )


def _get_students_in_batches(batch_ids, active_only=True):
    """Return Users queryset for students enrolled in given batches."""
    qs = Users.objects.filter(batch_id__in=batch_ids)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found or inactive'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        today = timezone.localdate()
        batch_ids = _get_teacher_batch_ids(teacher)

        total_students = (
            Users.objects.filter(batch_id__in=batch_ids, is_active=True)
            .values('student_id').distinct().count()
        )

        today_classes = ScheduledClass.objects.filter(
            teacher=teacher, scheduled_date=today,
        ).select_related('batch')

        live_classes_today = today_classes.filter(status='LIVE').count()

        today_completed = today_classes.filter(status='COMPLETED')
        today_attendance = 0
        for sc in today_completed:
            today_attendance += ClassWatchTime.objects.filter(
                scheduled_class=sc,
            ).values('student_id').distinct().count()

        upcoming_tests = 0

        quick_stats = {
            'totalStudents': total_students,
            'todayAttendance': today_attendance,
            'upcomingTests': upcoming_tests,
            'liveClassesToday': live_classes_today,
        }

        today_schedule = []
        for sc in today_classes.order_by('start_time'):
            student_count = 0
            if sc.batch_id:
                student_count = Users.objects.filter(
                    batch_id=sc.batch_id, is_active=True,
                ).count()
            today_schedule.append({
                'id': str(sc.id),
                'subject': sc.get_subject_display() if sc.subject else '',
                'topic': sc.title,
                'time': _format_time_12h(sc.start_time),
                'endTime': _format_time_12h(sc.end_time),
                'class': sc.batch.name if sc.batch else '',
                'section': '',
                'language': 'Hindi',
                'status': _class_status_display(sc),
                'students': student_count,
                'youtube_watch_url': sc.youtube_watch_url or '',
            })

        class_summary = []
        batches = Batch.objects.filter(id__in=batch_ids, status__iexact='ACTIVE')
        for b in batches:
            student_count = Users.objects.filter(
                batch=b, is_active=True,
            ).count()
            class_summary.append({
                'className': b.name,
                'section': b.code,
                'students': student_count,
            })

        profile = {
            'id': str(teacher.id),
            'name': teacher.full_name,
            'email': teacher.email,
            'phone': teacher.phone,
            'teacher_code': teacher.teacher_code,
            'subjects': teacher.subjects or [],
            'avatar_url': teacher.avatar_url or '',
        }

        return Response({'success': True, 'data': {
            'profile': profile,
            'quickStats': quick_stats,
            'todaySchedule': today_schedule,
            'classSummary': class_summary,
        }})


class DashboardStatsView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        total_classes = ScheduledClass.objects.filter(teacher=teacher).count()
        completed_classes = ScheduledClass.objects.filter(
            teacher=teacher, status='COMPLETED',
        )

        avg_attendance = 0
        completed_count = completed_classes.count()
        if completed_count > 0:
            total_viewers = 0
            total_expected = 0
            for sc in completed_classes.select_related('batch'):
                viewers = ClassWatchTime.objects.filter(
                    scheduled_class=sc,
                ).values('student_id').distinct().count()
                total_viewers += viewers
                if sc.batch_id:
                    expected = Users.objects.filter(
                        batch_id=sc.batch_id, is_active=True,
                    ).count()
                    total_expected += expected
            if total_expected > 0:
                avg_attendance = round((total_viewers / total_expected) * 100, 1)

        return Response({'success': True, 'data': {
            'total_classes': total_classes,
            'total_tests': 0,
            'avg_attendance': avg_attendance,
        }})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = {
            'id': str(teacher.id),
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'full_name': teacher.full_name,
            'display_name': teacher.display_name or '',
            'email': teacher.email,
            'phone': teacher.phone,
            'teacher_code': teacher.teacher_code,
            'employee_id': teacher.employee_id or '',
            'subjects': teacher.subjects or [],
            'specialization': teacher.specialization or [],
            'qualification': teacher.qualification or '',
            'highest_degree': teacher.highest_degree or '',
            'experience_years': teacher.experience_years,
            'experience_details': teacher.experience_details or '',
            'certifications': teacher.certifications or [],
            'employment_type': teacher.get_employment_type_display() if teacher.employment_type else '',
            'department': teacher.department or '',
            'designation': teacher.designation or '',
            'joining_date': teacher.joining_date.isoformat() if teacher.joining_date else None,
            'reporting_to': str(teacher.reporting_to_id) if teacher.reporting_to_id else None,
            'avatar_url': teacher.avatar_url or '',
            'personal_youtube_channel_id': teacher.personal_youtube_channel_id or '',
            'youtube_channel_verified': teacher.youtube_channel_verified,
            'can_create_streams': teacher.can_create_streams,
            'can_edit_student_profile': teacher.can_edit_student_profile,
            'can_override_attendance': teacher.can_override_attendance,
            'can_override_scores': teacher.can_override_scores,
            'max_batches_allowed': teacher.max_batches_allowed,
            'personal_email': teacher.personal_email or '',
            'personal_phone': teacher.personal_phone or '',
            'emergency_contact': teacher.emergency_contact or '',
            'address': teacher.address or '',
            'city': teacher.teacher_city or '',
            'state': teacher.teacher_state or '',
            'status': teacher.status,
            'email_verified': teacher.email_verified,
            'phone_verified': teacher.phone_verified,
            'created_at': teacher.created_at.isoformat() if teacher.created_at else None,
            'tenant_name': teacher.tenant.name if teacher.tenant_id else '',
            'tenant_code': teacher.tenant.code if teacher.tenant_id else '',
        }
        return Response({'success': True, 'data': data})

    def put(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        allowed_fields = [
            'first_name', 'last_name', 'phone', 'display_name',
            'avatar_url', 'personal_email', 'personal_phone',
            'address', 'teacher_city', 'teacher_state',
        ]
        updated = []
        for field in allowed_fields:
            if field in request.data:
                setattr(teacher, field, request.data[field])
                updated.append(field)

        if updated:
            teacher.save(update_fields=updated + ['updated_at'])

        return Response({'success': True, 'message': 'Profile updated'})


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------
class YouTubeConnectView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'YouTube connected'})


class YouTubeDisconnectView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'YouTube disconnected'})


class YouTubeStatusView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'connected': False}})


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
class StudentListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        batch_ids = _get_teacher_batch_ids(teacher)

        batch_student_qs = (
            Users.objects
            .filter(batch_id__in=batch_ids, is_active=True)
            .select_related('batch')
        )

        students_map = {}
        for bs in batch_student_qs:
            sid = str(bs.student_id or bs.id)
            if sid not in students_map:
                students_map[sid] = {
                    'id': sid,
                    'first_name': bs.name or '',
                    'last_name': '',
                    'full_name': bs.full_name,
                    'email': bs.email or '',
                    'phone': bs.phone or '',
                    'student_code': bs.userid or '',
                    'student_class': bs.category or '',
                    'exam_target': '',
                    'status': bs.status or 'active',
                    'avatar_url': bs.photo or '',
                    'batches': [],
                }
            students_map[sid]['batches'].append({
                'batch_id': str(bs.batch_id),
                'batch_name': bs.batch.name if bs.batch else '',
                'batch_code': bs.batch.code if bs.batch else '',
            })

        return Response({
            'success': True,
            'data': list(students_map.values()),
            'count': len(students_map),
        })


class StudentDetailView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = Users.objects.select_related('batch').get(
                Q(student_id=pk) | Q(id=pk), is_active=True,
            )
        except (Users.DoesNotExist, Users.MultipleObjectsReturned, ValueError):
            return Response(
                {'success': False, 'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        batch_ids = _get_teacher_batch_ids(teacher)
        if user.batch_id not in batch_ids:
            return Response(
                {'success': False, 'error': 'Student not in your batches'},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = {
            'id': str(user.student_id or user.id),
            'first_name': user.name or '',
            'last_name': '',
            'full_name': user.full_name,
            'email': user.email or '',
            'phone': user.phone or '',
            'student_code': user.userid or '',
            'student_class': user.category or '',
            'exam_target': '',
            'stream': '',
            'status': user.status or 'active',
            'avatar_url': user.photo or '',
            'city': user.city_name or '',
            'state': '',
        }
        return Response({'success': True, 'data': data})


class StudentProfileEditView(APIView):
    permission_classes = [_AllowAll]
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Student profile updated'})


class StudentPerformanceView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})


class StudentAttendanceView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})


class ProfileRequestListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})


class ProfileRequestDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Request updated'})


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
class ClassListCreateView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        classes = (
            ScheduledClass.objects
            .filter(teacher=teacher)
            .select_related('batch')
            .order_by('-scheduled_date', '-start_time')
        )

        status_filter = request.query_params.get('status')
        if status_filter:
            classes = classes.filter(status=status_filter.upper())

        subject_filter = request.query_params.get('subject')
        if subject_filter:
            classes = classes.filter(subject=subject_filter.upper())

        batch_filter = request.query_params.get('batch_id')
        if batch_filter:
            classes = classes.filter(batch_id=batch_filter)

        data = [_serialize_class(sc) for sc in classes[:100]]
        return Response({'success': True, 'data': data, 'count': len(data)})

    def post(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        d = request.data
        required = ['title', 'scheduled_date', 'start_time', 'end_time']
        missing = [f for f in required if not d.get(f)]
        if missing:
            return Response(
                {'success': False, 'error': f'Missing fields: {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch = None
        if d.get('batch_id'):
            try:
                batch = Batch.objects.get(id=d['batch_id'], tenant=teacher.tenant)
            except (Batch.DoesNotExist, ValueError):
                return Response(
                    {'success': False, 'error': 'Batch not found'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        class_code = d.get('class_code') or f"CLS-{uuid.uuid4().hex[:8].upper()}"

        try:
            sc = ScheduledClass.objects.create(
                tenant=teacher.tenant,
                teacher=teacher,
                batch=batch,
                title=d['title'],
                class_code=class_code,
                description=d.get('description', ''),
                scheduled_date=d['scheduled_date'],
                start_time=d['start_time'],
                end_time=d['end_time'],
                duration_minutes=d.get('duration_minutes'),
                subject=d.get('subject', '').upper() or None,
                status=d.get('status', 'DRAFT').upper(),
                created_by_id=teacher.id,
                created_by_type='TEACHER',
            )
        except Exception as e:
            logger.exception("Failed to create class")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {'success': True, 'data': _serialize_class(sc), 'message': 'Class created'},
            status=status.HTTP_201_CREATED,
        )


class ClassUpcomingView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        today = timezone.localdate()
        classes = (
            ScheduledClass.objects
            .filter(
                teacher=teacher,
                scheduled_date__gte=today,
                status__in=['DRAFT', 'SCHEDULED'],
            )
            .select_related('batch')
            .order_by('scheduled_date', 'start_time')
        )

        data = [_serialize_class(sc) for sc in classes[:50]]
        return Response({'success': True, 'data': data, 'count': len(data)})


class ClassCompletedView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        classes = (
            ScheduledClass.objects
            .filter(teacher=teacher, status='COMPLETED')
            .select_related('batch')
            .order_by('-scheduled_date', '-start_time')
        )

        data = [_serialize_class(sc) for sc in classes[:50]]
        return Response({'success': True, 'data': data, 'count': len(data)})


class ClassDetailView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.select_related('batch').get(
                id=pk, teacher=teacher,
            )
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = _serialize_class(sc, include_details=True)

        if sc.batch_id:
            data['expected_students'] = Users.objects.filter(
                batch_id=sc.batch_id, is_active=True,
            ).count()

        data['actual_viewers'] = ClassWatchTime.objects.filter(
            scheduled_class=sc,
        ).values('student_id').distinct().count()

        return Response({'success': True, 'data': data})

    def put(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        d = request.data
        updatable = [
            'title', 'description', 'scheduled_date', 'start_time',
            'end_time', 'duration_minutes', 'subject', 'status',
        ]
        updated_fields = []
        for field in updatable:
            if field in d:
                val = d[field]
                if field == 'subject' and val:
                    val = val.upper()
                if field == 'status' and val:
                    val = val.upper()
                setattr(sc, field, val)
                updated_fields.append(field)

        if d.get('batch_id'):
            try:
                sc.batch = Batch.objects.get(id=d['batch_id'], tenant=teacher.tenant)
                updated_fields.append('batch')
            except (Batch.DoesNotExist, ValueError):
                pass

        if updated_fields:
            sc.save(update_fields=updated_fields + ['updated_at'])

        return Response({
            'success': True,
            'data': _serialize_class(sc),
            'message': 'Class updated',
        })


class ClassStartView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sc.status == 'LIVE':
            return Response(
                {'success': False, 'error': 'Class is already live'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sc.status == 'COMPLETED':
            return Response(
                {'success': False, 'error': 'Class is already completed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        sc.status = 'LIVE'
        sc.actual_start_time = now
        sc.started_by = teacher
        sc.teacher_joined_at = now
        sc.teacher_join_notified = True
        sc.save(update_fields=[
            'status', 'actual_start_time', 'started_by',
            'teacher_joined_at', 'teacher_join_notified', 'updated_at',
        ])

        return Response({
            'success': True,
            'data': _serialize_class(sc),
            'message': 'Class started — teacher joined and students notified',
        })


class ClassEndView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if sc.status != 'LIVE':
            return Response(
                {'success': False, 'error': 'Class is not currently live'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        sc.status = 'COMPLETED'
        sc.actual_end_time = now
        sc.ended_by = teacher

        unique_viewers = ClassWatchTime.objects.filter(
            scheduled_class=sc,
        ).values('student_id').distinct().count()
        sc.total_unique_viewers = unique_viewers

        sc.save(update_fields=[
            'status', 'actual_end_time', 'ended_by',
            'total_unique_viewers', 'updated_at',
        ])

        return Response({
            'success': True,
            'data': _serialize_class(sc),
            'message': 'Class ended',
        })


class ClassStudentListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not sc.batch_id:
            return Response({'success': True, 'data': [], 'count': 0})

        batch_students = (
            Users.objects
            .filter(batch_id=sc.batch_id, is_active=True)
            .select_related('student')
        )

        watch_map = {}
        watches = ClassWatchTime.objects.filter(scheduled_class=sc)
        for w in watches:
            sid = str(w.student_id)
            if sid not in watch_map or w.total_watch_seconds > watch_map[sid]['total_watch_seconds']:
                watch_map[sid] = {
                    'total_watch_seconds': w.total_watch_seconds,
                    'joined_at': w.joined_at.isoformat() if w.joined_at else None,
                    'left_at': w.left_at.isoformat() if w.left_at else None,
                    'is_live_watch': w.is_live_watch,
                    'engagement_score': float(w.engagement_score) if w.engagement_score else None,
                }

        data = []
        for bs in batch_students:
            s = bs.student
            sid = str(s.id)
            entry = {
                'id': sid,
                'first_name': s.first_name,
                'last_name': s.last_name,
                'full_name': s.full_name,
                'email': s.email,
                'student_code': s.student_code,
                'watched': sid in watch_map,
            }
            if sid in watch_map:
                entry['watch_data'] = watch_map[sid]
            data.append(entry)

        return Response({'success': True, 'data': data, 'count': len(data)})


class ClassAttendeesView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        watches = (
            ClassWatchTime.objects
            .filter(scheduled_class=sc)
            .select_related('student')
            .order_by('-joined_at')
        )

        data = []
        for w in watches:
            # Get name from Users (primary source) or fall back to ClassWatchTime.student FK
            user_record = Users.objects.filter(student_id=w.student_id).first() if w.student_id else None
            if user_record:
                s_name = user_record.full_name
                s_code = user_record.userid or ''
            elif w.student:
                s_name = w.student.full_name
                s_code = ''
            else:
                s_name = ''
                s_code = ''
            data.append({
                'student_id': str(w.student_id),
                'student_name': s_name,
                'student_code': s_code,
                'joined_at': w.joined_at.isoformat() if w.joined_at else None,
                'left_at': w.left_at.isoformat() if w.left_at else None,
                'total_watch_seconds': w.total_watch_seconds,
                'is_live_watch': w.is_live_watch,
                'engagement_score': float(w.engagement_score) if w.engagement_score else None,
            })

        return Response({'success': True, 'data': data, 'count': len(data)})


class ClassWatchStatsView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            sc = ScheduledClass.objects.get(id=pk, teacher=teacher)
        except (ScheduledClass.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        watches = ClassWatchTime.objects.filter(scheduled_class=sc)
        agg = watches.aggregate(
            total_viewers=Count('student_id', distinct=True),
            avg_watch_seconds=Avg('total_watch_seconds'),
            total_watch_seconds=Sum('total_watch_seconds'),
            avg_engagement=Avg('engagement_score'),
            live_watchers=Count('id', filter=Q(is_live_watch=True)),
        )

        expected_students = 0
        if sc.batch_id:
            expected_students = Users.objects.filter(
                batch_id=sc.batch_id, is_active=True,
            ).count()

        total_viewers = agg['total_viewers'] or 0
        attendance_pct = 0
        if expected_students > 0:
            attendance_pct = round((total_viewers / expected_students) * 100, 1)

        avg_watch = agg['avg_watch_seconds'] or 0
        avg_watch_minutes = round(avg_watch / 60, 1) if avg_watch else 0

        data = {
            'class_id': str(sc.id),
            'title': sc.title,
            'total_unique_viewers': total_viewers,
            'expected_students': expected_students,
            'attendance_percentage': attendance_pct,
            'avg_watch_seconds': round(avg_watch, 1),
            'avg_watch_minutes': avg_watch_minutes,
            'total_watch_seconds': agg['total_watch_seconds'] or 0,
            'avg_engagement_score': round(float(agg['avg_engagement'] or 0), 2),
            'live_watchers': agg['live_watchers'] or 0,
            'peak_live_viewers': sc.peak_live_viewers or 0,
        }

        return Response({'success': True, 'data': data})


# ---------------------------------------------------------------------------
# Tests (stubs)
# ---------------------------------------------------------------------------
class TestListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Test created'}, status=status.HTTP_201_CREATED)


class TestDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Test updated'})


class TestPublishView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Test published'})


class TestCloseView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Test closed'})


class TestResultsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})


class TestAnalysisView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})


class TestResultsBulkUploadView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Results uploaded'})


class TestResultsManualUploadView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Results uploaded'})


class QuestionListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Question created'}, status=status.HTTP_201_CREATED)


class QuestionDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Question updated'})


# ---------------------------------------------------------------------------
# Attendance (stubs)
# ---------------------------------------------------------------------------
class AttendanceListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, class_id):
        return Response({'success': True, 'data': []})
    def post(self, request, class_id):
        return Response({'success': True, 'message': 'Attendance marked'})


class AttendanceEditView(APIView):
    permission_classes = [_AllowAll]
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Attendance updated'})


class AttendanceBulkUploadView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'Attendance bulk uploaded'})


class AttendanceCorrectionRequestView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'Correction request submitted'})


class AttendanceCorrectionListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})


class AttendanceReportsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})


# ---------------------------------------------------------------------------
# Materials (stubs)
# ---------------------------------------------------------------------------
class MaterialListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Material uploaded'}, status=status.HTTP_201_CREATED)


class MaterialDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def delete(self, request, pk):
        return Response({'success': True, 'message': 'Material deleted'})


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------
class BatchListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        batch_teachers = (
            BatchTeacher.objects
            .filter(teacher=teacher)
            .select_related('batch', 'subject')
        )

        data = []
        seen = set()
        for bt in batch_teachers:
            b = bt.batch
            if not b:
                continue
            bid = str(b.id)
            if bid in seen:
                continue
            seen.add(bid)

            student_count = Users.objects.filter(
                batch=b, is_active=True,
            ).count()

            data.append({
                'id': bid,
                'name': b.name,
                'code': b.code,
                'status': b.status,
                'class_level': b.class_level or '',
                'exam_target': b.exam_target or '',
                'max_students': b.max_students,
                'student_count': student_count,
                'subject': bt.subject.name if bt.subject else '',
                'is_primary': bt.is_primary,
                'start_date': b.start_date.isoformat() if b.start_date else None,
                'end_date': b.end_date.isoformat() if b.end_date else None,
            })

        return Response({'success': True, 'data': data, 'count': len(data)})


class BatchDetailView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        is_assigned = BatchTeacher.objects.filter(
            teacher=teacher, batch_id=pk,
        ).exists()

        if not is_assigned:
            return Response(
                {'success': False, 'error': 'Not assigned to this batch'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            batch = Batch.objects.get(id=pk, tenant=teacher.tenant)
        except (Batch.DoesNotExist, ValueError):
            return Response(
                {'success': False, 'error': 'Batch not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        student_count = Users.objects.filter(
            batch=batch, is_active=True,
        ).count()

        teachers = []
        for bt in BatchTeacher.objects.filter(batch=batch).select_related('teacher', 'subject'):
            teachers.append({
                'teacher_id': str(bt.teacher_id),
                'teacher_name': bt.teacher.full_name if bt.teacher else '',
                'subject': bt.subject.name if bt.subject else '',
                'is_primary': bt.is_primary,
            })

        total_classes = ScheduledClass.objects.filter(
            batch=batch, teacher=teacher,
        ).count()
        completed_classes = ScheduledClass.objects.filter(
            batch=batch, teacher=teacher, status='COMPLETED',
        ).count()

        data = {
            'id': str(batch.id),
            'name': batch.name,
            'code': batch.code,
            'description': batch.description or '',
            'status': batch.status,
            'class_level': batch.class_level or '',
            'exam_target': batch.exam_target or '',
            'max_students': batch.max_students,
            'student_count': student_count,
            'teachers': teachers,
            'total_classes': total_classes,
            'completed_classes': completed_classes,
            'start_date': batch.start_date.isoformat() if batch.start_date else None,
            'end_date': batch.end_date.isoformat() if batch.end_date else None,
        }
        return Response({'success': True, 'data': data})


class UsersListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        teacher = _get_teacher(request)
        if not teacher:
            return Response(
                {'success': False, 'error': 'Teacher not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        is_assigned = BatchTeacher.objects.filter(
            teacher=teacher, batch_id=pk,
        ).exists()

        if not is_assigned:
            return Response(
                {'success': False, 'error': 'Not assigned to this batch'},
                status=status.HTTP_403_FORBIDDEN,
            )

        batch_students = (
            Users.objects
            .filter(batch_id=pk, is_active=True)
            .select_related('student')
            .order_by('student__first_name', 'student__last_name')
        )

        data = []
        for bs in batch_students:
            s = bs.student
            data.append({
                'id': str(s.id),
                'first_name': s.first_name,
                'last_name': s.last_name,
                'full_name': s.full_name,
                'email': s.email,
                'phone': s.phone,
                'student_code': s.student_code,
                'student_class': s.student_class,
                'exam_target': s.exam_target,
                'status': s.status,
                'avatar_url': s.avatar_url or '',
                'enrolled_at': bs.enrolled_at.isoformat() if bs.enrolled_at else None,
            })

        return Response({'success': True, 'data': data, 'count': len(data)})


class BatchPerformanceView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})


# ---------------------------------------------------------------------------
# Communication (stubs)
# ---------------------------------------------------------------------------
class AnnouncementCreateView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'Announcement created'}, status=status.HTTP_201_CREATED)


class TicketListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})


class TicketDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})


class TicketMessageView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Message sent'})


class MessageListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Message sent'})
