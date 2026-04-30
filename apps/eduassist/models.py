"""
EduAssist - Chat Models

Stores chat conversations between users and the EduAssist AI helper.
Each conversation has multiple messages with role (user/assistant).
"""
import uuid
from django.db import models
from django.utils import timezone


class ChatConversation(models.Model):
    """A chat conversation between a user and EduAssist."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='chat_conversations'
    )

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10, help_text="STUDENT, TEACHER, or ADMIN")
    user_name = models.CharField(max_length=200, null=True, blank=True)

    title = models.CharField(
        max_length=500, default='New Conversation',
        help_text="Auto-generated from first message"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eduassist_conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['tenant', 'user_id'], name='idx_chat_user'),
        ]

    def __str__(self):
        return f"Chat: {self.user_name} — {self.title}"


class ChatMessage(models.Model):
    """A single message in a conversation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE,
        related_name='messages'
    )

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()

    # For tracking what context was injected (optional)
    context_summary = models.JSONField(
        null=True, blank=True,
        help_text="Summary of context injected for this response"
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'eduassist_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:80]}"
