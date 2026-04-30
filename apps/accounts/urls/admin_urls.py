"""
Admin URLs
"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from accounts.views import admin_views

app_name = 'admin_api'


class _RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'dashboard': '/api/v1/admin/dashboard',
                'students': '/api/v1/admin/students',
                'teachers': '/api/v1/admin/teachers',
                'admins': '/api/v1/admin/admins',
                'roles': '/api/v1/admin/roles',
                'batches': '/api/v1/admin/batches',
                'subjects': '/api/v1/admin/subjects',
                'reports': '/api/v1/admin/reports/',
                'audit-logs': '/api/v1/admin/audit-logs',
                'settings': '/api/v1/admin/settings',
                'tenants': '/api/v1/admin/tenants',
            }
        }})


urlpatterns = [
    path('', _RootView.as_view(), name='root'),

    # Dashboard
    path('dashboard', admin_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats', admin_views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/realtime', admin_views.DashboardRealtimeView.as_view(), name='dashboard-realtime'),

    # Admin Profile
    path('profile', admin_views.ProfileView.as_view(), name='profile'),
    path('profile/preferences', admin_views.PreferencesView.as_view(), name='preferences'),
    path('profile/mfa/setup', admin_views.MFASetupView.as_view(), name='mfa-setup'),
    path('profile/mfa/disable', admin_views.MFADisableView.as_view(), name='mfa-disable'),

    # User Management - Students
    path('students', admin_views.StudentListCreateView.as_view(), name='student-list'),
    path('students/<uuid:pk>', admin_views.StudentDetailView.as_view(), name='student-detail'),
    path('students/bulk-import', admin_views.StudentBulkImportView.as_view(), name='student-bulk-import'),
    path('students/export', admin_views.StudentExportView.as_view(), name='student-export'),

    # User Management - Teachers
    path('teachers', admin_views.TeacherListCreateView.as_view(), name='teacher-list'),
    path('teachers/<uuid:pk>', admin_views.TeacherDetailView.as_view(), name='teacher-detail'),
    path('teachers/<uuid:pk>/verify', admin_views.TeacherVerifyView.as_view(), name='teacher-verify'),

    # User Management - Admins
    path('admins', admin_views.AdminListCreateView.as_view(), name='admin-list'),
    path('admins/<uuid:pk>', admin_views.AdminDetailView.as_view(), name='admin-detail'),

    # Password/MFA Management
    path('users/<uuid:pk>/reset-password', admin_views.UserResetPasswordView.as_view(), name='user-reset-password'),
    path('users/<uuid:pk>/force-password-change', admin_views.UserForcePasswordChangeView.as_view(), name='user-force-password'),
    path('users/<uuid:pk>/mfa/reset', admin_views.UserMFAResetView.as_view(), name='user-mfa-reset'),
    path('mfa/policy', admin_views.MFAPolicyView.as_view(), name='mfa-policy'),
    path('mfa/status', admin_views.MFAStatusView.as_view(), name='mfa-status'),

    # Role Management
    path('roles', admin_views.RoleListCreateView.as_view(), name='role-list'),
    path('roles/<uuid:pk>', admin_views.RoleDetailView.as_view(), name='role-detail'),
    path('roles/<uuid:pk>/permissions', admin_views.RolePermissionsView.as_view(), name='role-permissions'),
    path('permissions', admin_views.PermissionListView.as_view(), name='permission-list'),

    # Batch Management
    path('batches', admin_views.BatchListCreateView.as_view(), name='batch-list'),
    path('batches/<uuid:pk>', admin_views.BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<uuid:pk>/students', admin_views.UsersView.as_view(), name='users-list'),
    path('batches/<uuid:pk>/students/<uuid:student_id>', admin_views.UsersRemoveView.as_view(), name='users-remove'),
    path('batches/<uuid:pk>/teachers', admin_views.BatchTeacherView.as_view(), name='batch-teachers'),

    # Course Structure
    path('subjects', admin_views.SubjectListCreateView.as_view(), name='subject-list'),
    path('chapters', admin_views.ChapterListCreateView.as_view(), name='chapter-list'),
    path('topics', admin_views.TopicListCreateView.as_view(), name='topic-list'),

    # YouTube
    path('youtube/channels', admin_views.YouTubeChannelListCreateView.as_view(), name='youtube-channels'),
    path('youtube/channels/<uuid:pk>', admin_views.YouTubeChannelDetailView.as_view(), name='youtube-channel-detail'),
    path('youtube/quota', admin_views.YouTubeQuotaView.as_view(), name='youtube-quota'),
    path('youtube/pending-approvals', admin_views.YouTubePendingApprovalsView.as_view(), name='youtube-pending'),
    path('youtube/approve/<uuid:class_id>', admin_views.YouTubeApproveView.as_view(), name='youtube-approve'),
    path('youtube/reject/<uuid:class_id>', admin_views.YouTubeRejectView.as_view(), name='youtube-reject'),

    # Approvals
    path('attendance/correction-requests', admin_views.AttendanceCorrectionListView.as_view(), name='attendance-corrections'),
    path('attendance/correction-requests/<uuid:pk>', admin_views.AttendanceCorrectionDetailView.as_view(), name='attendance-correction-detail'),
    path('profile-requests', admin_views.ProfileRequestListView.as_view(), name='profile-requests'),
    path('profile-requests/<uuid:pk>', admin_views.ProfileRequestDetailView.as_view(), name='profile-request-detail'),

    # Reports
    path('reports/enrollment', admin_views.EnrollmentReportView.as_view(), name='report-enrollment'),
    path('reports/performance', admin_views.PerformanceReportView.as_view(), name='report-performance'),
    path('reports/attendance', admin_views.AttendanceReportView.as_view(), name='report-attendance'),
    path('reports/teacher-activity', admin_views.TeacherActivityReportView.as_view(), name='report-teacher'),
    path('reports/geographic', admin_views.GeographicReportView.as_view(), name='report-geographic'),
    path('reports/financial', admin_views.FinancialReportView.as_view(), name='report-financial'),
    path('reports/engagement', admin_views.EngagementReportView.as_view(), name='report-engagement'),
    path('reports/export', admin_views.ReportExportView.as_view(), name='report-export'),

    # Audit
    path('audit-logs', admin_views.AuditLogListView.as_view(), name='audit-logs'),
    path('audit-logs/export', admin_views.AuditLogExportView.as_view(), name='audit-logs-export'),
    path('audit/purge-policy', admin_views.AuditPurgePolicyView.as_view(), name='audit-purge-policy'),

    # Session & Device Management
    path('users/<uuid:pk>/sessions', admin_views.UserSessionListView.as_view(), name='user-sessions'),
    path('users/<uuid:pk>/devices', admin_views.UserDeviceListView.as_view(), name='user-devices'),
    path('users/<uuid:pk>/devices/<uuid:device_id>', admin_views.UserDeviceDetailView.as_view(), name='user-device-detail'),
    path('users/<uuid:pk>/login-history', admin_views.UserLoginHistoryView.as_view(), name='user-login-history'),

    # Communication
    path('announcements', admin_views.AnnouncementListCreateView.as_view(), name='announcements'),
    path('announcements/<uuid:pk>', admin_views.AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('tickets', admin_views.TicketListView.as_view(), name='tickets'),
    path('tickets/<uuid:pk>', admin_views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/assign', admin_views.TicketAssignView.as_view(), name='ticket-assign'),
    path('tickets/analytics', admin_views.TicketAnalyticsView.as_view(), name='ticket-analytics'),

    # System Settings
    path('settings', admin_views.SettingsListView.as_view(), name='settings'),
    path('settings/<str:category>', admin_views.SettingsCategoryView.as_view(), name='settings-category'),
    path('feature-flags', admin_views.FeatureFlagListView.as_view(), name='feature-flags'),
    path('feature-flags/<str:key>', admin_views.FeatureFlagDetailView.as_view(), name='feature-flag-detail'),

    # Backup
    path('backup/policy', admin_views.BackupPolicyView.as_view(), name='backup-policy'),
    path('backup/trigger', admin_views.BackupTriggerView.as_view(), name='backup-trigger'),
    path('backup/history', admin_views.BackupHistoryView.as_view(), name='backup-history'),

    # Tenant Management (Super Admin)
    path('tenants', admin_views.TenantListCreateView.as_view(), name='tenants'),
    path('tenants/<uuid:pk>', admin_views.TenantDetailView.as_view(), name='tenant-detail'),
    path('tenants/<uuid:pk>/stats', admin_views.TenantStatsView.as_view(), name='tenant-stats'),
]
