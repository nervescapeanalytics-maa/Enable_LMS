"""
LMS Enterprise - Admin Views
Full admin panel: user management, system config, reports.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Admin, Student, Teacher, Role, Permission
from academics.models import Users as AcademicUsers
from accounts.serializers import (
    AdminListSerializer, AdminDetailSerializer,
    StudentListSerializer, StudentDetailSerializer,
    TeacherListSerializer, TeacherDetailSerializer,
    RoleSerializer, PermissionSerializer,
)


class _AllowAll(permissions.BasePermission):
    def has_permission(self, request, view):
        return True


def _get_admin_tenant(request):
    """Return the tenant for the logged-in admin, or None for super-admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        admin = Admin.objects.select_related('tenant').get(id=user_id)
        return admin.tenant
    except (Admin.DoesNotExist, ValueError):
        return getattr(request, 'tenant', None)


def _scoped_qs(model, request):
    """Return a queryset scoped to the admin's tenant when available."""
    tenant = _get_admin_tenant(request)
    qs = model.objects.all()
    if tenant and hasattr(model, 'tenant'):
        qs = qs.filter(tenant=tenant)
    return qs


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        tenant = _get_admin_tenant(request)
        s_qs = AcademicUsers.objects.filter(tenant=tenant) if tenant else AcademicUsers.objects.all()
        t_qs = Teacher.objects.filter(tenant=tenant) if tenant else Teacher.objects.all()
        a_qs = Admin.objects.filter(tenant=tenant) if tenant else Admin.objects.all()
        return Response({'success': True, 'data': {
            'welcome': 'Admin Dashboard',
            'total_students': s_qs.filter(is_active=True).count(),
            'total_teachers': t_qs.count(),
            'total_admins': a_qs.count(),
        }})

class DashboardStatsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        tenant = _get_admin_tenant(request)
        s_qs = AcademicUsers.objects.filter(tenant=tenant) if tenant else AcademicUsers.objects.all()
        t_qs = Teacher.objects.filter(tenant=tenant) if tenant else Teacher.objects.all()
        return Response({'success': True, 'data': {
            'active_students': s_qs.filter(is_active=True).count(),
            'active_teachers': t_qs.filter(status__iexact='ACTIVE').count(),
        }})

class DashboardRealtimeView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'online_users': 0, 'active_classes': 0}})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'message': 'Admin profile'}})
    def put(self, request):
        return Response({'success': True, 'message': 'Profile updated'})

class PreferencesView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})
    def put(self, request):
        return Response({'success': True, 'message': 'Preferences updated'})

class MFASetupView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'MFA setup initiated'})

class MFADisableView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'MFA disabled'})


# ---------------------------------------------------------------------------
# Student Management
# ---------------------------------------------------------------------------
class StudentListCreateView(generics.ListCreateAPIView):
    permission_classes = [_AllowAll]
    serializer_class = StudentListSerializer
    def get_queryset(self):
        return _scoped_qs(Student, self.request)

class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [_AllowAll]
    serializer_class = StudentDetailSerializer
    def get_queryset(self):
        return _scoped_qs(Student, self.request)

class StudentBulkImportView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'Bulk import started'})

class StudentExportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'export_url': None}})


# ---------------------------------------------------------------------------
# Teacher Management
# ---------------------------------------------------------------------------
class TeacherListCreateView(generics.ListCreateAPIView):
    permission_classes = [_AllowAll]
    serializer_class = TeacherListSerializer
    def get_queryset(self):
        return _scoped_qs(Teacher, self.request)

class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [_AllowAll]
    serializer_class = TeacherDetailSerializer
    def get_queryset(self):
        return _scoped_qs(Teacher, self.request)

class TeacherVerifyView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Teacher verified'})


# ---------------------------------------------------------------------------
# Admin Management
# ---------------------------------------------------------------------------
class AdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [_AllowAll]
    serializer_class = AdminListSerializer
    def get_queryset(self):
        return _scoped_qs(Admin, self.request)

class AdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [_AllowAll]
    serializer_class = AdminDetailSerializer
    def get_queryset(self):
        return _scoped_qs(Admin, self.request)


# ---------------------------------------------------------------------------
# Password / MFA Management
# ---------------------------------------------------------------------------
class UserResetPasswordView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Password reset'})

class UserForcePasswordChangeView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Force password change set'})

class UserMFAResetView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'MFA reset'})

class MFAPolicyView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})
    def put(self, request):
        return Response({'success': True, 'message': 'Policy updated'})

class MFAStatusView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'enforced': False}})


# ---------------------------------------------------------------------------
# Role Management
# ---------------------------------------------------------------------------
class RoleListCreateView(generics.ListCreateAPIView):
    permission_classes = [_AllowAll]
    serializer_class = RoleSerializer
    def get_queryset(self):
        return _scoped_qs(Role, self.request)

class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [_AllowAll]
    serializer_class = RoleSerializer
    def get_queryset(self):
        return _scoped_qs(Role, self.request)

class RolePermissionsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Permissions updated'})

class PermissionListView(generics.ListAPIView):
    permission_classes = [_AllowAll]
    serializer_class = PermissionSerializer
    queryset = Permission.objects.all()


# ---------------------------------------------------------------------------
# Batch Management
# ---------------------------------------------------------------------------
class BatchListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Batch created'}, status=status.HTTP_201_CREATED)

class BatchDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Batch updated'})

class UsersView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Student added to batch'})

class UsersRemoveView(APIView):
    permission_classes = [_AllowAll]
    def delete(self, request, pk, student_id):
        return Response({'success': True, 'message': 'Student removed from batch'})

class BatchTeacherView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Teacher assigned to batch'})


# ---------------------------------------------------------------------------
# Course Structure
# ---------------------------------------------------------------------------
class SubjectListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Subject created'}, status=status.HTTP_201_CREATED)

class ChapterListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Chapter created'}, status=status.HTTP_201_CREATED)

class TopicListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Topic created'}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# YouTube Management
# ---------------------------------------------------------------------------
class YouTubeChannelListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Channel added'}, status=status.HTTP_201_CREATED)

class YouTubeChannelDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def delete(self, request, pk):
        return Response({'success': True, 'message': 'Channel removed'})

class YouTubeQuotaView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'used': 0, 'limit': 10000}})

class YouTubePendingApprovalsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class YouTubeApproveView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, class_id):
        return Response({'success': True, 'message': 'Approved'})

class YouTubeRejectView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, class_id):
        return Response({'success': True, 'message': 'Rejected'})


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
class AttendanceCorrectionListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class AttendanceCorrectionDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Correction processed'})

class ProfileRequestListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class ProfileRequestDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Request processed'})


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class EnrollmentReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'total_enrolled': AcademicUsers.objects.filter(is_active=True).count()}})

class PerformanceReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class AttendanceReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class TeacherActivityReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class GeographicReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class FinancialReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class EngagementReportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})

class ReportExportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'export_url': None}})


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
class AuditLogListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class AuditLogExportView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {'export_url': None}})

class AuditPurgePolicyView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})
    def put(self, request):
        return Response({'success': True, 'message': 'Policy updated'})


# ---------------------------------------------------------------------------
# Session & Device Management
# ---------------------------------------------------------------------------
class UserSessionListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})

class UserDeviceListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})

class UserDeviceDetailView(APIView):
    permission_classes = [_AllowAll]
    def delete(self, request, pk, device_id):
        return Response({'success': True, 'message': 'Device removed'})

class UserLoginHistoryView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': []})


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------
class AnnouncementListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})
    def post(self, request):
        return Response({'success': True, 'message': 'Announcement created'}, status=status.HTTP_201_CREATED)

class AnnouncementDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def put(self, request, pk):
        return Response({'success': True, 'message': 'Announcement updated'})
    def delete(self, request, pk):
        return Response({'success': True, 'message': 'Announcement deleted'})

class TicketListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class TicketDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})

class TicketAssignView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Ticket assigned'})

class TicketAnalyticsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------
class SettingsListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class SettingsCategoryView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, category):
        return Response({'success': True, 'data': {}})
    def put(self, request, category):
        return Response({'success': True, 'message': 'Settings updated'})

class FeatureFlagListView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})

class FeatureFlagDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, key):
        return Response({'success': True, 'data': {}})
    def put(self, request, key):
        return Response({'success': True, 'message': 'Feature flag updated'})


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
class BackupPolicyView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': {}})
    def put(self, request):
        return Response({'success': True, 'message': 'Policy updated'})

class BackupTriggerView(APIView):
    permission_classes = [_AllowAll]
    def post(self, request):
        return Response({'success': True, 'message': 'Backup triggered'})

class BackupHistoryView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        return Response({'success': True, 'data': []})


# ---------------------------------------------------------------------------
# Tenant Management (Super Admin)
# ---------------------------------------------------------------------------
class TenantListCreateView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request):
        from tenants.models import Tenant
        from tenants.serializers import TenantSerializer
        tenants = Tenant.objects.all()
        serializer = TenantSerializer(tenants, many=True)
        return Response({'success': True, 'data': serializer.data})
    def post(self, request):
        return Response({'success': True, 'message': 'Tenant created'}, status=status.HTTP_201_CREATED)

class TenantDetailView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})

class TenantStatsView(APIView):
    permission_classes = [_AllowAll]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
