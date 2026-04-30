"""
EduAssist - API Views

Endpoints:
- POST /api/v1/eduassist/chat/  — Send a message and get AI response
- GET  /api/v1/eduassist/conversations/  — List user's conversations
- GET  /api/v1/eduassist/conversations/<id>/  — Get conversation with messages
- DELETE /api/v1/eduassist/conversations/<id>/  — Close a conversation
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ChatConversation
from .serializers import (
    ChatConversationSerializer,
    ChatConversationListSerializer,
    ChatSendMessageSerializer,
)
from .chat_service import handle_chat_message


class EduAssistRootView(APIView):
    def get(self, request):
        return Response({
            'success': True,
            'data': {
                'name': 'EduAssist',
                'description': 'AI-powered helper for the LMS platform',
                'endpoints': {
                    'chat': '/api/v1/eduassist/chat/',
                    'conversations': '/api/v1/eduassist/conversations/',
                },
            }
        })


class ChatView(APIView):
    """
    POST /api/v1/eduassist/chat/
    Send a message to EduAssist and receive a response.
    """
    def post(self, request):
        ser = ChatSendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        message = ser.validated_data['message']
        conversation_id = ser.validated_data.get('conversation_id')

        # Get user info from request
        # In a real system, this comes from JWT token
        user = request.user
        user_id = getattr(user, 'id', None)
        user_name = getattr(user, 'full_name', None) or getattr(user, 'first_name', 'User')

        # Determine user role
        user_role = 'student'  # default
        user_type = request.headers.get('X-User-Type', '').lower()
        if user_type in ('admin', 'teacher', 'student'):
            user_role = user_type
        elif hasattr(user, '_meta'):
            model_name = user._meta.model_name.lower()
            if 'admin' in model_name:
                user_role = 'admin'
            elif 'teacher' in model_name:
                user_role = 'teacher'

        # Get tenant
        tenant = getattr(request, 'tenant', None)
        if not tenant and hasattr(user, 'tenant'):
            tenant = user.tenant

        try:
            result = handle_chat_message(
                tenant=tenant,
                user_id=user_id,
                user_name=user_name,
                user_role=user_role,
                message=message,
                conversation_id=conversation_id,
            )
            return Response({
                'success': True,
                'data': result,
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': 'I encountered a problem processing your message. Please try again.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationListView(generics.ListAPIView):
    """
    GET /api/v1/eduassist/conversations/
    List the current user's conversations (most recent first).
    """
    serializer_class = ChatConversationListSerializer

    def get_queryset(self):
        user = self.request.user
        user_id = getattr(user, 'id', None)
        return ChatConversation.objects.filter(
            user_id=user_id, is_active=True
        ).order_by('-updated_at')


class ConversationDetailView(generics.RetrieveDestroyAPIView):
    """
    GET /api/v1/eduassist/conversations/<id>/
    Retrieve a conversation with all messages.

    DELETE /api/v1/eduassist/conversations/<id>/
    Close (soft-delete) a conversation.
    """
    serializer_class = ChatConversationSerializer

    def get_queryset(self):
        user = self.request.user
        user_id = getattr(user, 'id', None)
        return ChatConversation.objects.filter(user_id=user_id)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
