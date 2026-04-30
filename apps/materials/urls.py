"""Materials - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from materials.models import (
    StudyMaterial, MaterialAccess, PhotoGallery, Scholarship, TopperStudent,
)

app_name = 'materials'
# P removed — using IsAuthenticated default from settings


class StudyMaterialSerializer(s.ModelSerializer):
    class Meta:
        model = StudyMaterial
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class MaterialAccessSerializer(s.ModelSerializer):
    class Meta:
        model = MaterialAccess
        fields = '__all__'
        read_only_fields = ('id',)

class PhotoGallerySerializer(s.ModelSerializer):
    class Meta:
        model = PhotoGallery
        fields = '__all__'
        read_only_fields = ('id',)

class ScholarshipSerializer(s.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = '__all__'
        read_only_fields = ('id',)

class TopperStudentSerializer(s.ModelSerializer):
    class Meta:
        model = TopperStudent
        fields = '__all__'
        read_only_fields = ('id',)


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'materials': '/api/v1/materials/list/',
                'gallery': '/api/v1/materials/gallery/',
                'scholarships': '/api/v1/materials/scholarships/',
                'toppers': '/api/v1/materials/toppers/',
            }
        }})

class MaterialList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer

class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer

class GalleryList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = PhotoGallery.objects.all()
    serializer_class = PhotoGallerySerializer

class ScholarshipList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Scholarship.objects.all()
    serializer_class = ScholarshipSerializer

class TopperList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = TopperStudent.objects.all()
    serializer_class = TopperStudentSerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('list/', MaterialList.as_view(), name='material-list'),
    path('list/<uuid:pk>/', MaterialDetail.as_view(), name='material-detail'),
    path('gallery/', GalleryList.as_view(), name='gallery-list'),
    path('scholarships/', ScholarshipList.as_view(), name='scholarship-list'),
    path('toppers/', TopperList.as_view(), name='topper-list'),
]
