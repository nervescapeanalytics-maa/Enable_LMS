"""Scheduling - URL Configuration"""
from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.SchedulingRootView.as_view(), name='root'),

    # ── Recurring Rules ──
    path('rules/', views.RecurringRuleListView.as_view(), name='rule-list'),
    path('rules/<uuid:pk>/', views.RecurringRuleDetailView.as_view(), name='rule-detail'),
    path('rules/<uuid:pk>/activate/', views.ActivateRuleView.as_view(), name='rule-activate'),
    path('rules/<uuid:pk>/pause/', views.PauseRuleView.as_view(), name='rule-pause'),
    path('rules/<uuid:pk>/duplicate/', views.DuplicateRuleView.as_view(), name='rule-duplicate'),

    # ── Enrollments ──
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment-list'),
    path('enrollments/bulk/', views.BulkEnrollView.as_view(), name='enrollment-bulk'),
    path('enrollments/<uuid:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment-detail'),

    # ── Blackout Dates ──
    path('blackout-dates/', views.BlackoutDateListView.as_view(), name='blackout-list'),
    path('blackout-dates/<uuid:pk>/', views.BlackoutDateDetailView.as_view(), name='blackout-detail'),

    # ── Class Attendance (per-session) ──
    path('attendance/<uuid:class_id>/', views.ClassAttendanceListView.as_view(), name='class-attendance'),
    path('attendance/<uuid:class_id>/bulk/', views.BulkAttendanceView.as_view(), name='class-attendance-bulk'),
]
