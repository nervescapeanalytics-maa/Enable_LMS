"""
LMS Enterprise - Account Serializers
"""
from rest_framework import serializers
from accounts.models import (
    Student, Teacher, Admin, Parent, ParentStudent,
    Role, Permission, RolePermission, PasswordChangeRequest,
)


# ---------------------------------------------------------------------------
# Student Serializers
# ---------------------------------------------------------------------------
class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Student
        fields = [
            'id', 'tenant', 'student_code', 'enrollment_number',
            'first_name', 'last_name', 'full_name', 'email', 'phone',
            'student_class', 'exam_target', 'stream', 'batch',
            'status', 'city', 'state', 'subscription_type', 'fee_status',
            'created_at',
        ]
        read_only_fields = ('id', 'created_at')


class StudentDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Student
        exclude = ['password_hash', 'mfa_secret', 'mfa_backup_codes']
        read_only_fields = ('id', 'created_at', 'updated_at')


class StudentCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Student
        exclude = ['password_hash', 'mfa_secret', 'mfa_backup_codes']
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        password = validated_data.pop('password')
        student = Student(**validated_data)
        student.set_password(password)
        student.save()
        return student


# ---------------------------------------------------------------------------
# Teacher Serializers
# ---------------------------------------------------------------------------
class TeacherListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Teacher
        fields = [
            'id', 'tenant', 'teacher_code', 'employee_id',
            'first_name', 'last_name', 'full_name', 'email', 'phone',
            'subjects', 'specialization', 'qualification',
            'employment_type', 'status', 'department', 'designation',
            'created_at',
        ]
        read_only_fields = ('id', 'created_at')


class TeacherDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Teacher
        exclude = [
            'password_hash', 'mfa_secret', 'mfa_backup_codes',
            'youtube_oauth_token', 'youtube_refresh_token',
            'bank_account', 'pan_number',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class TeacherCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Teacher
        exclude = [
            'password_hash', 'mfa_secret', 'mfa_backup_codes',
            'youtube_oauth_token', 'youtube_refresh_token',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        password = validated_data.pop('password')
        teacher = Teacher(**validated_data)
        teacher.set_password(password)
        teacher.save()
        return teacher


# ---------------------------------------------------------------------------
# Admin Serializers
# ---------------------------------------------------------------------------
class AdminListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Admin
        fields = [
            'id', 'tenant', 'admin_code', 'admin_type',
            'first_name', 'last_name', 'full_name', 'email', 'phone',
            'role', 'status', 'theme', 'created_at',
        ]
        read_only_fields = ('id', 'created_at')


class AdminDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Admin
        exclude = ['password_hash', 'mfa_secret', 'mfa_backup_codes']
        read_only_fields = ('id', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# Parent Serializers
# ---------------------------------------------------------------------------
class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Parent
        exclude = ['password_hash', 'mfa_secret', 'mfa_backup_codes']
        read_only_fields = ('id', 'created_at', 'updated_at')


class ParentStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentStudent
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


# ---------------------------------------------------------------------------
# Role & Permission Serializers
# ---------------------------------------------------------------------------
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'
        read_only_fields = ('id',)


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


# ---------------------------------------------------------------------------
# Auth Serializers
# ---------------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField()
    user_type = serializers.ChoiceField(
        choices=['STUDENT', 'TEACHER', 'ADMIN', 'PARENT'],
        default='STUDENT',
    )
    tenant_code = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError("Either email or phone is required.")
        return attrs


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField()
    password = serializers.CharField(min_length=8)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    user_type = serializers.ChoiceField(
        choices=['STUDENT', 'TEACHER', 'ADMIN', 'PARENT'],
        default='STUDENT',
    )
    tenant_code = serializers.CharField()
    # Student-specific
    student_class = serializers.CharField(required=False)
    exam_target = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    pin_code = serializers.CharField(required=False)


class TokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    user_type = serializers.CharField()
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs


class PasswordChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordChangeRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
