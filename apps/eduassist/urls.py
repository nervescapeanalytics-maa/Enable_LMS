"""EduAssist - URL Configuration"""
from django.urls import path
from . import views

app_name = 'eduassist'

urlpatterns = [
    path('', views.EduAssistRootView.as_view(), name='root'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
]
