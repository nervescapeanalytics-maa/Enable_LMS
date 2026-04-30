"""Academics - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from academics.models import (
    AcademicSession, Group, Category, Subject, SubjectSection,
    Chapter, Topic, Batch, Users, BatchTeacher,
    Language, State, City, Religion, School,
)
from academics.serializers import (
    AcademicSessionSerializer, GroupSerializer, CategorySerializer,
    SubjectSerializer, SubjectSectionSerializer, ChapterSerializer,
    TopicSerializer, BatchSerializer, UsersSerializer,
    BatchTeacherSerializer, LanguageSerializer, StateSerializer,
    CitySerializer, ReligionSerializer, SchoolSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response

app_name = 'academics'

# P removed — using IsAuthenticated default from settings


class AcademicsRootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'sessions': '/api/v1/academics/sessions/',
                'groups': '/api/v1/academics/groups/',
                'categories': '/api/v1/academics/categories/',
                'subjects': '/api/v1/academics/subjects/',
                'sections': '/api/v1/academics/sections/',
                'chapters': '/api/v1/academics/chapters/',
                'topics': '/api/v1/academics/topics/',
                'batches': '/api/v1/academics/batches/',
                'languages': '/api/v1/academics/languages/',
                'states': '/api/v1/academics/states/',
                'cities': '/api/v1/academics/cities/',
                'religions': '/api/v1/academics/religions/',
                'schools': '/api/v1/academics/schools/',
            }
        }})


# Generic List/Create and Detail views
class SessionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer

class SessionDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer

class GroupList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class GroupDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class CategoryList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class SubjectList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class SubjectDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class SectionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SubjectSection.objects.all()
    serializer_class = SubjectSectionSerializer

class SectionDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SubjectSection.objects.all()
    serializer_class = SubjectSectionSerializer

class ChapterList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer

class ChapterDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer

class TopicList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

class TopicDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

class BatchList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

class BatchDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

class UsersList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Users.objects.all()
    serializer_class = UsersSerializer

class BatchTeacherList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = BatchTeacher.objects.all()
    serializer_class = BatchTeacherSerializer

class LanguageList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

class StateList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = State.objects.all()
    serializer_class = StateSerializer

class CityList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = City.objects.all()
    serializer_class = CitySerializer

class ReligionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Religion.objects.all()
    serializer_class = ReligionSerializer

class SchoolList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = School.objects.all()
    serializer_class = SchoolSerializer


urlpatterns = [
    path('', AcademicsRootView.as_view(), name='root'),
    path('sessions/', SessionList.as_view(), name='session-list'),
    path('sessions/<uuid:pk>/', SessionDetail.as_view(), name='session-detail'),
    path('groups/', GroupList.as_view(), name='group-list'),
    path('groups/<uuid:pk>/', GroupDetail.as_view(), name='group-detail'),
    path('categories/', CategoryList.as_view(), name='category-list'),
    path('categories/<uuid:pk>/', CategoryDetail.as_view(), name='category-detail'),
    path('subjects/', SubjectList.as_view(), name='subject-list'),
    path('subjects/<uuid:pk>/', SubjectDetail.as_view(), name='subject-detail'),
    path('sections/', SectionList.as_view(), name='section-list'),
    path('sections/<uuid:pk>/', SectionDetail.as_view(), name='section-detail'),
    path('chapters/', ChapterList.as_view(), name='chapter-list'),
    path('chapters/<uuid:pk>/', ChapterDetail.as_view(), name='chapter-detail'),
    path('topics/', TopicList.as_view(), name='topic-list'),
    path('topics/<uuid:pk>/', TopicDetail.as_view(), name='topic-detail'),
    path('batches/', BatchList.as_view(), name='batch-list'),
    path('batches/<uuid:pk>/', BatchDetail.as_view(), name='batch-detail'),
    path('users/', UsersList.as_view(), name='users-list'),
    path('batch-teachers/', BatchTeacherList.as_view(), name='batch-teacher-list'),
    path('languages/', LanguageList.as_view(), name='language-list'),
    path('states/', StateList.as_view(), name='state-list'),
    path('cities/', CityList.as_view(), name='city-list'),
    path('religions/', ReligionList.as_view(), name='religion-list'),
    path('schools/', SchoolList.as_view(), name='school-list'),
]
