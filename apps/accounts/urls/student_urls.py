"""
Student URLs
"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from accounts.views import student_views

app_name = 'student'


class _RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'dashboard': '/api/v1/student/dashboard',
                'profile': '/api/v1/student/profile',
                'classes': '/api/v1/student/classes',
                'tests': '/api/v1/student/tests',
                'materials': '/api/v1/student/materials',
                'attendance': '/api/v1/student/attendance',
                'announcements': '/api/v1/student/announcements',
                'notifications': '/api/v1/student/notifications',
                'tickets': '/api/v1/student/tickets',
                'settings': '/api/v1/student/settings',
            }
        }})


urlpatterns = [
    path('', _RootView.as_view(), name='root'),

    # Dashboard
    path('dashboard', student_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats', student_views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/upcoming', student_views.DashboardUpcomingView.as_view(), name='dashboard-upcoming'),

    # Profile
    path('profile', student_views.ProfileView.as_view(), name='profile'),
    path('profile/change-request', student_views.ProfileChangeRequestView.as_view(), name='profile-change-request'),
    path('profile/change-requests', student_views.ProfileChangeRequestListView.as_view(), name='profile-change-requests'),

    # Classes
    path('classes', student_views.ClassListView.as_view(), name='class-list'),
    path('classes/upcoming', student_views.ClassUpcomingView.as_view(), name='class-upcoming'),
    path('classes/live', student_views.ClassLiveView.as_view(), name='class-live'),
    path('classes/<uuid:pk>', student_views.ClassDetailView.as_view(), name='class-detail'),
    path('classes/<uuid:pk>/access-token', student_views.ClassAccessTokenView.as_view(), name='class-access-token'),
    path('classes/<uuid:pk>/recording', student_views.ClassRecordingView.as_view(), name='class-recording'),
    path('classes/<uuid:pk>/join', student_views.ClassJoinView.as_view(), name='class-join'),
    path('classes/<uuid:pk>/leave', student_views.ClassLeaveView.as_view(), name='class-leave'),
    path('classes/<uuid:pk>/heartbeat', student_views.ClassHeartbeatView.as_view(), name='class-heartbeat'),

    # Tests
    path('tests', student_views.TestListView.as_view(), name='test-list'),
    path('tests/upcoming', student_views.TestUpcomingView.as_view(), name='test-upcoming'),
    path('tests/<uuid:pk>', student_views.TestDetailView.as_view(), name='test-detail'),
    path('tests/<uuid:pk>/start', student_views.TestStartView.as_view(), name='test-start'),
    path('tests/<uuid:pk>/submit', student_views.TestSubmitView.as_view(), name='test-submit'),
    path('tests/<uuid:pk>/result', student_views.TestResultView.as_view(), name='test-result'),
    path('tests/<uuid:pk>/solutions', student_views.TestSolutionsView.as_view(), name='test-solutions'),

    # Materials
    path('materials', student_views.MaterialListView.as_view(), name='material-list'),
    path('materials/<uuid:pk>', student_views.MaterialDetailView.as_view(), name='material-detail'),
    path('materials/<uuid:pk>/download', student_views.MaterialDownloadView.as_view(), name='material-download'),

    # Attendance
    path('attendance', student_views.AttendanceView.as_view(), name='attendance'),
    path('attendance/summary', student_views.AttendanceSummaryView.as_view(), name='attendance-summary'),
    path('attendance/calendar', student_views.AttendanceCalendarView.as_view(), name='attendance-calendar'),

    # Communication
    path('announcements', student_views.AnnouncementListView.as_view(), name='announcements'),
    path('notifications', student_views.NotificationListView.as_view(), name='notifications'),
    path('notifications/<uuid:pk>/read', student_views.NotificationReadView.as_view(), name='notification-read'),
    path('notifications/read-all', student_views.NotificationReadAllView.as_view(), name='notifications-read-all'),
    path('tickets', student_views.TicketListCreateView.as_view(), name='tickets'),
    path('tickets/<uuid:pk>', student_views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/messages', student_views.TicketMessageView.as_view(), name='ticket-messages'),
    path('messages', student_views.MessageListCreateView.as_view(), name='messages'),

    # Settings
    path('settings', student_views.SettingsView.as_view(), name='settings'),
]
