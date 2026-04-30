"""Audit - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from audit.models import AuditLog, AuditPurgePolicy, BackupPolicy, BackupHistory

app_name = 'audit'
# P removed — using IsAuthenticated default from settings


class AuditLogSerializer(s.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class PurgePolicySerializer(s.ModelSerializer):
    class Meta:
        model = AuditPurgePolicy
        fields = '__all__'
        read_only_fields = ('id',)

class BackupPolicySerializer(s.ModelSerializer):
    class Meta:
        model = BackupPolicy
        fields = '__all__'
        read_only_fields = ('id',)

class BackupHistorySerializer(s.ModelSerializer):
    class Meta:
        model = BackupHistory
        fields = '__all__'
        read_only_fields = ('id',)


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'logs': '/api/v1/audit/logs/',
                'purge-policies': '/api/v1/audit/purge-policies/',
                'backups': '/api/v1/audit/backups/',
                'backup-policies': '/api/v1/audit/backup-policies/',
            }
        }})

class AuditLogList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

class AuditLogDetail(generics.RetrieveAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

class PurgePolicyList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AuditPurgePolicy.objects.all()
    serializer_class = PurgePolicySerializer

class BackupPolicyList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = BackupPolicy.objects.all()
    serializer_class = BackupPolicySerializer

class BackupHistoryList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = BackupHistory.objects.all()
    serializer_class = BackupHistorySerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('logs/', AuditLogList.as_view(), name='audit-logs'),
    path('logs/<uuid:pk>/', AuditLogDetail.as_view(), name='audit-log-detail'),
    path('purge-policies/', PurgePolicyList.as_view(), name='purge-policies'),
    path('backups/', BackupHistoryList.as_view(), name='backup-list'),
    path('backup-policies/', BackupPolicyList.as_view(), name='backup-policies'),
]
