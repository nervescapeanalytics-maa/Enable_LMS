"""
EduAssist - REST Serializers
"""
from rest_framework import serializers
from .models import ChatConversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'created_at')
        read_only_fields = ('id', 'created_at')


class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ('id', 'title', 'is_active', 'created_at', 'updated_at', 'messages', 'message_count')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations (no messages)."""
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ('id', 'title', 'is_active', 'created_at', 'updated_at', 'message_count')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatSendMessageSerializer(serializers.Serializer):
    """Input serializer for sending a message to EduAssist."""
    message = serializers.CharField(max_length=5000)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
