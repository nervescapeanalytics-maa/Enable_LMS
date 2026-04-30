from django.contrib import admin
from django.utils.html import format_html
from sessions_tracking.models import UserDevice, UserSession, LoginHistory, UserActivity
from core.admin_utils import EnhancedModelAdmin, export_as_csv, export_as_json, colored_status


@admin.register(UserDevice)
class UserDeviceAdmin(EnhancedModelAdmin):
    list_display = ('device_name', 'device_type_badge', 'user_id_short', 'trusted_badge', 'blocked_badge', 'last_seen')
    list_filter = ('device_type', 'is_trusted', 'is_blocked')
    search_fields = ('device_name', 'user_id')
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'first_seen', 'last_seen')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'user_id', 'user_type'),
        }),
        ('Device', {
            'fields': (
                'device_name', 'device_type', 'device_fingerprint',
                'os_name', 'os_version', 'browser_name', 'browser_version',
                'screen_resolution', 'user_agent',
            ),
        }),
        ('Trust & push', {
            'fields': (
                'is_trusted', 'is_blocked', 'blocked_reason',
                'push_token', 'push_platform',
            ),
        }),
        ('Usage', {
            'fields': ('total_sessions', 'first_seen', 'last_seen', 'device_meta'),
        }),
    )

    def device_type_badge(self, obj):
        dt = getattr(obj, 'device_type', '')
        icons = {'DESKTOP': 'fa-desktop', 'MOBILE': 'fa-mobile-alt', 'TABLET': 'fa-tablet-alt', 'BROWSER': 'fa-globe'}
        icon = icons.get(dt, 'fa-question')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">'
            '<i class="fas {}"></i> {}</span>', icon, dt or '-'
        )
    device_type_badge.short_description = 'Device Type'

    def user_id_short(self, obj):
        uid = str(getattr(obj, 'user_id', ''))
        return format_html('<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;" title="{}">{}</span>', uid, uid[:8])
    user_id_short.short_description = 'User'

    def trusted_badge(self, obj):
        return colored_status(getattr(obj, 'is_trusted', False))
    trusted_badge.short_description = 'Trusted'

    def blocked_badge(self, obj):
        if getattr(obj, 'is_blocked', False):
            return format_html('<span style="color:#ef4444;font-weight:700;">BLOCKED</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    blocked_badge.short_description = 'Blocked'


@admin.register(UserSession)
class UserSessionAdmin(EnhancedModelAdmin):
    list_display = ('user_id_short', 'user_type', 'status_badge', 'ip_display', 'started_at', 'last_activity_at', 'duration_display')
    list_filter = ('status', 'user_type')
    search_fields = ('user_id', 'ip_address')
    date_hierarchy = 'started_at'
    actions = [export_as_csv, export_as_json]
    list_per_page = 50
    readonly_fields = ('id', 'started_at', 'last_activity_at', 'ended_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'user_id', 'user_type', 'device'),
        }),
        ('Tokens', {
            'fields': ('session_token', 'refresh_token_hash'),
        }),
        ('Network & geo', {
            'fields': (
                'ip_address', 'geo_city', 'geo_state', 'geo_country', 'geo_coordinates',
            ),
        }),
        ('Session lifecycle', {
            'fields': (
                'status', 'started_at', 'last_activity_at', 'ended_at', 'end_reason',
                'expires_at', 'total_active_seconds', 'is_primary_session',
                'concurrent_session_check',
            ),
        }),
        ('Metadata', {
            'fields': ('session_meta',),
        }),
    )

    def user_id_short(self, obj):
        uid = str(getattr(obj, 'user_id', ''))
        return format_html('<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;" title="{}">{}</span>', uid, uid[:8])
    user_id_short.short_description = 'User'

    def ip_display(self, obj):
        ip = getattr(obj, 'ip_address', '')
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            ip or '-'
        )
    ip_display.short_description = 'IP Address'

    def duration_display(self, obj):
        start = getattr(obj, 'started_at', None)
        last = getattr(obj, 'last_activity_at', None)
        if start and last:
            delta = last - start
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                return format_html('<span style="color:#94a3b8;">{}h {}m</span>', hours, minutes)
            return format_html('<span style="color:#94a3b8;">{}m</span>', minutes)
        return '-'
    duration_display.short_description = 'Duration'


@admin.register(LoginHistory)
class LoginHistoryAdmin(EnhancedModelAdmin):
    list_display = ('username_attempted', 'user_type', 'result_badge', 'ip_display', 'attempted_at', 'suspicious_badge')
    list_filter = ('result', 'is_suspicious', 'user_type')
    search_fields = ('username_attempted', 'ip_address')
    date_hierarchy = 'attempted_at'
    actions = [export_as_csv, export_as_json]
    list_per_page = 50
    readonly_fields = ('id', 'attempted_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'user_id', 'user_type'),
        }),
        ('Attempt', {
            'fields': ('username_attempted', 'ip_address', 'user_agent', 'device'),
        }),
        ('Outcome', {
            'fields': ('result', 'failure_reason', 'attempted_at', 'session_id'),
        }),
        ('Risk & geo', {
            'fields': (
                'is_suspicious', 'risk_score', 'risk_factors',
                'geo_city', 'geo_country',
            ),
        }),
    )

    def result_badge(self, obj):
        r = getattr(obj, 'result', '')
        colors = {'SUCCESS': '#10b981', 'FAILED': '#ef4444', 'BLOCKED': '#f59e0b', 'LOCKED': '#8b5cf6'}
        c = colors.get(r, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, r or '-'
        )
    result_badge.short_description = 'Result'

    def ip_display(self, obj):
        ip = getattr(obj, 'ip_address', '')
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            ip or '-'
        )
    ip_display.short_description = 'IP Address'

    def suspicious_badge(self, obj):
        if getattr(obj, 'is_suspicious', False):
            return format_html('<span style="color:#ef4444;font-weight:700;">&#9888; Suspicious</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    suspicious_badge.short_description = 'Suspicious'


@admin.register(UserActivity)
class UserActivityAdmin(EnhancedModelAdmin):
    list_display = ('user_id_short', 'activity_type_badge', 'activity_description_short', 'page_url_short', 'ip_display', 'resource_type', 'occurred_at')
    list_filter = ('activity_type',)
    search_fields = ('user_id', 'activity_description', 'page_url')
    date_hierarchy = 'occurred_at'
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'occurred_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'user_id', 'user_type', 'session'),
        }),
        ('Activity', {
            'fields': (
                'activity_type', 'activity_description',
                'resource_type', 'resource_id', 'resource_name',
                'page_url', 'referrer_url', 'ip_address', 'duration_seconds', 'occurred_at',
            ),
        }),
        ('Payload', {
            'fields': ('activity_data',),
        }),
    )

    def user_id_short(self, obj):
        uid = str(getattr(obj, 'user_id', ''))
        return format_html('<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;" title="{}">{}</span>', uid, uid[:8])
    user_id_short.short_description = 'User'

    def activity_type_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'activity_type', '-')
        )
    activity_type_badge.short_description = 'Activity'

    def activity_description_short(self, obj):
        desc = getattr(obj, 'activity_description', '') or ''
        short = desc[:60] + '…' if len(desc) > 60 else desc
        return format_html('<span title="{}">{}</span>', desc, short or '-')
    activity_description_short.short_description = 'Description'

    def page_url_short(self, obj):
        url = getattr(obj, 'page_url', '') or ''
        # Show only path
        from urllib.parse import urlparse
        try:
            path = urlparse(url).path or url
        except Exception:
            path = url
        short = path[:50] + '…' if len(path) > 50 else path
        return format_html(
            '<span style="font-family:monospace;font-size:0.75rem;color:#94a3b8;" title="{}">{}</span>',
            url, short or '-'
        )
    page_url_short.short_description = 'Page URL'

    def ip_display(self, obj):
        ip = getattr(obj, 'ip_address', '')
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            ip or '-'
        )
    ip_display.short_description = 'IP Address'
