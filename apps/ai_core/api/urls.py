from django.urls import path

from . import views

urlpatterns = [
    path("features/",             views.FeatureCatalogView.as_view(),   name="ai-features"),
    path("doubt-solver/",         views.DoubtSolveView.as_view(),       name="ai-doubt-solver"),
    path("study-planner/",        views.StudyPlannerView.as_view(),     name="ai-study-planner"),
    path("practice-quiz/",        views.PracticeQuizView.as_view(),     name="ai-practice-quiz"),
    path("performance-insights/", views.PerformanceInsightsView.as_view(), name="ai-performance"),
    path("learning-path/",        views.LearningPathView.as_view(),     name="ai-learning-path"),
    path("adaptive-learning/",    views.AdaptiveLearningView.as_view(), name="ai-adaptive"),
    path("exam-result-planning/", views.ExamResultPlanningView.as_view(), name="ai-exam-result"),
    path("feedback/",             views.FeedbackView.as_view(),         name="ai-feedback"),
    path("me/export/",            views.MyAIDataExportView.as_view(),   name="ai-me-export"),
    path("me/erase/",             views.MyAIDataDeleteView.as_view(),   name="ai-me-erase"),
]
