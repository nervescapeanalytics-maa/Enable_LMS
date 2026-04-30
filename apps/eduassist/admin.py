"""EduAssist - Django Admin Registration"""
from django.contrib import admin
from .models import ChatConversation, ChatMessage


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_type', 'title', 'is_active', 'created_at', 'updated_at')
    list_filter = ('user_type', 'is_active', 'tenant')
    search_fields = ('user_name', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'user_id', 'user_type', 'user_name', 'title', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'short_content', 'created_at')
    list_filter = ('role',)
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'conversation', 'role', 'content', 'context_summary', 'created_at'),
        }),
    )

    def short_content(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    short_content.short_description = 'Content'
