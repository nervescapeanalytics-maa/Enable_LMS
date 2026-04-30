"""Scheduling - REST Serializers"""
from rest_framework import serializers
from .models import RecurringRule, Enrollment, BlackoutDate, ClassAttendance


class RecurringRuleSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = RecurringRule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'generated_until')

    def get_teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else None

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject else None


class RecurringRuleDuplicateSerializer(serializers.Serializer):
    """Serializer for the 'Duplicate and Edit' workflow."""
    effective_from = serializers.DateField(
        help_text="Must be tomorrow or later"
    )
    title = serializers.CharField(required=False)
    rrule = serializers.CharField(required=False)
    start_time = serializers.TimeField(required=False)
    duration_mins = serializers.IntegerField(required=False)
    teacher = serializers.UUIDField(required=False)
    subject = serializers.UUIDField(required=False)


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ('id', 'enrolled_at')

    def get_student_name(self, obj):
        return obj.student.full_name if obj.student else None


class EnrollBulkSerializer(serializers.Serializer):
    """Enroll multiple students at once (manual, class group, or CSV)."""
    recurring_rule = serializers.UUIDField(required=False)
    class_instance = serializers.UUIDField(required=False)
    method = serializers.ChoiceField(choices=Enrollment.EnrollmentMethod.choices)
    student_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False,
        help_text="For manual enrollment"
    )
    class_group_id = serializers.UUIDField(
        required=False,
        help_text="For class group enrollment"
    )
    student_emails = serializers.ListField(
        child=serializers.EmailField(), required=False,
        help_text="For CSV upload enrollment"
    )


class BlackoutDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlackoutDate
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class ClassAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = ClassAttendance
        fields = '__all__'
        read_only_fields = ('id', 'marked_at')

    def get_student_name(self, obj):
        return obj.student.full_name if obj.student else None


class BulkAttendanceSerializer(serializers.Serializer):
    """Mark attendance for multiple students at once."""
    class_instance_id = serializers.UUIDField()
    records = serializers.ListField(child=serializers.DictField())
    # Each dict: { "student_id": "uuid", "status": "PRESENT|ABSENT|LATE" }
