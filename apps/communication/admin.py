from django.contrib import admin
from django.utils.html import format_html
from communication.models import (
    SupportTicket, TicketMessage, Announcement, AnnouncementRead,
    DirectMessage, Notification
)
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    fields = ('sender_name', 'message', 'is_internal_note', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True


def close_tickets(modeladmin, request, queryset):
    count = queryset.update(status='CLOSED')
    modeladmin.message_user(request, f"Closed {count} tickets.")
close_tickets.short_description = "Close selected tickets"


def resolve_tickets(modeladmin, request, queryset):
    count = queryset.update(status='RESOLVED')
    modeladmin.message_user(request, f"Resolved {count} tickets.")
resolve_tickets.short_description = "Resolve selected tickets"


@admin.register(SupportTicket)
class SupportTicketAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = (
        'ticket_number', 'title', 'category_badge', 'priority_badge',
        'status_badge', 'created_display',
    )
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'title')
    date_hierarchy = 'created_at'
    inlines = [TicketMessageInline]
    actions = [export_as_csv, export_as_json, close_tickets, resolve_tickets]

    def category_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'category', '-')
        )
    category_badge.short_description = 'Category'

    def priority_badge(self, obj):
        p = getattr(obj, 'priority', '')
        colors = {'LOW': '#10b981', 'MEDIUM': '#3b82f6', 'HIGH': '#f59e0b', 'CRITICAL': '#ef4444', 'URGENT': '#ef4444'}
        c = colors.get(p, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:700;">{}</span>',
            c, c, p or '-'
        )
    priority_badge.short_description = 'Priority'


@admin.register(TicketMessage)
class TicketMessageAdmin(EnhancedModelAdmin):
    list_display = ('ticket', 'sender_name', 'internal_badge', 'created_display')
    list_filter = ('is_internal_note',)
    actions = [export_as_csv]

    def internal_badge(self, obj):
        if obj.is_internal_note:
            return format_html('<span style="color:#f59e0b;font-weight:600;">Internal</span>')
        return format_html('<span style="color:#64748b;">Public</span>')
    internal_badge.short_description = 'Type'


@admin.register(Announcement)
class AnnouncementAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('title', 'type_badge', 'target_audience', 'published_badge', 'pinned_badge', 'published_at')
    list_filter = ('announcement_type', 'target_audience', 'is_published', 'is_pinned')
    search_fields = ('title',)
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    def type_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'announcement_type', '-')
        )
    type_badge.short_description = 'Type'

    def published_badge(self, obj):
        return colored_status(getattr(obj, 'is_published', False))
    published_badge.short_description = 'Published'

    def pinned_badge(self, obj):
        if getattr(obj, 'is_pinned', False):
            return format_html('<span style="color:#f59e0b;">&#128204;</span>')
        return '-'
    pinned_badge.short_description = 'Pinned'


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(EnhancedModelAdmin):
    list_display = ('announcement', 'user_id', 'read_at', 'ack_badge')
    list_filter = ('acknowledged',)
    readonly_fields = ('id', 'read_at', 'acknowledged_at')
    actions = [export_as_csv]

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'announcement', 'user_id', 'user_type', 'read_at', 'acknowledged', 'acknowledged_at'),
        }),
    )

    def ack_badge(self, obj):
        return colored_status(getattr(obj, 'acknowledged', False))
    ack_badge.short_description = 'Acknowledged'


@admin.register(DirectMessage)
class DirectMessageAdmin(EnhancedModelAdmin):
    list_display = ('sender_name', 'recipient_name', 'subject', 'read_badge', 'created_display')
    list_filter = ('is_read',)
    search_fields = ('sender_name', 'recipient_name', 'subject')
    actions = [export_as_csv]

    def read_badge(self, obj):
        return colored_status(getattr(obj, 'is_read', False))
    read_badge.short_description = 'Read'


@admin.register(Notification)
class NotificationAdmin(EnhancedModelAdmin):
    list_display = ('user_id', 'notification_type', 'channel_badge', 'title', 'read_badge', 'delivered_badge')
    list_filter = ('notification_type', 'channel', 'is_read', 'is_delivered')
    search_fields = ('title',)
    actions = [export_as_csv, export_as_json]

    def channel_badge(self, obj):
        ch = getattr(obj, 'channel', '')
        colors = {'EMAIL': '#3b82f6', 'SMS': '#10b981', 'PUSH': '#f59e0b', 'IN_APP': '#8b5cf6'}
        c = colors.get(ch, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, ch or '-'
        )
    channel_badge.short_description = 'Channel'

    def read_badge(self, obj):
        return colored_status(getattr(obj, 'is_read', False))
    read_badge.short_description = 'Read'

    def delivered_badge(self, obj):
        return colored_status(getattr(obj, 'is_delivered', False))
    delivered_badge.short_description = 'Delivered'
