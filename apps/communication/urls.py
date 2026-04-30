"""Communication - URL Configuration"""
from django.urls import path
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as s
from communication.models import (
    SupportTicket, TicketMessage, Announcement,
    AnnouncementRead, DirectMessage, Notification,
)

app_name = 'communication'
# P removed — using IsAuthenticated default from settings


class TicketSerializer(s.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class TicketMessageSerializer(s.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class AnnouncementSerializer(s.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class DirectMessageSerializer(s.ModelSerializer):
    class Meta:
        model = DirectMessage
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class NotificationSerializer(s.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'tickets': '/api/v1/communication/tickets/',
                'announcements': '/api/v1/communication/announcements/',
                'messages': '/api/v1/communication/messages/',
                'notifications': '/api/v1/communication/notifications/',
            }
        }})

class TicketList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SupportTicket.objects.all()
    serializer_class = TicketSerializer

class TicketDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = SupportTicket.objects.all()
    serializer_class = TicketSerializer

class TicketMessageList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    serializer_class = TicketMessageSerializer
    def get_queryset(self):
        return TicketMessage.objects.filter(ticket_id=self.kwargs['pk'])

class AnnouncementList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

class AnnouncementDetail(generics.RetrieveUpdateDestroyAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

class MessageList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = DirectMessage.objects.all()
    serializer_class = DirectMessageSerializer

class NotificationList(generics.ListCreateAPIView):
    # permission_classes uses IsAuthenticated default from settings
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer


urlpatterns = [
    path('', RootView.as_view(), name='root'),
    path('tickets/', TicketList.as_view(), name='ticket-list'),
    path('tickets/<uuid:pk>/', TicketDetail.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/messages/', TicketMessageList.as_view(), name='ticket-messages'),
    path('announcements/', AnnouncementList.as_view(), name='announcement-list'),
    path('announcements/<uuid:pk>/', AnnouncementDetail.as_view(), name='announcement-detail'),
    path('messages/', MessageList.as_view(), name='message-list'),
    path('notifications/', NotificationList.as_view(), name='notification-list'),
]
