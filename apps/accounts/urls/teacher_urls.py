"""
Teacher URLs
"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from accounts.views import teacher_views

app_name = 'teacher'


class _RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'dashboard': '/api/v1/teacher/dashboard',
                'profile': '/api/v1/teacher/profile',
                'students': '/api/v1/teacher/students',
                'classes': '/api/v1/teacher/classes',
                'tests': '/api/v1/teacher/tests',
                'materials': '/api/v1/teacher/materials',
                'batches': '/api/v1/teacher/batches',
                'attendance': '/api/v1/teacher/attendance/<class_id>',
                'announcements': '/api/v1/teacher/announcements',
                'tickets': '/api/v1/teacher/tickets',
            }
        }})


urlpatterns = [
    path('', _RootView.as_view(), name='root'),

    # Dashboard
    path('dashboard', teacher_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats', teacher_views.DashboardStatsView.as_view(), name='dashboard-stats'),

    # Profile
    path('profile', teacher_views.ProfileView.as_view(), name='profile'),
    path('youtube/connect', teacher_views.YouTubeConnectView.as_view(), name='youtube-connect'),
    path('youtube/disconnect', teacher_views.YouTubeDisconnectView.as_view(), name='youtube-disconnect'),
    path('youtube/status', teacher_views.YouTubeStatusView.as_view(), name='youtube-status'),

    # Students
    path('students', teacher_views.StudentListView.as_view(), name='student-list'),
    path('students/<uuid:pk>', teacher_views.StudentDetailView.as_view(), name='student-detail'),
    path('students/<uuid:pk>/profile', teacher_views.StudentProfileEditView.as_view(), name='student-profile-edit'),
    path('students/<uuid:pk>/performance', teacher_views.StudentPerformanceView.as_view(), name='student-performance'),
    path('students/<uuid:pk>/attendance', teacher_views.StudentAttendanceView.as_view(), name='student-attendance'),
    path('profile-requests', teacher_views.ProfileRequestListView.as_view(), name='profile-requests'),
    path('profile-requests/<uuid:pk>', teacher_views.ProfileRequestDetailView.as_view(), name='profile-request-detail'),

    # Classes
    path('classes', teacher_views.ClassListCreateView.as_view(), name='class-list'),
    path('classes/upcoming', teacher_views.ClassUpcomingView.as_view(), name='class-upcoming'),
    path('classes/completed', teacher_views.ClassCompletedView.as_view(), name='class-completed'),
    path('classes/<uuid:pk>', teacher_views.ClassDetailView.as_view(), name='class-detail'),
    path('classes/<uuid:pk>/start', teacher_views.ClassStartView.as_view(), name='class-start'),
    path('classes/<uuid:pk>/end', teacher_views.ClassEndView.as_view(), name='class-end'),
    path('classes/<uuid:pk>/students', teacher_views.ClassStudentListView.as_view(), name='class-students'),
    path('classes/<uuid:pk>/attendees', teacher_views.ClassAttendeesView.as_view(), name='class-attendees'),
    path('classes/<uuid:pk>/watch-stats', teacher_views.ClassWatchStatsView.as_view(), name='class-watch-stats'),

    # Tests
    path('tests', teacher_views.TestListCreateView.as_view(), name='test-list'),
    path('tests/<uuid:pk>', teacher_views.TestDetailView.as_view(), name='test-detail'),
    path('tests/<uuid:pk>/publish', teacher_views.TestPublishView.as_view(), name='test-publish'),
    path('tests/<uuid:pk>/close', teacher_views.TestCloseView.as_view(), name='test-close'),
    path('tests/<uuid:pk>/results', teacher_views.TestResultsView.as_view(), name='test-results'),
    path('tests/<uuid:pk>/analysis', teacher_views.TestAnalysisView.as_view(), name='test-analysis'),
    path('tests/<uuid:pk>/results/bulk-upload', teacher_views.TestResultsBulkUploadView.as_view(), name='test-results-bulk'),
    path('tests/<uuid:pk>/results/manual-upload', teacher_views.TestResultsManualUploadView.as_view(), name='test-results-manual'),
    path('questions', teacher_views.QuestionListCreateView.as_view(), name='question-list'),
    path('questions/<uuid:pk>', teacher_views.QuestionDetailView.as_view(), name='question-detail'),

    # Attendance
    path('attendance/<uuid:class_id>', teacher_views.AttendanceListCreateView.as_view(), name='attendance'),
    path('attendance/<uuid:pk>/edit', teacher_views.AttendanceEditView.as_view(), name='attendance-edit'),
    path('attendance/bulk-upload', teacher_views.AttendanceBulkUploadView.as_view(), name='attendance-bulk'),
    path('attendance/correction-request', teacher_views.AttendanceCorrectionRequestView.as_view(), name='attendance-correction'),
    path('attendance/correction-requests', teacher_views.AttendanceCorrectionListView.as_view(), name='attendance-corrections'),
    path('attendance/reports', teacher_views.AttendanceReportsView.as_view(), name='attendance-reports'),

    # Materials
    path('materials', teacher_views.MaterialListCreateView.as_view(), name='material-list'),
    path('materials/<uuid:pk>', teacher_views.MaterialDetailView.as_view(), name='material-detail'),

    # Batches
    path('batches', teacher_views.BatchListView.as_view(), name='batch-list'),
    path('batches/<uuid:pk>', teacher_views.BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<uuid:pk>/students', teacher_views.UsersListView.as_view(), name='users-list'),
    path('batches/<uuid:pk>/performance', teacher_views.BatchPerformanceView.as_view(), name='batch-performance'),

    # Communication
    path('announcements', teacher_views.AnnouncementCreateView.as_view(), name='announcement-create'),
    path('tickets', teacher_views.TicketListView.as_view(), name='ticket-list'),
    path('tickets/<uuid:pk>', teacher_views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/messages', teacher_views.TicketMessageView.as_view(), name='ticket-messages'),
    path('messages', teacher_views.MessageListCreateView.as_view(), name='messages'),
]
