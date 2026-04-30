"""Scheduling - API Views"""
from datetime import date
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import RecurringRule, Enrollment, BlackoutDate, ClassAttendance
from .serializers import (
    RecurringRuleSerializer, RecurringRuleDuplicateSerializer,
    EnrollmentSerializer, EnrollBulkSerializer,
    BlackoutDateSerializer,
    ClassAttendanceSerializer, BulkAttendanceSerializer,
)
from . import services


class SchedulingRootView(APIView):
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'rules': '/api/v1/scheduling/rules/',
                'enrollments': '/api/v1/scheduling/enrollments/',
                'blackout-dates': '/api/v1/scheduling/blackout-dates/',
                'attendance': '/api/v1/scheduling/attendance/<class_id>/',
            }
        }})


# ── Recurring Rules ──

class RecurringRuleListView(generics.ListCreateAPIView):
    serializer_class = RecurringRuleSerializer

    def get_queryset(self):
        qs = RecurringRule.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        teacher_id = self.request.query_params.get('teacher')
        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)
        return qs


class RecurringRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RecurringRule.objects.all()
    serializer_class = RecurringRuleSerializer


class ActivateRuleView(APIView):
    """Activate a draft/paused rule."""
    def post(self, request, pk):
        try:
            rule = RecurringRule.objects.get(pk=pk)
        except RecurringRule.DoesNotExist:
            return Response({'error': 'Rule not found'}, status=status.HTTP_404_NOT_FOUND)

        if rule.status not in (RecurringRule.RuleStatus.DRAFT, RecurringRule.RuleStatus.PAUSED):
            return Response(
                {'error': 'Only draft or paused rules can be activated'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rule.status = RecurringRule.RuleStatus.ACTIVE
        rule.save(update_fields=['status', 'updated_at'])
        return Response(RecurringRuleSerializer(rule).data)


class PauseRuleView(APIView):
    """Pause an active rule."""
    def post(self, request, pk):
        try:
            rule = RecurringRule.objects.get(pk=pk)
        except RecurringRule.DoesNotExist:
            return Response({'error': 'Rule not found'}, status=status.HTTP_404_NOT_FOUND)

        if rule.status != RecurringRule.RuleStatus.ACTIVE:
            return Response(
                {'error': 'Only active rules can be paused'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rule.status = RecurringRule.RuleStatus.PAUSED
        rule.save(update_fields=['status', 'updated_at'])
        return Response(RecurringRuleSerializer(rule).data)


class DuplicateRuleView(APIView):
    """Duplicate and Edit → Supersede workflow."""
    def post(self, request, pk):
        try:
            original = RecurringRule.objects.get(pk=pk)
        except RecurringRule.DoesNotExist:
            return Response({'error': 'Rule not found'}, status=status.HTTP_404_NOT_FOUND)

        ser = RecurringRuleDuplicateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        effective_from = ser.validated_data['effective_from']
        if effective_from <= date.today():
            return Response(
                {'error': 'Effective From must be at least tomorrow.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        changes = {k: v for k, v in ser.validated_data.items() if k != 'effective_from'}

        try:
            new_rule = services.duplicate_and_supersede(original, effective_from, changes)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            RecurringRuleSerializer(new_rule).data,
            status=status.HTTP_201_CREATED
        )


# ── Enrollments ──

class EnrollmentListView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        qs = Enrollment.objects.filter(is_active=True)
        rule_id = self.request.query_params.get('rule')
        if rule_id:
            qs = qs.filter(recurring_rule_id=rule_id)
        instance_id = self.request.query_params.get('class_instance')
        if instance_id:
            qs = qs.filter(class_instance_id=instance_id)
        student_id = self.request.query_params.get('student')
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs


class EnrollmentDetailView(generics.RetrieveDestroyAPIView):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

    def perform_destroy(self, instance):
        """Soft-delete: mark as inactive instead of hard delete."""
        from django.utils import timezone as tz
        instance.is_active = False
        instance.unenrolled_at = tz.now()
        instance.save(update_fields=['is_active', 'unenrolled_at'])


class BulkEnrollView(APIView):
    """Enroll students in bulk (manual / class group / CSV)."""
    def post(self, request):
        ser = EnrollBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Determine target
        from scheduling.models import RecurringRule
        from classes.models import ScheduledClass

        is_recurring = bool(data.get('recurring_rule'))
        if is_recurring:
            target = RecurringRule.objects.get(id=data['recurring_rule'])
        else:
            target = ScheduledClass.objects.get(id=data['class_instance'])

        tenant = target.tenant
        enrolled_by = getattr(request.user, 'id', None)
        method = data['method']

        if method == 'MANUAL':
            count = services.enroll_students_manual(
                tenant, target, data.get('student_ids', []),
                enrolled_by, is_recurring
            )
        elif method == 'CLASS_GROUP':
            count = services.enroll_by_class_group(
                tenant, target, data['class_group_id'],
                enrolled_by, is_recurring
            )
        elif method == 'CSV_UPLOAD':
            count = services.enroll_by_csv_emails(
                tenant, target, data.get('student_emails', []),
                enrolled_by, is_recurring
            )
        else:
            return Response({'error': 'Invalid method'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'enrolled_count': count,
            'message': f'{count} student(s) enrolled successfully.'
        })


# ── Blackout Dates ──

class BlackoutDateListView(generics.ListCreateAPIView):
    queryset = BlackoutDate.objects.all()
    serializer_class = BlackoutDateSerializer


class BlackoutDateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlackoutDate.objects.all()
    serializer_class = BlackoutDateSerializer


# ── Class Attendance ──

class ClassAttendanceListView(generics.ListAPIView):
    serializer_class = ClassAttendanceSerializer

    def get_queryset(self):
        return ClassAttendance.objects.filter(
            class_instance_id=self.kwargs['class_id']
        )


class BulkAttendanceView(APIView):
    """Mark attendance for all students in a class session."""
    def post(self, request, class_id):
        ser = BulkAttendanceSerializer(data={
            'class_instance_id': class_id,
            'records': request.data.get('records', []),
        })
        ser.is_valid(raise_exception=True)

        # Get teacher from request (simplified)
        from accounts.models import Teacher
        teacher = Teacher.objects.filter(
            id=getattr(request.user, 'id', None)
        ).first()

        count = services.mark_bulk_attendance(
            tenant=None,  # Will be inferred from class instance
            class_instance_id=class_id,
            records=ser.validated_data['records'],
            marked_by_teacher=teacher,
        )

        return Response({
            'success': True,
            'marked_count': count,
            'message': f'Attendance marked for {count} student(s).'
        })
