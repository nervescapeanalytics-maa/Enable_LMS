from django.contrib import admin
from django.utils.html import format_html
from realtime.models import RealtimeEvent
from core.admin_utils import EnhancedModelAdmin, export_as_csv, export_as_json, colored_status


@admin.register(RealtimeEvent)
class RealtimeEventAdmin(EnhancedModelAdmin):
    list_display = ('event_type_badge', 'target_type', 'target_channel', 'delivered_badge', 'priority_badge', 'created_display')
    list_filter = ('event_type', 'is_delivered', 'priority')
    search_fields = ('target_channel',)
    actions = [export_as_csv, export_as_json]
    list_per_page = 50
    readonly_fields = ('id', 'created_at', 'delivered_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant'),
        }),
        ('Event', {
            'fields': (
                'event_type', 'event_key', 'target_type', 'target_id',
                'target_channel', 'payload', 'priority',
            ),
        }),
        ('Delivery', {
            'fields': (
                'is_delivered', 'delivered_at', 'delivery_attempts', 'expires_at', 'created_at',
            ),
        }),
    )

    def event_type_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'event_type', '-')
        )
    event_type_badge.short_description = 'Event'

    def delivered_badge(self, obj):
        return colored_status(getattr(obj, 'is_delivered', False))
    delivered_badge.short_description = 'Delivered'

    def priority_badge(self, obj):
        p = getattr(obj, 'priority', '')
        colors = {'LOW': '#94a3b8', 'NORMAL': '#3b82f6', 'HIGH': '#f59e0b', 'URGENT': '#ef4444'}
        c = colors.get(str(p).upper() if p else '', '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, p or '-'
        )
    priority_badge.short_description = 'Priority'
