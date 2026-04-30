"""Attendance - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from attendance.models import Attendance, AttendanceSummary, AttendanceCorrectionRequest
from rest_framework import serializers as s

app_name = 'attendance'
# P removed — using IsAuthenticated default from settings


class AttendanceSerializer(s.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('id',)

class AttendanceSummarySerializer(s.ModelSerializer):
    class Meta:
        model = AttendanceSummary
        fields = '__all__'
        read_only_fields = ('id',)

class CorrectionRequestSerializer(s.ModelSerializer):
    class Meta:
        model = AttendanceCorrectionRequest
        fields = '__all__'
        read_only_fields = ('id',)


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'list': '/api/v1/attendance/list/',
                'mark': '/api/v1/attendance/mark/',
                'corrections': '/api/v1/attendance/corrections/',
                'summary': '/api/v1/attendance/summary/',
            }
        }})

class AttendanceList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

class AttendanceDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

class MarkView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def post(self, request):
        return Response({'success': True, 'message': 'Attendance marked'})

class BulkMarkView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def post(self, request):
        return Response({'success': True, 'message': 'Bulk attendance marked'})

class CorrectionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AttendanceCorrectionRequest.objects.all()
    serializer_class = CorrectionRequestSerializer

class CorrectionDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AttendanceCorrectionRequest.objects.all()
    serializer_class = CorrectionRequestSerializer

class SummaryList(generics.ListAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AttendanceSummary.objects.all()
    serializer_class = AttendanceSummarySerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('list/', AttendanceList.as_view(), name='attendance-list'),
    path('list/<uuid:pk>/', AttendanceDetail.as_view(), name='attendance-detail'),
    path('mark/', MarkView.as_view(), name='attendance-mark'),
    path('bulk-mark/', BulkMarkView.as_view(), name='attendance-bulk-mark'),
    path('corrections/', CorrectionList.as_view(), name='correction-list'),
    path('corrections/<uuid:pk>/', CorrectionDetail.as_view(), name='correction-detail'),
    path('summary/', SummaryList.as_view(), name='attendance-summary'),
]
