"""
LMS Enterprise - Root URL Configuration

URL Map:
    /admin/              → Django Built-in Admin Panel
    /staff/*             → Staff Dashboard (custom admin pages)
    /student/dashboard/  → Student Dashboard
    /teacher/dashboard/  → Teacher Dashboard
    /api/v1/*            → REST API endpoints
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

# Load custom admin site configuration (dashboard stats, branding)
import core.enf_admin_site as enf_admin_site  # noqa: F401

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class APIRootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({
            'success': True,
            'application': 'LMS Enterprise API',
            'version': 'v1',
            'endpoints': {
                'auth': '/api/v1/auth/',
                'student': '/api/v1/student/',
                'teacher': '/api/v1/teacher/',
                'admin': '/api/v1/admin/',
                'tenants': '/api/v1/tenants/',
                'academics': '/api/v1/academics/',
                'classes': '/api/v1/classes/',
                'assessments': '/api/v1/assessments/',
                'attendance': '/api/v1/attendance/',
                'materials': '/api/v1/materials/',
                'communication': '/api/v1/communication/',
                'sessions': '/api/v1/sessions/',
                'audit': '/api/v1/audit/',
                'system': '/api/v1/system/',
                'scheduling': '/api/v1/scheduling/',
            }
        })




class HealthCheckView(APIView):
    """Health check endpoint for monitoring and load balancers."""
    permission_classes = []
    authentication_classes = []
    throttle_classes = []
    def get(self, request):
        import django
        from django.db import connection
        health = {
            'status': 'healthy',
            'django_version': django.__version__,
            'database': 'unknown',
        }
        try:
            connection.ensure_connection()
            health['database'] = 'connected'
        except Exception as e:
            health['status'] = 'degraded'
            health['database'] = str(e)
        return Response(health)

# ============================================================================
# CORE URL PATTERNS
# ============================================================================
urlpatterns = [
    # ── Django Built-in Admin Panel ──
    path('admin/switch-tenant/', include('tenants.admin_urls')),
    path('admin/', admin.site.urls),

    # ── Health Check ──
    path('health/', HealthCheckView.as_view(), name='health-check'),

    # ── API Root ──
    path('api/v1/', APIRootView.as_view(), name='api-root'),

    # ── API v1 Endpoints ──
    path('api/v1/auth/', include('accounts.urls.auth_urls')),
    path('api/v1/student/', include('accounts.urls.student_urls')),
    path('api/v1/teacher/', include('accounts.urls.teacher_urls')),
    path('api/v1/admin/', include('accounts.urls.admin_urls')),

    # ── Module APIs ──
    path('api/v1/tenants/', include('tenants.urls')),
    path('api/v1/academics/', include('academics.urls')),
    path('api/v1/classes/', include('classes.urls')),
    path('api/v1/assessments/', include('assessments.urls')),
    path('api/v1/attendance/', include('attendance.urls')),
    path('api/v1/materials/', include('materials.urls')),
    path('api/v1/communication/', include('communication.urls')),
    path('api/v1/sessions/', include('sessions_tracking.urls')),
    path('api/v1/audit/', include('audit.urls')),
    path('api/v1/system/', include('system_config.urls')),
    path('api/v1/scheduling/', include('scheduling.urls')),
]


# ============================================================================
# FRONTEND ROUTES — Public Pages
# ============================================================================
from core.frontend_views import (
    HomeView, LoginView, RegisterView, LogoutView,
    StudentDashboardView, TeacherDashboardView, AdminDashboardView,
    ProgramsView, PartnersView, ScholarshipsView, NewsView,
    AboutView, FounderView, ManagementView, EnquiryView,
    GalleryView,
)

urlpatterns += [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Content pages
    path('programs/', ProgramsView.as_view(), name='programs'),
    path('partners/', PartnersView.as_view(), name='partners'),
    path('scholarships/', ScholarshipsView.as_view(), name='scholarships'),
    path('news/', NewsView.as_view(), name='news'),
    path('about/', AboutView.as_view(), name='about'),
    path('founder/', FounderView.as_view(), name='founder'),
    path('management/', ManagementView.as_view(), name='management'),
    path('enquiry/', EnquiryView.as_view(), name='enquiry'),
    path('gallery/', GalleryView.as_view(), name='gallery'),
]


# ============================================================================
# STUDENT DASHBOARD — /student/*
# ============================================================================
from core.student_exam_views import (
    ExamListView as StudentExamListView,
    ExamTakeView as StudentExamTakeView,
    ExamResultView as StudentExamResultView,
)
from assessments.views.student_exam_api import (
    AnswerAutoSaveView as StudentAnswerAutoSaveView,
    ProctorEventView as StudentProctorEventView,
    ProctorSnapshotView as StudentProctorSnapshotView,
    ExamSubmitView as StudentExamSubmitView,
    TestFeedbackSubmitView as StudentFeedbackSubmitView,
)
from core.student_schedule_view import StudentScheduleView
from core.student_resources_view import (
    ResourceListView as StudentResourceListView,
    ResourceViewAction as StudentResourceViewAction,
    ResourceDownloadAction as StudentResourceDownloadAction,
)

urlpatterns += [
    # Server-rendered portals (must come BEFORE SPA catch-all)
    path('student/exams/', StudentExamListView.as_view(), name='student-exam-list'),
    path('student/exams/<uuid:test_id>/take/', StudentExamTakeView.as_view(), name='student-exam-take'),
    path('student/exams/<uuid:test_id>/result/<uuid:attempt_id>/', StudentExamResultView.as_view(), name='student-exam-result'),
    # Phase 3 — REST endpoints (auto-save, proctoring, submit)
    path('student/exams/<uuid:test_id>/api/answer/',        StudentAnswerAutoSaveView.as_view(),  name='student-exam-api-answer'),
    path('student/exams/<uuid:test_id>/api/proctor-event/', StudentProctorEventView.as_view(),    name='student-exam-api-proctor-event'),
    path('student/exams/<uuid:test_id>/api/snapshot/',      StudentProctorSnapshotView.as_view(), name='student-exam-api-snapshot'),
    path('student/exams/<uuid:test_id>/api/submit/',        StudentExamSubmitView.as_view(),      name='student-exam-api-submit'),
    path('student/exams/<uuid:test_id>/api/feedback/',      StudentFeedbackSubmitView.as_view(),  name='student-exam-api-feedback'),
    path('student/schedule/', StudentScheduleView.as_view(), name='student-schedule'),
    path('student/resources/', StudentResourceListView.as_view(), name='student-resources'),
    path('student/resources/<uuid:material_id>/view/', StudentResourceViewAction.as_view(), name='student-resource-view'),
    path('student/resources/<uuid:material_id>/download/', StudentResourceDownloadAction.as_view(), name='student-resource-download'),

    # React SPA dashboard
    path('student/dashboard/', StudentDashboardView.as_view(), name='student-dashboard'),
    re_path(r'^student/dashboard/(?P<path>.*)$', StudentDashboardView.as_view(), name='student-dashboard-spa'),
]


# ============================================================================
# TEACHER DASHBOARD — /teacher/*
# ============================================================================
from core.teacher_offline_marks import (
    TeacherOfflineMarksView, TeacherTestApiView, TeacherTestReportView,
)
from core.teacher_published_tests import TeacherPublishedTestsView

urlpatterns += [
    # Server-rendered teacher pages — must come BEFORE the SPA catch-all
    path('teacher/offline-marks/',   TeacherOfflineMarksView.as_view(), name='teacher-offline-marks'),
    path('teacher/test-report/',     TeacherTestReportView.as_view(),   name='teacher-test-report'),
    path('teacher/api/tests/',       TeacherTestApiView.as_view(),      name='teacher-api-tests'),
    path('teacher/published-tests/', TeacherPublishedTestsView.as_view(), name='teacher-published-tests'),

    path('teacher/dashboard/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
    re_path(r'^teacher/dashboard/(?P<path>.*)$', TeacherDashboardView.as_view(), name='teacher-dashboard-spa'),
]


# ============================================================================
# STAFF DASHBOARD — /staff/*  (formerly "Admin Dashboard")
# This is the custom admin interface built with Django templates.
# Django's built-in admin panel lives at /admin/ separately.
# ============================================================================
from core.admin_page_views import (
    AnalyticsView, MonitoringView, SubjectsView, BatchesView,
    ProgramsAdminView, AcademicSessionsView, TestsView, QuestionsView,
    TestReportsView, SchoolsView, TeachersView, TeacherAttendanceView,
    StudentsView, StudentAttendanceView, LiveClassesView, StudyMaterialsView,
    AnnouncementsView, TicketsView, TenantsView, SettingsView,
    AuditView, ProfileView, NotificationsView,
    StaffRolesView, IntegrationsView, ReportsView, ReportRunView, WebsiteSettingsView,
    ExamManagementView, ComplianceView, AIFeaturesView, DashboardIntegrationView,
    AutoGradeView,
)
from assessments.views.admin_exam_views import (
    ExamListView, ExamCreateView, ExamEditView, ExamDetailView,
    ExamPublishView, ExamUnpublishView, ExamArchiveView, ExamDeleteView,
    ExamSectionCreateView, ExamFeatureFlagsView,
    QuestionListView, QuestionCreateView, QuestionEditView, QuestionDeleteView,
)
from assessments.views.phase4_views import (
    QuestionImportView, question_import_template,
    ZipExportPickerView,
    TestVersionListView, TestVersionSnapshotView, TestVersionRestoreView, TestVersionDiffView,
    AIInsightsView, UnderperformerListView, ExamReportsView, export_exam_report_csv,
    ExamThresholdsView,
)

urlpatterns += [
    # Staff Dashboard — Main
    path('staff/dashboard/', AdminDashboardView.as_view(), name='staff-dashboard'),

    # Staff Dashboard — Analytics & Monitoring
    path('staff/analytics/', AnalyticsView.as_view(), name='staff-analytics'),
    path('staff/monitoring/', MonitoringView.as_view(), name='staff-monitoring'),

    # Staff Dashboard — Academic Management
    path('staff/subjects/', SubjectsView.as_view(), name='staff-subjects'),
    path('staff/batches/', BatchesView.as_view(), name='staff-batches'),
    path('staff/programs/', ProgramsAdminView.as_view(), name='staff-programs'),
    path('staff/sessions/', AcademicSessionsView.as_view(), name='staff-sessions'),

    # Staff Dashboard — Exams & Assessments (Phase 2)
    path('staff/exams/',                                ExamListView.as_view(),          name='staff-exams'),
    path('staff/exams/new/',                            ExamCreateView.as_view(),        name='staff-exam-create'),
    path('staff/exams/flags/',                          ExamFeatureFlagsView.as_view(),  name='staff-exam-flags'),
    path('staff/exams/questions/',                      QuestionListView.as_view(),      name='staff-exam-questions'),
    path('staff/exams/questions/new/',                  QuestionCreateView.as_view(),    name='staff-exam-question-create'),
    path('staff/exams/questions/<uuid:qid>/edit/',      QuestionEditView.as_view(),      name='staff-exam-question-edit'),
    path('staff/exams/questions/<uuid:qid>/delete/',    QuestionDeleteView.as_view(),    name='staff-exam-question-delete'),
    path('staff/exams/<uuid:test_id>/',                 ExamDetailView.as_view(),        name='staff-exam-detail'),
    path('staff/exams/<uuid:test_id>/edit/',            ExamEditView.as_view(),          name='staff-exam-edit'),
    path('staff/exams/<uuid:test_id>/publish/',         ExamPublishView.as_view(),       name='staff-exam-publish'),
    path('staff/exams/<uuid:test_id>/unpublish/',       ExamUnpublishView.as_view(),     name='staff-exam-unpublish'),
    path('staff/exams/<uuid:test_id>/archive/',         ExamArchiveView.as_view(),       name='staff-exam-archive'),
    path('staff/exams/<uuid:test_id>/delete/',          ExamDeleteView.as_view(),        name='staff-exam-delete'),
    path('staff/exams/<uuid:test_id>/sections/new/',    ExamSectionCreateView.as_view(), name='staff-exam-section-create'),

    # Staff Dashboard — Exams Phase 4 (bulk import + version control)
    path('staff/exams/import/',                         QuestionImportView.as_view(),    name='staff-exam-import'),
    path('staff/exams/import/template/',                question_import_template,        name='staff-exam-import-template'),
    path('staff/exams/export-zip/',                     ZipExportPickerView.as_view(),   name='staff-exam-export-zip-picker'),
    path('staff/exams/<uuid:test_id>/versions/',        TestVersionListView.as_view(),   name='staff-exam-versions'),
    path('staff/exams/<uuid:test_id>/versions/snapshot/', TestVersionSnapshotView.as_view(), name='staff-exam-version-snapshot'),
    path('staff/exams/<uuid:test_id>/versions/diff/',   TestVersionDiffView.as_view(),   name='staff-exam-version-diff'),
    path('staff/exams/<uuid:test_id>/versions/<uuid:version_id>/restore/', TestVersionRestoreView.as_view(), name='staff-exam-version-restore'),

    # Staff Dashboard — Analytics & Alerting (Phase 4)
    path('staff/analytics/exam-reports/',               ExamReportsView.as_view(),       name='staff-exam-reports'),
    path('staff/analytics/exam-reports/export/',        export_exam_report_csv,          name='staff-exam-reports-export'),
    path('staff/analytics/ai-insights/',                AIInsightsView.as_view(),        name='staff-ai-insights'),
    path('staff/analytics/underperformers/',            UnderperformerListView.as_view(), name='staff-underperformers'),
    path('staff/analytics/thresholds/',                 ExamThresholdsView.as_view(),    name='staff-exam-thresholds'),

    # Staff Dashboard — Assessments (legacy read-only views, kept for back-compat)
    path('staff/tests/', TestsView.as_view(), name='staff-tests'),
    path('staff/questions/', QuestionsView.as_view(), name='staff-questions'),
    path('staff/test-reports/', TestReportsView.as_view(), name='staff-test-reports'),

    # Staff Dashboard — People Management
    path('staff/schools/', SchoolsView.as_view(), name='staff-schools'),
    path('staff/teachers/', TeachersView.as_view(), name='staff-teachers'),
    path('staff/teacher-attendance/', TeacherAttendanceView.as_view(), name='staff-teacher-attendance'),
    path('staff/students/', StudentsView.as_view(), name='staff-students'),
    path('staff/student-attendance/', StudentAttendanceView.as_view(), name='staff-student-attendance'),

    # Staff Dashboard — Content & Classes
    path('staff/live-classes/', LiveClassesView.as_view(), name='staff-live-classes'),
    path('staff/study-materials/', StudyMaterialsView.as_view(), name='staff-study-materials'),

    # Staff Dashboard — Communication
    path('staff/announcements/', AnnouncementsView.as_view(), name='staff-announcements'),
    path('staff/tickets/', TicketsView.as_view(), name='staff-tickets'),

    # Staff Dashboard — System
    path('staff/tenants/', TenantsView.as_view(), name='staff-tenants'),
    path('staff/settings/', SettingsView.as_view(), name='staff-settings'),
    path('staff/audit/', AuditView.as_view(), name='staff-audit'),
    path('staff/profile/', ProfileView.as_view(), name='staff-profile'),
    path('staff/notifications/', NotificationsView.as_view(), name='staff-notifications'),

    # Staff Dashboard — Advanced
    path('staff/staff-roles/', StaffRolesView.as_view(), name='staff-roles'),
    path('staff/integrations/', IntegrationsView.as_view(), name='staff-integrations'),
    path('staff/reports/', ReportsView.as_view(), name='staff-reports'),
    path('staff/reports/run/<uuid:template_id>/', ReportRunView.as_view(), name='staff-report-run'),
    path('staff/website-settings/', WebsiteSettingsView.as_view(), name='staff-website-settings'),
    path('staff/exam-management/', ExamManagementView.as_view(), name='staff-exam-management'),
    path('staff/compliance/', ComplianceView.as_view(), name='staff-compliance'),
    path('staff/ai-features/', AIFeaturesView.as_view(), name='staff-ai-features'),
    path('staff/dashboard-integration/', DashboardIntegrationView.as_view(), name='staff-dashboard-integration'),
    path('staff/exam/<uuid:test_id>/grade/', AutoGradeView.as_view(), name='staff-auto-grade'),
]


# ============================================================================
# STATIC & MEDIA (Development)
# ============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
