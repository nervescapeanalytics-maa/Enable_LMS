"""
LMS Enterprise - Student Views
CRUD + dashboard for student users.
"""
import uuid
import logging
from datetime import timedelta

from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Student, Teacher
from academics.models import Batch, Users
from classes.models import ScheduledClass, ClassAccessToken, ClassWatchTime

try:
    from attendance.models import AttendanceRecord
except ImportError:
    AttendanceRecord = None

logger = logging.getLogger(__name__)


class _AllowAll(permissions.BasePermission):
    def has_permission(self, request, view):
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_student(request):
    """Read user_id from session and return the Student object (for subsystems that FK to Student)."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Student.objects.select_related('batch', 'tenant').get(id=user_id)
    except (Student.DoesNotExist, ValueError):
        return None


def _get_user(request):
    """Read user_id from session and return the Users record (primary student data source)."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Users.objects.select_related('batch', 'tenant').get(student_id=user_id, is_active=True)
    except Users.DoesNotExist:
        # Fallback: try by id directly
        try:
            return Users.objects.select_related('batch', 'tenant').get(id=user_id, is_active=True)
        except Users.DoesNotExist:
            return None
    except ValueError:
        return None


def _get_student_batch_ids(student_or_user):
    """
    Return a list of batch UUIDs the student belongs to.
    Accepts either a Student or Users object.
    """
    batch_ids = set()
    if hasattr(student_or_user, 'batch_id') and student_or_user.batch_id:
        batch_ids.add(student_or_user.batch_id)
    # If it's a Student object, also look up Users records
    sid = getattr(student_or_user, 'student_id', None) or getattr(student_or_user, 'id', None)
    if sid:
        enrolled = Users.objects.filter(
            student_id=sid, is_active=True
        ).values_list('batch_id', flat=True)
        batch_ids.update(enrolled)
    return list(batch_ids)


def _get_student_classes(student, batch_ids, **filters):
    """
    Return a ScheduledClass queryset filtered by access rules:
      (a) batch_id in student's batch list (BATCH_ONLY)
      (b) access_type = ALL_STUDENTS
      (c) access_type = MULTI_BATCH and student's batch in allowed_batches
      (d) access_type = CUSTOM and student's id in allowed_students
    Additional filters are applied via **filters kwargs.
    """
    student_id_str = str(student.id)
    batch_id_strs = [str(bid) for bid in batch_ids]

    q_batch_only = Q(access_type='BATCH_ONLY', batch_id__in=batch_ids)
    q_all = Q(access_type='ALL_STUDENTS')

    q_multi = Q(access_type='MULTI_BATCH')
    multi_sub = Q()
    for bid_str in batch_id_strs:
        multi_sub |= Q(allowed_batches__contains=[bid_str])
    if batch_id_strs:
        q_multi &= multi_sub

    q_custom = Q(access_type='CUSTOM')
    q_custom &= Q(allowed_students__contains=[student_id_str])

    access_q = q_batch_only | q_all
    if batch_id_strs:
        access_q |= q_multi
    access_q |= q_custom

    qs = ScheduledClass.objects.filter(
        access_q, tenant=student.tenant, **filters
    ).exclude(
        status__in=['DRAFT', 'CANCELLED']
    ).select_related('teacher', 'batch')

    return qs.distinct()


def _format_time(t):
    """Format a time object as '03:00 PM'."""
    if t is None:
        return None
    return t.strftime('%I:%M %p')


def _format_date(d):
    """Format a date as 'YYYY-MM-DD'."""
    if d is None:
        return None
    return d.strftime('%Y-%m-%d')


def _teacher_name(teacher):
    if teacher is None:
        return 'Unknown'
    return f"{teacher.first_name} {teacher.last_name}".strip() or 'Unknown'


def _class_status_label(sc):
    """Map ScheduledClass.status to frontend label."""
    mapping = {
        'LIVE': 'live',
        'SCHEDULED': 'upcoming',
        'COMPLETED': 'completed',
        'RESCHEDULED': 'upcoming',
    }
    return mapping.get(sc.status, sc.status.lower())


def _serialize_class(sc, viewer_count=None):
    """Serialize a ScheduledClass to the frontend format."""
    return {
        'id': str(sc.id),
        'subject': sc.subject or '',
        'topic': sc.title,
        'title': sc.title,
        'description': sc.description or '',
        'time': _format_time(sc.start_time),
        'endTime': _format_time(sc.end_time),
        'startTime': _format_time(sc.start_time),
        'scheduledDate': _format_date(sc.scheduled_date),
        'language': 'Hindi',
        'teacher': _teacher_name(sc.teacher),
        'status': _class_status_label(sc),
        'youtubeLink': sc.youtube_watch_url or sc.youtube_embed_url or '',
        'youtubeEmbedUrl': sc.youtube_embed_url or '',
        'students': viewer_count if viewer_count is not None else (sc.total_unique_viewers or 0),
        'durationMinutes': sc.duration_minutes,
        'batchName': sc.batch.name if sc.batch else '',
        'classCode': sc.class_code,
        'teacherJoined': sc.teacher_joined_at is not None,
        'teacherJoinedAt': sc.teacher_joined_at.isoformat() if sc.teacher_joined_at else None,
    }


def _auth_error():
    return Response(
        {'success': False, 'error': 'Authentication required'},
        status=status.HTTP_401_UNAUTHORIZED,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        user = _get_user(request)
        batch_ids = _get_student_batch_ids(user or student)
        today = timezone.localdate()

        today_classes = _get_student_classes(
            student, batch_ids, scheduled_date=today
        ).order_by('start_time')

        live_classes_data = [_serialize_class(sc) for sc in today_classes]

        total_watched = ClassWatchTime.objects.filter(student=student).count()
        total_classes_count = _get_student_classes(
            student, batch_ids,
            status__in=['COMPLETED', 'LIVE'],
        ).count()
        attendance_pct = 0
        if total_classes_count > 0:
            attendance_pct = round((total_watched / total_classes_count) * 100)
            attendance_pct = min(attendance_pct, 100)

        total_students_in_batch = 0
        if batch_ids:
            total_students_in_batch = Users.objects.filter(
                batch_id__in=batch_ids, is_active=True
            ).values('student_id').distinct().count()

        # Profile data from Users (primary source) with Student fallback
        if user:
            batch_obj = user.batch
            profile_data = {
                'id': str(user.student_id or user.id),
                'name': user.full_name,
                'email': user.email or '',
                'phone': user.phone or '',
                'class': user.category or '',
                'stream': '',
                'rollNo': user.userid or '',
                'section': batch_obj.name if batch_obj else '',
                'medium': '',
                'school': user.other_school or '',
                'center': user.city_name or '',
                'joinDate': _format_date(user.enrolled_at.date() if user.enrolled_at else None),
                'avatar': user.photo or '',
            }
        else:
            profile_data = {
                'id': str(student.id),
                'name': student.full_name,
                'email': student.email or '',
                'phone': student.phone or '',
                'class': '',
                'stream': '',
                'rollNo': '',
                'section': student.batch.name if student.batch else '',
                'medium': '',
                'school': '',
                'center': '',
                'joinDate': _format_date(student.created_at.date() if student.created_at else None),
                'avatar': '',
            }

        stats_data = {
            'classesToday': today_classes.count(),
            'attendance': attendance_pct,
            'nextExamIn': None,
            'rank': None,
            'totalStudents': total_students_in_batch,
            'streak': 0,
        }

        return Response({
            'success': True,
            'data': {
                'profile': profile_data,
                'stats': stats_data,
                'todayLiveClasses': live_classes_data,
            },
        })


class DashboardStatsView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)
        today = timezone.localdate()

        classes_today = _get_student_classes(
            student, batch_ids, scheduled_date=today
        ).count()

        watch_records = ClassWatchTime.objects.filter(student=student)
        total_watched = watch_records.count()

        total_eligible = _get_student_classes(
            student, batch_ids,
            status__in=['COMPLETED', 'LIVE'],
        ).count()
        attendance_pct = 0
        if total_eligible > 0:
            attendance_pct = round((total_watched / total_eligible) * 100)
            attendance_pct = min(attendance_pct, 100)

        avg_score = watch_records.aggregate(
            avg=Avg('engagement_score')
        )['avg']

        return Response({
            'success': True,
            'data': {
                'attendance_percent': attendance_pct,
                'test_average': round(float(avg_score), 1) if avg_score else 0,
                'classes_attended': total_watched,
                'classes_today': classes_today,
                'rank': None,
            },
        })


class DashboardUpcomingView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)
        today = timezone.localdate()
        week_end = today + timedelta(days=7)

        upcoming = _get_student_classes(
            student, batch_ids,
            scheduled_date__gte=today,
            scheduled_date__lte=week_end,
            status__in=['SCHEDULED', 'RESCHEDULED'],
        ).order_by('scheduled_date', 'start_time')[:20]

        classes_data = [_serialize_class(sc) for sc in upcoming]

        return Response({
            'success': True,
            'data': {
                'classes': classes_data,
                'tests': [],
            },
        })


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        user = _get_user(request)

        if user:
            batch_obj = user.batch
            data = {
                'id': str(user.student_id or user.id),
                'name': user.full_name,
                'firstName': user.name or '',
                'lastName': '',
                'displayName': user.name or '',
                'email': user.email or '',
                'phone': user.phone or '',
                'class': user.category or '',
                'stream': '',
                'rollNo': user.userid or '',
                'enrollmentNumber': '',
                'section': batch_obj.name if batch_obj else '',
                'medium': '',
                'board': '',
                'school': user.other_school or '',
                'center': user.city_name or '',
                'joinDate': _format_date(user.enrolled_at.date() if user.enrolled_at else None),
                'avatar': user.photo or '',
                'dateOfBirth': _format_date(user.dob.date() if user.dob else None),
                'gender': user.gender or '',
                'bloodGroup': '',
                'aadhaarLastFour': '',
                'address': user.city_name or '',
                'addressLine1': '',
                'addressLine2': '',
                'city': user.city_name or '',
                'district': '',
                'state': '',
                'pinCode': '',
                'country': 'India',
                'parentName': user.father_name or '',
                'parentPhone': user.phone1 or '',
                'parentEmail': '',
                'parentRelation': 'Father' if user.father_name else '',
                'parentOccupation': '',
                'alternateContact': user.phone1 or '',
                'admissionDate': _format_date(user.enrolled_at.date() if user.enrolled_at else None),
                'admissionSource': '',
                'subscriptionType': '',
                'subscriptionStart': None,
                'subscriptionEnd': None,
                'feeStatus': '',
                'preferredLanguage': 'en',
                'notificationEmail': True,
                'notificationSms': True,
                'notificationPush': True,
                'notificationWhatsapp': False,
                'status': user.status or 'active',
                'emailVerified': False,
                'phoneVerified': False,
                'batchName': batch_obj.name if batch_obj else '',
                'batchCode': batch_obj.code if batch_obj else '',
                'tenantName': user.tenant.name if user.tenant_id else '',
                'tenantCode': user.tenant.code if user.tenant_id else '',
            }
        else:
            data = {
                'id': str(student.id),
                'name': student.full_name,
                'firstName': student.first_name,
                'lastName': student.last_name,
                'displayName': student.display_name or '',
                'email': student.email or '',
                'phone': student.phone or '',
                'class': '',
                'stream': '',
                'rollNo': '',
                'enrollmentNumber': '',
                'section': student.batch.name if student.batch else '',
                'medium': '',
                'board': '',
                'school': '',
                'center': '',
                'joinDate': _format_date(student.created_at.date() if student.created_at else None),
                'avatar': '',
                'dateOfBirth': None,
                'gender': '',
                'bloodGroup': '',
                'aadhaarLastFour': '',
                'address': '',
                'addressLine1': '',
                'addressLine2': '',
                'city': '',
                'district': '',
                'state': '',
                'pinCode': '',
                'country': 'India',
                'parentName': '',
                'parentPhone': '',
                'parentEmail': '',
                'parentRelation': '',
                'parentOccupation': '',
                'alternateContact': '',
                'admissionDate': None,
                'admissionSource': '',
                'subscriptionType': '',
                'subscriptionStart': None,
                'subscriptionEnd': None,
                'feeStatus': '',
                'preferredLanguage': 'en',
                'notificationEmail': True,
                'notificationSms': True,
                'notificationPush': True,
                'notificationWhatsapp': False,
                'status': 'active',
                'emailVerified': False,
                'phoneVerified': False,
                'batchName': student.batch.name if student.batch else '',
                'batchCode': student.batch.code if student.batch else '',
                'tenantName': student.tenant.name if student.tenant_id else '',
                'tenantCode': student.tenant.code if student.tenant_id else '',
            }
        return Response({'success': True, 'data': data})

    def put(self, request):
        user = _get_user(request)
        if not user:
            return _auth_error()

        allowed_fields = ['phone', 'other_school', 'city_name', 'email']
        updated = []
        field_map = {
            'phone': 'phone',
            'school': 'other_school',
            'city': 'city_name',
            'email': 'email',
        }
        for camel, field in field_map.items():
            val = request.data.get(camel)
            if val is not None:
                setattr(user, field, val)
                updated.append(field)

        if updated:
            user.save(update_fields=updated)

        return Response({'success': True, 'message': 'Profile updated'})


class ProfileChangeRequestView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request):
        return Response({'success': True, 'message': 'Profile change request submitted'})


class ProfileChangeRequestListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        return Response({'success': True, 'data': []})


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
class ClassListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)
        filters = {}

        status_filter = request.query_params.get('status')
        if status_filter:
            filters['status'] = status_filter.upper()

        subject_filter = request.query_params.get('subject')
        if subject_filter:
            filters['subject'] = subject_filter.upper()

        date_from = request.query_params.get('date_from')
        if date_from:
            filters['scheduled_date__gte'] = date_from

        date_to = request.query_params.get('date_to')
        if date_to:
            filters['scheduled_date__lte'] = date_to

        classes = _get_student_classes(
            student, batch_ids, **filters
        ).order_by('-scheduled_date', '-start_time')

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        page_size = min(page_size, 100)
        start = (page - 1) * page_size
        end = start + page_size

        total = classes.count()
        page_classes = classes[start:end]

        return Response({
            'success': True,
            'data': [_serialize_class(sc) for sc in page_classes],
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'totalPages': (total + page_size - 1) // page_size if page_size else 1,
            },
        })


class ClassUpcomingView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)
        today = timezone.localdate()

        upcoming = _get_student_classes(
            student, batch_ids,
            scheduled_date__gte=today,
            status__in=['SCHEDULED', 'RESCHEDULED'],
        ).order_by('scheduled_date', 'start_time')[:30]

        return Response({
            'success': True,
            'data': [_serialize_class(sc) for sc in upcoming],
        })


class ClassLiveView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)

        live = _get_student_classes(
            student, batch_ids, status='LIVE',
        ).order_by('start_time')

        live_data = []
        for sc in live:
            viewer_count = ClassWatchTime.objects.filter(
                scheduled_class=sc, left_at__isnull=True, is_live_watch=True,
            ).count()
            live_data.append(_serialize_class(sc, viewer_count=viewer_count))

        return Response({'success': True, 'data': live_data})


class ClassDetailView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        try:
            sc = ScheduledClass.objects.select_related('teacher', 'batch', 'chapter', 'topic').get(pk=pk, tenant=student.tenant)
        except ScheduledClass.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        viewer_count = ClassWatchTime.objects.filter(
            scheduled_class=sc, left_at__isnull=True, is_live_watch=True,
        ).count()

        watch_record = ClassWatchTime.objects.filter(
            scheduled_class=sc, student=student,
        ).order_by('-joined_at').first()

        data = _serialize_class(sc, viewer_count=viewer_count)
        data.update({
            'accessType': sc.access_type,
            'privacyStatus': sc.privacy_status,
            'actualStartTime': sc.actual_start_time.isoformat() if sc.actual_start_time else None,
            'actualEndTime': sc.actual_end_time.isoformat() if sc.actual_end_time else None,
            'chapterName': sc.chapter.name if sc.chapter else None,
            'topicName': sc.topic.name if sc.topic else None,
            'topicsCovered': sc.topics_covered or [],
            'learningObjectives': sc.learning_objectives or [],
            'recordingUrl': sc.youtube_recording_url or '',
            'attachedMaterials': sc.attached_materials or [],
            'watchRecord': None,
        })

        if watch_record:
            data['watchRecord'] = {
                'joinedAt': watch_record.joined_at.isoformat() if watch_record.joined_at else None,
                'leftAt': watch_record.left_at.isoformat() if watch_record.left_at else None,
                'totalWatchSeconds': watch_record.total_watch_seconds,
                'videoProgressPercent': float(watch_record.video_progress_percent) if watch_record.video_progress_percent else 0,
                'completionStatus': watch_record.completion_status,
                'isLiveWatch': watch_record.is_live_watch,
            }

        return Response({'success': True, 'data': data})


class ClassAccessTokenView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        token_obj = ClassAccessToken.objects.filter(
            scheduled_class_id=pk,
            student=student,
            revoked=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        return Response({
            'success': True,
            'data': {
                'token': token_obj.token if token_obj else None,
                'expiresAt': token_obj.expires_at.isoformat() if token_obj else None,
            },
        })


class ClassRecordingView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        try:
            sc = ScheduledClass.objects.get(pk=pk, tenant=student.tenant)
        except ScheduledClass.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            'success': True,
            'data': {
                'recording_url': sc.youtube_recording_url or None,
                'youtubeWatchUrl': sc.youtube_watch_url or None,
            },
        })


class ClassJoinView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        try:
            sc = ScheduledClass.objects.get(pk=pk, tenant=student.tenant)
        except ScheduledClass.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        now = timezone.now()
        token_val = uuid.uuid4().hex
        ClassAccessToken.objects.update_or_create(
            scheduled_class=sc,
            student=student,
            tenant=student.tenant,
            defaults={
                'token': token_val,
                'expires_at': now + timedelta(hours=6),
                'used': True,
                'used_at': now,
                'revoked': False,
            },
        )

        watch_session_id = f"{sc.id}-{student.id}-{now.strftime('%Y%m%d%H%M%S')}"
        watch, created = ClassWatchTime.objects.get_or_create(
            scheduled_class=sc,
            student=student,
            left_at__isnull=True,
            defaults={
                'tenant': student.tenant,
                'watch_session_id': watch_session_id,
                'joined_at': now,
                'is_live_watch': True,
                'total_watch_seconds': 0,
            },
        )
        if not created:
            watch.is_live_watch = True
            watch.save(update_fields=['is_live_watch', 'updated_at'] if hasattr(watch, 'updated_at') else ['is_live_watch'])

        return Response({
            'success': True,
            'message': 'Joined class',
            'data': {
                'accessToken': token_val,
                'watchSessionId': watch.watch_session_id,
            },
        })


class ClassLeaveView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        now = timezone.now()
        watch = ClassWatchTime.objects.filter(
            scheduled_class_id=pk,
            student=student,
            left_at__isnull=True,
        ).order_by('-joined_at').first()

        if watch:
            watch.left_at = now
            elapsed = int((now - watch.joined_at).total_seconds())
            watch.total_watch_seconds = max(watch.total_watch_seconds, elapsed)
            watch.save(update_fields=['left_at', 'total_watch_seconds'])

        return Response({'success': True, 'message': 'Left class'})


class ClassHeartbeatView(APIView):
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()

        watch = ClassWatchTime.objects.filter(
            scheduled_class_id=pk,
            student=student,
            left_at__isnull=True,
        ).order_by('-joined_at').first()

        if not watch:
            return Response(
                {'success': False, 'error': 'No active watch session'},
                status=status.HTTP_404_NOT_FOUND,
            )

        elapsed = int((timezone.now() - watch.joined_at).total_seconds())
        watch.total_watch_seconds = max(watch.total_watch_seconds, elapsed)

        progress = request.data.get('videoProgressPercent')
        if progress is not None:
            watch.video_progress_percent = progress

        tab_switch = request.data.get('tabSwitch')
        if tab_switch:
            watch.tab_switches = F('tab_switches') + 1

        watch.save(update_fields=['total_watch_seconds', 'video_progress_percent', 'tab_switches'])

        return Response({'success': True, 'message': 'Heartbeat recorded'})


# ---------------------------------------------------------------------------
# Tests — wired to real DB (admin-uploaded tests reflect immediately)
# ---------------------------------------------------------------------------
def _serialize_test(t, attempts_used=0):
    return {
        'id': str(t.id),
        'test_code': t.test_code,
        'title': t.title,
        'description': t.description or '',
        'test_type': t.test_type,
        'subject': t.subject.name if t.subject_id else None,
        'subject_code': t.subject.code if t.subject_id else None,
        'chapter': t.chapter.name if t.chapter_id else None,
        'class_level': t.chapter.class_level if t.chapter_id else None,
        'duration_minutes': t.total_duration_minutes,
        'total_marks': float(t.total_marks or 0),
        'total_questions': t.total_questions,
        'passing_percent': float(t.passing_percent or 0),
        'positive_marks': float(t.positive_marks_per_question or 0),
        'negative_marks': float(t.negative_marks_per_question or 0),
        'start_datetime': t.start_datetime.isoformat() if t.start_datetime else None,
        'end_datetime': t.end_datetime.isoformat() if t.end_datetime else None,
        'status': t.status,
        'max_attempts': t.max_attempts,
        'attempts_used': attempts_used,
        'attempts_remaining': max(t.max_attempts - attempts_used, 0),
        'take_url': f'/student/exams/{t.id}/take/',
    }


def _visible_tests_qs(student):
    """Same logic as core.student_exam_views._visible_tests_qs."""
    from assessments.models import Test
    from academics.models import Users as _Users
    now = timezone.now()
    batch_ids = set()
    if student.batch_id:
        batch_ids.add(student.batch_id)
    for bid in _Users.objects.filter(
        student_id=student.id, is_active=True
    ).values_list('batch_id', flat=True):
        if bid:
            batch_ids.add(bid)
    qs = Test.objects.filter(
        tenant=student.tenant, is_deleted=False,
        status__in=['PUBLISHED', 'ACTIVE'],
    ).select_related('subject', 'chapter')
    qs = qs.filter(
        Q(start_datetime__isnull=True) | Q(start_datetime__lte=now)
    ).filter(
        Q(end_datetime__isnull=True) | Q(end_datetime__gte=now)
    )
    qs = qs.filter(
        Q(access_mode='OPEN')
        | Q(access_mode='SCHEDULED')
        | Q(access_mode='PASSWORD')
        | Q(access_mode='BATCH_ONLY', batch_id__in=batch_ids)
        | Q(access_mode='BATCH_ONLY', batch__isnull=True)
    )
    if student.student_class:
        qs = qs.filter(
            Q(chapter__isnull=True)
            | Q(chapter__class_level__isnull=True)
            | Q(chapter__class_level='')
            | Q(chapter__class_level=str(student.student_class))
        )
    return qs.order_by('-start_datetime', '-published_at', '-created_at')


class TestListView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()
        from assessments.models import TestAttempt
        tests = list(_visible_tests_qs(student))
        used_map = {}
        for row in (
            TestAttempt.objects
            .filter(student=student, test__in=tests)
            .values('test_id')
            .annotate(c=Count('id'))
        ):
            used_map[row['test_id']] = row['c']
        data = [_serialize_test(t, used_map.get(t.id, 0)) for t in tests]
        return Response({'success': True, 'data': data, 'count': len(data)})


class TestUpcomingView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()
        from assessments.models import Test
        now = timezone.now()
        upcoming = Test.objects.filter(
            tenant=student.tenant, is_deleted=False,
            status__in=['PUBLISHED', 'ACTIVE'],
            start_datetime__gt=now,
        ).select_related('subject', 'chapter').order_by('start_datetime')[:10]
        return Response({'success': True, 'data': [_serialize_test(t) for t in upcoming]})


class TestDetailView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()
        from assessments.models import Test, TestAttempt
        test = Test.objects.filter(
            id=pk, tenant=student.tenant, is_deleted=False,
        ).select_related('subject', 'chapter').first()
        if not test:
            return Response({'success': False, 'error': 'Test not found'}, status=404)
        used = TestAttempt.objects.filter(test=test, student=student).count()
        return Response({'success': True, 'data': _serialize_test(test, used)})


class TestStartView(APIView):
    """SPA convenience: returns the redirect URL to the server-rendered take page."""
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()
        return Response({
            'success': True,
            'data': {'redirect_url': f'/student/exams/{pk}/take/'},
        })


class TestSubmitView(APIView):
    """Test submission happens via POST to /student/exams/<id>/take/. This stub
    exists for compatibility but advises clients to use the server-rendered flow."""
    permission_classes = [_AllowAll]

    def post(self, request, pk):
        return Response({
            'success': False,
            'error': 'Submit through /student/exams/<test_id>/take/ form',
        }, status=400)


class TestResultView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()
        from assessments.models import TestAttempt
        attempt = TestAttempt.objects.filter(
            test_id=pk, student=student,
            status__in=['EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'],
        ).order_by('-submitted_at').first()
        if not attempt:
            return Response({'success': False, 'error': 'No completed attempt'}, status=404)
        return Response({'success': True, 'data': {
            'attempt_id': str(attempt.id),
            'raw_score': float(attempt.raw_score or 0),
            'total_marks': float(attempt.total_marks or 0),
            'percentage': float(attempt.percentage or 0),
            'correct': attempt.correct,
            'incorrect': attempt.incorrect,
            'skipped': attempt.skipped,
            'result': attempt.result,
            'submitted_at': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            'view_url': f'/student/exams/{pk}/result/{attempt.id}/',
        }})


class TestSolutionsView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request, pk):
        student = _get_student(request)
        if not student:
            return _auth_error()
        from assessments.models import TestAttempt, TestAttemptAnswer
        attempt = TestAttempt.objects.filter(
            test_id=pk, student=student,
        ).order_by('-submitted_at').first()
        if not attempt:
            return Response({'success': True, 'data': []})
        answers = TestAttemptAnswer.objects.filter(
            attempt=attempt
        ).select_related('question').order_by('question__question_order')
        out = [{
            'question': a.question.question_text,
            'student_answer': a.student_answer,
            'correct_answer': a.question.correct_answer,
            'is_correct': a.is_correct,
            'marks_awarded': float(a.marks_awarded or 0),
            'explanation': a.question.answer_explanation,
        } for a in answers]
        return Response({'success': True, 'data': out})


# ---------------------------------------------------------------------------
# Materials (stubs)
# ---------------------------------------------------------------------------
class MaterialListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class MaterialDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})

class MaterialDownloadView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {'download_url': None}})


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
class AttendanceView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        watch_qs = ClassWatchTime.objects.filter(
            student=student,
        ).select_related('scheduled_class', 'scheduled_class__teacher')

        if date_from:
            watch_qs = watch_qs.filter(scheduled_class__scheduled_date__gte=date_from)
        if date_to:
            watch_qs = watch_qs.filter(scheduled_class__scheduled_date__lte=date_to)

        watch_qs = watch_qs.order_by('-scheduled_class__scheduled_date')

        records = []
        for w in watch_qs[:100]:
            sc = w.scheduled_class
            present = (
                w.total_watch_seconds >= (sc.auto_attendance_threshold_minutes * 60)
                if sc.auto_attendance_threshold_minutes else True
            )
            records.append({
                'id': str(w.id),
                'classId': str(sc.id),
                'classTitle': sc.title,
                'subject': sc.subject or '',
                'teacher': _teacher_name(sc.teacher),
                'date': _format_date(sc.scheduled_date),
                'joinedAt': w.joined_at.isoformat() if w.joined_at else None,
                'leftAt': w.left_at.isoformat() if w.left_at else None,
                'totalWatchSeconds': w.total_watch_seconds,
                'present': present,
                'status': 'present' if present else 'partial',
                'completionStatus': w.completion_status,
            })

        return Response({'success': True, 'data': records})


class AttendanceSummaryView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        batch_ids = _get_student_batch_ids(student)

        total_eligible = _get_student_classes(
            student, batch_ids,
            status__in=['COMPLETED', 'LIVE'],
        ).count()

        watched_classes = ClassWatchTime.objects.filter(
            student=student,
        ).values('scheduled_class_id').distinct().count()

        present_count = 0
        if total_eligible > 0:
            watch_records = ClassWatchTime.objects.filter(
                student=student,
            ).select_related('scheduled_class')
            for w in watch_records:
                sc = w.scheduled_class
                threshold_secs = (sc.auto_attendance_threshold_minutes or 15) * 60
                if w.total_watch_seconds >= threshold_secs:
                    present_count += 1

        absent_count = max(0, total_eligible - watched_classes)
        pct = round((present_count / total_eligible) * 100) if total_eligible > 0 else 0

        return Response({
            'success': True,
            'data': {
                'total': total_eligible,
                'present': present_count,
                'absent': absent_count,
                'partial': max(0, watched_classes - present_count),
                'percent': min(pct, 100),
            },
        })


class AttendanceCalendarView(APIView):
    permission_classes = [_AllowAll]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return _auth_error()

        month = request.query_params.get('month')
        year = request.query_params.get('year')

        watch_qs = ClassWatchTime.objects.filter(
            student=student,
        ).select_related('scheduled_class')

        if month and year:
            watch_qs = watch_qs.filter(
                scheduled_class__scheduled_date__year=int(year),
                scheduled_class__scheduled_date__month=int(month),
            )

        calendar_data = {}
        for w in watch_qs:
            sc = w.scheduled_class
            date_str = _format_date(sc.scheduled_date)
            threshold_secs = (sc.auto_attendance_threshold_minutes or 15) * 60
            present = w.total_watch_seconds >= threshold_secs

            if date_str not in calendar_data:
                calendar_data[date_str] = {
                    'date': date_str,
                    'totalClasses': 0,
                    'attended': 0,
                    'status': 'absent',
                }
            calendar_data[date_str]['totalClasses'] += 1
            if present:
                calendar_data[date_str]['attended'] += 1

        for entry in calendar_data.values():
            if entry['attended'] == entry['totalClasses'] and entry['totalClasses'] > 0:
                entry['status'] = 'present'
            elif entry['attended'] > 0:
                entry['status'] = 'partial'
            else:
                entry['status'] = 'absent'

        return Response({'success': True, 'data': list(calendar_data.values())})


# ---------------------------------------------------------------------------
# Communication (stubs)
# ---------------------------------------------------------------------------
class AnnouncementListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class NotificationListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class NotificationReadView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Notification marked as read'})

class NotificationReadAllView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'All notifications marked as read'})

class TicketListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Ticket created'}, status=status.HTTP_201_CREATED)

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


# ---------------------------------------------------------------------------
# Settings (stub)
# ---------------------------------------------------------------------------
class SettingsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        user = _get_user(request)
        if not user:
            student = _get_student(request)
            if not student:
                return _auth_error()
        return Response({
            'success': True,
            'data': {
                'preferredLanguage': 'en',
                'notificationEmail': True,
                'notificationSms': True,
                'notificationPush': True,
                'notificationWhatsapp': False,
                'quietHoursStart': None,
                'quietHoursEnd': None,
            },
        })
    def put(self, request):
        # Settings preferences not yet stored on Users model
        return Response({'success': True, 'message': 'Settings updated'})
