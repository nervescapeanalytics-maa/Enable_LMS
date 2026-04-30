"""
Centralized permission classes for the LMS API.

Usage in views:
    from core.permissions import IsTeacherOrAdmin, IsStudentOwner

    class MyViewSet(viewsets.ModelViewSet):
        permission_classes = [IsTeacherOrAdmin]

The project-wide default is IsAuthenticated (set in settings.py).
Only override per-view when you need more specific control.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherOrAdmin(BasePermission):
    """Allow access to teachers and admin/staff users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        return hasattr(request.user, 'teacher_profile') or \
            getattr(request.user, 'role', None) == 'teacher'


class IsStudentOwner(BasePermission):
    """Allow students to access only their own data."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check common patterns for student ownership
        if hasattr(obj, 'student'):
            if hasattr(obj.student, 'user'):
                return obj.student.user == request.user
            return obj.student == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsReadOnly(BasePermission):
    """Allow read-only access (GET, HEAD, OPTIONS)."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """Allow full access to admins, read-only to authenticated users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser
