"""System Config - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from system_config.models import (
    SystemSetting, FeatureFlag, MFAPolicy,
    MaintenanceWindow, FounderInfo, EnquiryForm,
)

app_name = 'system_config'
# P removed — using IsAuthenticated default from settings


class SystemSettingSerializer(s.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class FeatureFlagSerializer(s.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class MFAPolicySerializer(s.ModelSerializer):
    class Meta:
        model = MFAPolicy
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class MaintenanceWindowSerializer(s.ModelSerializer):
    class Meta:
        model = MaintenanceWindow
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class FounderInfoSerializer(s.ModelSerializer):
    class Meta:
        model = FounderInfo
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class EnquiryFormSerializer(s.ModelSerializer):
    class Meta:
        model = EnquiryForm
        fields = '__all__'
        read_only_fields = ('id', 'submitted_at')


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'settings': '/api/v1/system/settings/',
                'feature-flags': '/api/v1/system/feature-flags/',
                'mfa-policies': '/api/v1/system/mfa-policies/',
                'maintenance': '/api/v1/system/maintenance/',
                'founders': '/api/v1/system/founders/',
                'enquiries': '/api/v1/system/enquiries/',
            }
        }})


class SettingList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer

class SettingDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer

class FeatureFlagList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer

class FeatureFlagDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer

class MFAPolicyList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = MFAPolicy.objects.all()
    serializer_class = MFAPolicySerializer

class MaintenanceList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = MaintenanceWindow.objects.all()
    serializer_class = MaintenanceWindowSerializer

class FounderList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = FounderInfo.objects.all()
    serializer_class = FounderInfoSerializer

class FounderDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = FounderInfo.objects.all()
    serializer_class = FounderInfoSerializer

class EnquiryList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = EnquiryForm.objects.all()
    serializer_class = EnquiryFormSerializer

class EnquiryDetail(generics.RetrieveAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = EnquiryForm.objects.all()
    serializer_class = EnquiryFormSerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('settings/', SettingList.as_view(), name='settings-list'),
    path('settings/<uuid:pk>/', SettingDetail.as_view(), name='settings-detail'),
    path('feature-flags/', FeatureFlagList.as_view(), name='feature-flags'),
    path('feature-flags/<uuid:pk>/', FeatureFlagDetail.as_view(), name='feature-flag-detail'),
    path('mfa-policies/', MFAPolicyList.as_view(), name='mfa-policies'),
    path('maintenance/', MaintenanceList.as_view(), name='maintenance'),
    path('founders/', FounderList.as_view(), name='founders'),
    path('founders/<uuid:pk>/', FounderDetail.as_view(), name='founder-detail'),
    path('enquiries/', EnquiryList.as_view(), name='enquiries'),
    path('enquiries/<uuid:pk>/', EnquiryDetail.as_view(), name='enquiry-detail'),
]
