"""Assessments - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from assessments.models import (
    Test, TestSection, Question, TestAttempt,
    TestAttemptAnswer, TestFeedback, OfflineTestMarks,
)
from assessments.serializers import (
    TestListSerializer, TestDetailSerializer, TestSectionSerializer,
    QuestionSerializer, TestAttemptSerializer, TestAttemptAnswerSerializer,
    TestFeedbackSerializer, OfflineTestMarksSerializer,
)

app_name = 'assessments'
# P removed — using IsAuthenticated default from settings


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'tests': '/api/v1/assessments/tests/',
                'questions': '/api/v1/assessments/questions/',
                'attempts': '/api/v1/assessments/attempts/',
                'feedback': '/api/v1/assessments/feedback/',
                'offline-marks': '/api/v1/assessments/offline-marks/',
            }
        }})


class TestList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Test.objects.all()
    serializer_class = TestListSerializer

class TestDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Test.objects.all()
    serializer_class = TestDetailSerializer

class TestSectionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    serializer_class = TestSectionSerializer
    def get_queryset(self):
        return TestSection.objects.filter(test_id=self.kwargs['pk'])

class QuestionList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

class QuestionDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

class AttemptList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = TestAttempt.objects.all()
    serializer_class = TestAttemptSerializer

class AttemptDetail(generics.RetrieveAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = TestAttempt.objects.all()
    serializer_class = TestAttemptSerializer

class FeedbackList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = TestFeedback.objects.all()
    serializer_class = TestFeedbackSerializer

class OfflineMarksList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = OfflineTestMarks.objects.all()
    serializer_class = OfflineTestMarksSerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('tests/', TestList.as_view(), name='test-list'),
    path('tests/<uuid:pk>/', TestDetail.as_view(), name='test-detail'),
    path('tests/<uuid:pk>/sections/', TestSectionList.as_view(), name='test-sections'),
    path('questions/', QuestionList.as_view(), name='question-list'),
    path('questions/<uuid:pk>/', QuestionDetail.as_view(), name='question-detail'),
    path('attempts/', AttemptList.as_view(), name='attempt-list'),
    path('attempts/<uuid:pk>/', AttemptDetail.as_view(), name='attempt-detail'),
    path('feedback/', FeedbackList.as_view(), name='feedback-list'),
    path('offline-marks/', OfflineMarksList.as_view(), name='offline-marks'),
]
