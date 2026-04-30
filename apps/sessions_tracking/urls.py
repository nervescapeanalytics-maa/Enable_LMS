"""Sessions Tracking - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from sessions_tracking.models import (
    UserDevice, UserSession, LoginHistory, UserActivity,
)

app_name = 'sessions_tracking'
# P removed — using IsAuthenticated default from settings


class UserDeviceSerializer(s.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class UserSessionSerializer(s.ModelSerializer):
    class Meta:
        model = UserSession
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class LoginHistorySerializer(s.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = '__all__'
        read_only_fields = ('id',)

class UserActivitySerializer(s.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'
        read_only_fields = ('id',)


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'sessions': '/api/v1/sessions/sessions/',
                'devices': '/api/v1/sessions/devices/',
                'login-history': '/api/v1/sessions/login-history/',
                'activity': '/api/v1/sessions/activity/',
            }
        }})

class SessionList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = UserSession.objects.all()
    serializer_class = UserSessionSerializer

class SessionDetail(generics.RetrieveDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = UserSession.objects.all()
    serializer_class = UserSessionSerializer

class DeviceList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer

class LoginHistoryList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer

class ActivityList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('sessions/', SessionList.as_view(), name='session-list'),
    path('sessions/<uuid:pk>/', SessionDetail.as_view(), name='session-detail'),
    path('devices/', DeviceList.as_view(), name='device-list'),
    path('login-history/', LoginHistoryList.as_view(), name='login-history'),
    path('activity/', ActivityList.as_view(), name='activity-list'),
]
