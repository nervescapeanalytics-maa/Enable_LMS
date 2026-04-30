"""Classes - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from classes.models import (
    YouTubeChannel, ScheduledClass, ClassAccessToken, ClassWatchTime,
)

app_name = 'classes'
# P removed — using IsAuthenticated default from settings


class YouTubeChannelSerializer(s.ModelSerializer):
    class Meta:
        model = YouTubeChannel
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ScheduledClassSerializer(s.ModelSerializer):
    class Meta:
        model = ScheduledClass
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ClassAccessTokenSerializer(s.ModelSerializer):
    class Meta:
        model = ClassAccessToken
        fields = '__all__'
        read_only_fields = ('id',)

class ClassWatchTimeSerializer(s.ModelSerializer):
    class Meta:
        model = ClassWatchTime
        fields = '__all__'
        read_only_fields = ('id',)


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'scheduled': '/api/v1/classes/scheduled/',
                'youtube-channels': '/api/v1/classes/youtube-channels/',
                'access-tokens': '/api/v1/classes/access-tokens/',
                'watch-time': '/api/v1/classes/watch-time/',
            }
        }})

class ScheduledClassList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = ScheduledClass.objects.all()
    serializer_class = ScheduledClassSerializer

class ScheduledClassDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = ScheduledClass.objects.all()
    serializer_class = ScheduledClassSerializer

class YouTubeChannelList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = YouTubeChannel.objects.all()
    serializer_class = YouTubeChannelSerializer

class YouTubeChannelDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = YouTubeChannel.objects.all()
    serializer_class = YouTubeChannelSerializer

class AccessTokenList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = ClassAccessToken.objects.all()
    serializer_class = ClassAccessTokenSerializer

class WatchTimeList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = ClassWatchTime.objects.all()
    serializer_class = ClassWatchTimeSerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('scheduled/', ScheduledClassList.as_view(), name='class-list'),
    path('scheduled/<uuid:pk>/', ScheduledClassDetail.as_view(), name='class-detail'),
    path('youtube-channels/', YouTubeChannelList.as_view(), name='youtube-channels'),
    path('youtube-channels/<uuid:pk>/', YouTubeChannelDetail.as_view(), name='youtube-channel-detail'),
    path('access-tokens/', AccessTokenList.as_view(), name='access-token-list'),
    path('watch-time/', WatchTimeList.as_view(), name='watch-time-list'),
]
