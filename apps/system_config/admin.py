from django.contrib import admin
from django.utils.html import format_html
from system_config.models import (
    SystemSetting, FeatureFlag, MFAPolicy,
    MaintenanceWindow, FounderInfo, EnquiryForm,
    AIFeatureConfig, AttendanceRule,
    IntegrationConfig, WebsiteSetting, ReportTemplate,
    WebsiteNews, Testimonial, FooterConfig, TickerItem,
)
from system_config.forms import (
    SystemSettingForm, FeatureFlagForm, MFAPolicyForm,
    MaintenanceWindowForm, FounderInfoForm,
    AIFeatureConfigForm,
    IntegrationConfigForm, WebsiteSettingForm,
    ReportTemplateForm, FooterConfigForm,
)
from communication.models import (
    Announcement, DirectMessage, Notification, SupportTicket, TicketMessage,
)
from core.admin_utils import (
    EnhancedModelAdmin, ImportExportMixin, export_as_csv,
    export_as_json, activate_selected, deactivate_selected, colored_status,
)


# ═══════════════════════════════════════════════════════════════════
# SYSTEM SETTING
# ═══════════════════════════════════════════════════════════════════
@admin.register(SystemSetting)
class SystemSettingAdmin(EnhancedModelAdmin):
    form = SystemSettingForm
    list_display = ('setting_key', 'value_type_badge', 'category_badge', 'secret_badge', 'editable_badge')
    list_filter = ('value_type', 'category', 'is_secret')
    search_fields = ('setting_key',)
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Setting Info', {
            'fields': ('tenant', 'setting_key', 'value_type', 'category', 'is_secret', 'is_editable', 'description'),
        }),
        ('Value', {
            'fields': ('setting_value', 'setting_json'),
        }),
        ('Audit', {
            'fields': ('updated_by_id', 'created_at', 'updated_at'),
        }),
    )

    def value_type_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'value_type', '-')
        )
    value_type_badge.short_description = 'Type'

    def category_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(139,92,246,0.1);color:#c084fc;font-weight:600;">{}</span>',
            getattr(obj, 'category', '-')
        )
    category_badge.short_description = 'Category'

    def secret_badge(self, obj):
        if getattr(obj, 'is_secret', False):
            return format_html('<span style="color:#ef4444;font-weight:700;">&#128274; Secret</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    secret_badge.short_description = 'Secret'

    def editable_badge(self, obj):
        return colored_status(getattr(obj, 'is_editable', False))
    editable_badge.short_description = 'Editable'


# ═══════════════════════════════════════════════════════════════════
# FEATURE FLAG
# ═══════════════════════════════════════════════════════════════════
@admin.register(FeatureFlag)
class FeatureFlagAdmin(EnhancedModelAdmin):
    form = FeatureFlagForm
    list_display = ('flag_key', 'flag_name', 'enabled_badge', 'rollout_display')
    list_filter = ('is_enabled',)
    search_fields = ('flag_key', 'flag_name')
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Flag Identity', {
            'fields': ('tenant', 'flag_key', 'flag_name', 'description'),
        }),
        ('Rollout & targeting', {
            'fields': ('is_enabled', 'rollout_percentage', 'start_date', 'end_date', 'allowed_user_types', 'allowed_user_ids'),
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
        }),
    )

    def enabled_badge(self, obj):
        if getattr(obj, 'is_enabled', False):
            return format_html('<span style="color:#10b981;font-weight:700;">&#9679; ON</span>')
        return format_html('<span style="color:#ef4444;font-weight:600;">&#9675; OFF</span>')
    enabled_badge.short_description = 'Enabled'

    def rollout_display(self, obj):
        pct = getattr(obj, 'rollout_percentage', 0) or 0
        color = '#10b981' if pct >= 80 else '#f59e0b' if pct >= 30 else '#94a3b8'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="flex:1;height:6px;background:rgba(99,102,241,0.1);border-radius:3px;overflow:hidden;max-width:100px;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:3px;"></div></div>'
            '<span style="font-size:0.78rem;color:{};font-weight:600;">{}%</span></div>',
            pct, color, color, pct
        )
    rollout_display.short_description = 'Rollout'


# ═══════════════════════════════════════════════════════════════════
# MFA POLICY
# ═══════════════════════════════════════════════════════════════════
@admin.register(MFAPolicy)
class MFAPolicyAdmin(EnhancedModelAdmin):
    form = MFAPolicyForm
    list_display = ('mfa_type', 'mandatory_badge', 'otp_length', 'otp_expiry_seconds', 'active_badge')
    list_filter = ('is_active', 'is_mandatory')
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Policy', {
            'fields': ('tenant', 'mfa_type', 'is_active', 'is_mandatory', 'applies_to_user_types'),
        }),
        ('OTP & security', {
            'fields': ('otp_length', 'otp_expiry_seconds', 'resend_cooldown_seconds', 'lockout_duration_minutes', 'max_attempts'),
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
        }),
    )

    def mandatory_badge(self, obj):
        if getattr(obj, 'is_mandatory', False):
            return format_html('<span style="color:#ef4444;font-weight:700;">Mandatory</span>')
        return format_html('<span style="color:#64748b;">Optional</span>')
    mandatory_badge.short_description = 'Mandatory'

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# MAINTENANCE WINDOW
# ═══════════════════════════════════════════════════════════════════
@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(EnhancedModelAdmin):
    form = MaintenanceWindowForm
    list_display = ('title', 'scope', 'start_time', 'end_time', 'active_badge')
    list_filter = ('is_active', 'scope')
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Window', {
            'fields': ('title', 'description', 'scope', 'start_time', 'end_time', 'is_active', 'notification_sent', 'affected_features'),
        }),
        ('Audit', {
            'fields': ('id', 'created_at'),
        }),
    )

    def active_badge(self, obj):
        if getattr(obj, 'is_active', False):
            return format_html('<span style="color:#f59e0b;font-weight:700;">&#9888; Active</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# FOUNDER INFO
# ═══════════════════════════════════════════════════════════════════
@admin.register(FounderInfo)
class FounderInfoAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = FounderInfoForm
    list_display = ('name', 'member_type', 'designation', 'active_badge', 'photo_preview')
    list_filter = ('is_active', 'member_type')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'

    def photo_preview(self, obj):
        url = getattr(obj, 'photo_url', None)
        if url:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;border:2px solid rgba(99,102,241,0.2);">',
                url
            )
        return '-'
    photo_preview.short_description = 'Photo'


# ═══════════════════════════════════════════════════════════════════
# ENQUIRY FORM
# ═══════════════════════════════════════════════════════════════════
@admin.register(EnquiryForm)
class EnquiryFormAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('name', 'email', 'phone', 'source_badge', 'status_badge', 'created_display')
    list_filter = ('status', 'source')
    search_fields = ('name', 'email', 'phone')
    date_hierarchy = 'created_at'
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Contact', {
            'fields': ('tenant', 'name', 'email', 'phone', 'subject', 'message', 'source'),
        }),
        ('Assignment', {
            'fields': ('status', 'assigned_to', 'notes', 'follow_up_date'),
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at'),
        }),
    )

    def source_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'source', '-')
        )
    source_badge.short_description = 'Source'


# ═══════════════════════════════════════════════════════════════════
# AI FEATURE CONFIG — NEW
# ═══════════════════════════════════════════════════════════════════
@admin.register(AIFeatureConfig)
class AIFeatureConfigAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = AIFeatureConfigForm
    list_display = (
        'feature_icon', 'feature_name', 'category_badge', 'scope_badge',
        'enabled_toggle_badge', 'provider_badge', 'rate_info', 'updated_display',
    )
    list_filter = ('is_enabled', 'category', 'integration_scope', 'provider')
    search_fields = ('feature_key', 'feature_name', 'description')
    list_editable = ()
    actions = [export_as_csv, export_as_json, 'enable_features', 'disable_features']
    ordering = ['sort_order', 'feature_name']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Feature Identity', {
            'fields': ('tenant', 'feature_key', 'feature_name', 'description', 'icon_class', 'sort_order', 'created_by'),
        }),
        ('Control', {
            'fields': ('is_enabled', 'category', 'integration_scope'),
        }),
        ('Provider & API', {
            'fields': ('provider', 'api_endpoint', 'api_key_reference'),
            'classes': ('collapse',),
        }),
        ('Rate Limits', {
            'fields': ('max_requests_per_hour', 'max_requests_per_user'),
            'classes': ('collapse',),
        }),
        ('Advanced', {
            'fields': ('config_json',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def feature_icon(self, obj):
        icon = getattr(obj, 'icon_class', 'fas fa-brain')
        return format_html(
            '<div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#8b5cf6);'
            'display:flex;align-items:center;justify-content:center;">'
            '<i class="{}" style="color:#fff;font-size:0.8rem;"></i></div>',
            icon
        )
    feature_icon.short_description = ''

    def category_badge(self, obj):
        colors = {
            'CONTENT': ('#8b5cf6', 'rgba(139,92,246,0.12)'),
            'ANALYTICS': ('#3b82f6', 'rgba(59,130,246,0.12)'),
            'ASSESSMENT': ('#f59e0b', 'rgba(245,158,11,0.12)'),
            'COMMUNICATION': ('#10b981', 'rgba(16,185,129,0.12)'),
            'AUTOMATION': ('#22d3ee', 'rgba(34,211,238,0.12)'),
        }
        cat = getattr(obj, 'category', '')
        fg, bg = colors.get(cat, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;color:{};background:{};">{}</span>',
            fg, bg, cat.replace('_', ' ').title() if cat else '-'
        )
    category_badge.short_description = 'Category'

    def scope_badge(self, obj):
        scope = getattr(obj, 'integration_scope', '')
        scope_colors = {
            'ADMIN': ('rgba(245,158,11,0.15)', '#fbbf24'),
            'TEACHER': ('rgba(16,185,129,0.15)', '#34d399'),
            'STUDENT': ('rgba(59,130,246,0.15)', '#60a5fa'),
            'ALL': ('rgba(139,92,246,0.15)', '#c084fc'),
        }
        bg, fg = scope_colors.get(scope, ('rgba(148,163,184,0.12)', '#94a3b8'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, scope
        )
    scope_badge.short_description = 'Scope'

    def enabled_toggle_badge(self, obj):
        if getattr(obj, 'is_enabled', False):
            return format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;'
                'font-size:0.75rem;font-weight:700;background:rgba(16,185,129,0.12);color:#34d399;'
                'border:1px solid rgba(16,185,129,0.2);"><span style="width:6px;height:6px;border-radius:50%;background:#34d399;"></span>Enabled</span>'
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;'
            'font-size:0.75rem;font-weight:700;background:rgba(239,68,68,0.12);color:#f87171;'
            'border:1px solid rgba(239,68,68,0.2);"><span style="width:6px;height:6px;border-radius:50%;background:#f87171;"></span>Disabled</span>'
        )
    enabled_toggle_badge.short_description = 'Status'

    def provider_badge(self, obj):
        p = getattr(obj, 'provider', None)
        if not p:
            return format_html('<span style="color:#64748b;">—</span>')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);'
            'color:#a5b4fc;font-weight:600;font-family:monospace;">{}</span>',
            p
        )
    provider_badge.short_description = 'Provider'

    def rate_info(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:0.78rem;">{}/hr · {}/user</span>',
            getattr(obj, 'max_requests_per_hour', 0),
            getattr(obj, 'max_requests_per_user', 0),
        )
    rate_info.short_description = 'Rate Limit'

    @admin.action(description="✅ Enable selected features")
    def enable_features(self, request, queryset):
        count = queryset.update(is_enabled=True)
        self.message_user(request, f"Enabled {count} AI feature(s).")

    @admin.action(description="🚫 Disable selected features")
    def disable_features(self, request, queryset):
        count = queryset.update(is_enabled=False)
        self.message_user(request, f"Disabled {count} AI feature(s).")


# ClassLinkConfig is now registered under the 'classes' app
# as part of the consolidated "Live Classes" feature.
# See classes/admin.py → StreamingPlatformAdmin

# ═══════════════════════════════════════════════════════════════════
# ATTENDANCE RULE — NEW
# ═══════════════════════════════════════════════════════════════════
@admin.register(AttendanceRule)
class AttendanceRuleAdmin(EnhancedModelAdmin):
    list_display = (
        'rule_name', 'applies_to_badge', 'grace_display', 'late_display',
        'min_watch_pct', 'auto_live_badge', 'teacher_self_badge', 'active_badge',
    )
    list_filter = ('is_active', 'applies_to', 'auto_mark_from_live_class', 'teacher_self_attendance_required')
    search_fields = ('rule_name',)
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Rule Identity', {
            'fields': ('tenant', 'rule_name', 'description', 'applies_to', 'is_active'),
        }),
        ('Timing Rules', {
            'fields': ('class_start_grace_minutes', 'late_threshold_minutes', 'absent_threshold_minutes', 'min_watch_percentage'),
        }),
        ('Auto-Attendance Sources', {
            'fields': ('auto_mark_from_live_class', 'auto_mark_from_biometric', 'auto_mark_from_geofence'),
        }),
        ('Notifications', {
            'fields': ('notify_absent_student', 'notify_parent_on_absent', 'notify_admin_below_threshold', 'threshold_alert_percentage'),
            'classes': ('collapse',),
        }),
        ('Teacher Attendance', {
            'fields': ('teacher_self_attendance_required', 'teacher_attendance_auto_from_class'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def applies_to_badge(self, obj):
        scope = getattr(obj, 'applies_to', '')
        colors = {'STUDENT': '#60a5fa', 'TEACHER': '#34d399', 'ALL': '#c084fc'}
        c = colors.get(scope, '#94a3b8')
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{}22;">{}</span>',
            c, c, scope
        )
    applies_to_badge.short_description = 'Applies To'

    def grace_display(self, obj):
        return format_html('<span style="color:#10b981;font-size:0.82rem;">{}min</span>', getattr(obj, 'class_start_grace_minutes', 10))
    grace_display.short_description = 'Grace'

    def late_display(self, obj):
        return format_html('<span style="color:#f59e0b;font-size:0.82rem;">{}min</span>', getattr(obj, 'late_threshold_minutes', 15))
    late_display.short_description = 'Late After'

    def min_watch_pct(self, obj):
        pct = getattr(obj, 'min_watch_percentage', 75)
        return format_html('<span style="color:#94a3b8;font-size:0.82rem;">{}%</span>', pct)
    min_watch_pct.short_description = 'Min Watch'

    def auto_live_badge(self, obj):
        if getattr(obj, 'auto_mark_from_live_class', False):
            return format_html('<span style="color:#10b981;font-weight:600;">⚡ Auto</span>')
        return format_html('<span style="color:#64748b;">Manual</span>')
    auto_live_badge.short_description = 'Live Class'

    def teacher_self_badge(self, obj):
        if getattr(obj, 'teacher_self_attendance_required', False):
            return format_html('<span style="color:#f59e0b;font-weight:600;">Required</span>')
        return format_html('<span style="color:#64748b;">Optional</span>')
    teacher_self_badge.short_description = 'Teacher Self'

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'


# ─── Integration Config ──────────────────────────────────────────────
@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(EnhancedModelAdmin):
    form = IntegrationConfigForm
    list_display = ('name', 'type_badge', 'provider', 'health_badge', 'enabled_badge', 'rate_info', 'updated_at')
    list_filter = ('integration_type', 'health_status', 'is_active')
    search_fields = ('name', 'provider', 'integration_type')
    readonly_fields = ('last_health_check', 'created_at', 'updated_at')
    fieldsets = (
        ('Integration Info', {
            'fields': ('name', 'integration_type', 'provider', 'is_active', 'description')
        }),
        ('Authentication', {
            'fields': ('api_key', 'api_secret', 'api_endpoint', 'oauth_client_id', 'oauth_client_secret', 'oauth_token', 'oauth_refresh_token', 'oauth_token_expiry'),
            'classes': ('collapse',),
        }),
        ('LLM Configuration', {
            'fields': ('model_name', 'max_tokens', 'temperature', 'system_prompt'),
            'classes': ('collapse',),
        }),
        ('YouTube Configuration', {
            'fields': ('channel_id', 'channel_name', 'playlist_ids', 'auto_sync_videos'),
            'classes': ('collapse',),
        }),
        ('Rate Limiting & Budget', {
            'fields': ('max_requests_per_hour', 'max_requests_per_user', 'daily_budget_limit', 'monthly_budget_limit'),
            'classes': ('collapse',),
        }),
        ('Health & Status', {
            'fields': ('health_status', 'last_health_check', 'is_verified', 'created_at', 'updated_at'),
        }),
        ('Advanced', {
            'fields': ('tenant', 'webhook_url', 'config_json', 'usage_stats', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    def type_badge(self, obj):
        colors = {
            'LLM': '#8b5cf6', 'YOUTUBE': '#ef4444', 'ZOOM': '#2563eb',
            'GOOGLE_MEET': '#16a34a', 'WHATSAPP': '#22c55e', 'SMS': '#f59e0b',
            'EMAIL': '#6366f1', 'STORAGE': '#64748b', 'PAYMENT': '#ec4899',
            'ANALYTICS': '#0891b2', 'CUSTOM': '#78716c',
        }
        c = colors.get(obj.integration_type, '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', c, obj.get_integration_type_display())
    type_badge.short_description = 'Type'

    def health_badge(self, obj):
        colors = {'HEALTHY': '#22c55e', 'DEGRADED': '#f59e0b', 'DOWN': '#ef4444', 'UNKNOWN': '#64748b'}
        c = colors.get(obj.health_status, '#64748b')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', c, obj.get_health_status_display())
    health_badge.short_description = 'Health'

    def enabled_badge(self, obj):
        return colored_status(obj.is_active)
    enabled_badge.short_description = 'Enabled'

    def rate_info(self, obj):
        return format_html('<span style="color:#64748b;font-size:11px;">{}/hr</span>', obj.max_requests_per_hour or '∞')
    rate_info.short_description = 'Rate Limit'


# ─── Website Setting ─────────────────────────────────────────────────
@admin.register(WebsiteSetting)
class WebsiteSettingAdmin(EnhancedModelAdmin):
    form = WebsiteSettingForm
    list_display = ('setting_key', 'section_badge', 'value_preview', 'active_badge_ws', 'sort_order', 'updated_at')
    list_filter = ('section', 'is_active')
    search_fields = ('setting_key', 'setting_value', 'section')
    list_editable = ('sort_order',)
    ordering = ('section', 'sort_order')
    fieldsets = (
        ('Setting Info', {
            'fields': ('section', 'setting_key', 'is_active', 'sort_order')
        }),
        ('Value', {
            'fields': ('setting_value', 'setting_json', 'media_url')
        }),
        ('Timestamps', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('updated_at',)

    def section_badge(self, obj):
        colors = {
            'HERO': '#8b5cf6', 'ABOUT': '#2563eb', 'PROGRAMS': '#16a34a',
            'TESTIMONIALS': '#f59e0b', 'FOOTER': '#64748b', 'SEO': '#0891b2',
            'SOCIAL': '#ec4899', 'BRANDING': '#6366f1', 'CONTACT': '#ef4444', 'CUSTOM': '#78716c',
        }
        c = colors.get(obj.section, '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', c, obj.get_section_display())
    section_badge.short_description = 'Section'

    def value_preview(self, obj):
        val = obj.setting_value or ''
        if len(val) > 60:
            val = val[:60] + '…'
        return val or format_html('<span style="color:#94a3b8;">—</span>')
    value_preview.short_description = 'Value'

    def active_badge_ws(self, obj):
        return colored_status(obj.is_active)
    active_badge_ws.short_description = 'Active'


# ─── Report Template ──────────────────────────────────────────────────
@admin.register(ReportTemplate)
class ReportTemplateAdmin(EnhancedModelAdmin):
    form = ReportTemplateForm
    list_display = ('name', 'type_badge_rpt', 'format_badge', 'schedule_badge', 'active_badge_rpt', 'created_by_display', 'updated_at')
    list_filter = ('report_type', 'default_format', 'is_scheduled', 'is_active')
    search_fields = ('name', 'description', 'report_type')
    readonly_fields = ('created_at', 'updated_at')

    class Media:
        js = ('js/report_builder.js',)
    fieldsets = (
        ('Report Info', {
            'fields': ('tenant', 'name', 'description', 'report_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('filters_json', 'columns_json', 'group_by', 'sort_by', 'default_format'),
            'description': 'Set up report filters (like Excel filters), select columns to include, and choose grouping/sorting.',
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'schedule_cron', 'recipients_email'),
            'classes': ('collapse',),
            'description': 'Enable scheduling to automatically generate and email this report on a recurring basis.',
        }),
        ('Meta', {
            'fields': ('created_by_user', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def created_by_display(self, obj):
        if not obj.created_by:
            return format_html('<span style="color:#94a3b8;">—</span>')
        # Try to resolve the UUID to a name
        try:
            from accounts.models import Admin as AdminModel, Teacher
            try:
                admin_user = AdminModel.objects.get(id=obj.created_by)
                name = f"{admin_user.first_name} {admin_user.last_name}".strip() or str(obj.created_by)[:8]
                return format_html('<span style="color:#2563eb;font-weight:500;">{}</span>', name)
            except AdminModel.DoesNotExist:
                pass
            try:
                teacher = Teacher.objects.get(id=obj.created_by)
                name = f"{teacher.first_name} {teacher.last_name}".strip() or str(obj.created_by)[:8]
                return format_html('<span style="color:#8b5cf6;font-weight:500;">{}</span>', name)
            except Teacher.DoesNotExist:
                pass
        except Exception:
            pass
        return format_html('<span style="color:#64748b;">{}</span>', str(obj.created_by)[:8])
    created_by_display.short_description = 'Created By'

    def type_badge_rpt(self, obj):
        colors = {
            'STUDENT': '#8b5cf6', 'TEACHER': '#2563eb', 'ATTENDANCE': '#f59e0b',
            'EXAM': '#ef4444', 'CENTER': '#16a34a', 'FINANCIAL': '#ec4899', 'COMBINED': '#0891b2',
        }
        c = colors.get(obj.report_type, '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', c, obj.get_report_type_display())
    type_badge_rpt.short_description = 'Type'

    def format_badge(self, obj):
        icons = {'CSV': '📄', 'EXCEL': '📊', 'PDF': '📕', 'JSON': '📋'}
        return format_html('{} {}', icons.get(obj.default_format, '📄'), obj.get_default_format_display())
    format_badge.short_description = 'Format'

    def schedule_badge(self, obj):
        if obj.is_scheduled:
            return format_html('<span style="color:#22c55e;font-weight:600;">⏰ {}</span>', obj.schedule_cron or 'Scheduled')
        return format_html('<span style="color:#64748b;">Manual</span>')
    schedule_badge.short_description = 'Schedule'

    def active_badge_rpt(self, obj):
        return colored_status(obj.is_active)
    active_badge_rpt.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# WEBSITE NEWS
# ═══════════════════════════════════════════════════════════════════
@admin.register(WebsiteNews)
class WebsiteNewsAdmin(EnhancedModelAdmin):
    list_display = ('title', 'news_type_badge', 'priority_badge', 'homepage_badge', 'is_published', 'publish_date')
    list_filter = ('news_type', 'priority', 'is_published', 'show_on_homepage', 'show_as_banner')
    search_fields = ('title', 'summary', 'content')
    date_hierarchy = 'publish_date'
    prepopulated_fields = {'slug': ('title',)}
    actions = [export_as_csv, activate_selected, deactivate_selected]
    list_editable = ('is_published',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Article', {
            'fields': ('id', 'tenant', 'title', 'slug', 'news_type', 'priority'),
        }),
        ('Content', {
            'fields': ('summary', 'content', 'featured_image'),
        }),
        ('Display & scheduling', {
            'fields': ('show_on_homepage', 'show_as_banner', 'banner_color', 'is_published', 'publish_date', 'expiry_date'),
        }),
        ('Author & audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def news_type_badge(self, obj):
        colors = {'ANNOUNCEMENT': '#8b5cf6', 'NEWS': '#2563eb', 'EVENT': '#16a34a', 'ALERT': '#ef4444', 'UPDATE': '#f59e0b'}
        c = colors.get(obj.news_type, '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', c, obj.get_news_type_display())
    news_type_badge.short_description = 'Type'

    def priority_badge(self, obj):
        colors = {'LOW': '#94a3b8', 'NORMAL': '#2563eb', 'HIGH': '#f59e0b', 'URGENT': '#ef4444'}
        c = colors.get(obj.priority, '#64748b')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', c, obj.get_priority_display())
    priority_badge.short_description = 'Priority'

    def homepage_badge(self, obj):
        if obj.show_on_homepage:
            return format_html('<span style="color:#22c55e;">🏠 Yes</span>')
        return format_html('<span style="color:#94a3b8;">No</span>')
    homepage_badge.short_description = 'Homepage'

    def published_badge(self, obj):
        return colored_status(obj.is_published)
    published_badge.short_description = 'Published'
    published_badge.admin_order_field = 'is_published'


# ═══════════════════════════════════════════════════════════════════
# TESTIMONIALS
# ═══════════════════════════════════════════════════════════════════
@admin.register(Testimonial)
class TestimonialAdmin(EnhancedModelAdmin):
    list_display = ('author_name', 'type_badge', 'rating_stars', 'achievement', 'is_featured', 'is_published')
    list_filter = ('author_type', 'is_featured', 'is_published', 'rating')
    search_fields = ('author_name', 'content', 'achievement')
    list_editable = ('is_featured', 'is_published')
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Author', {
            'fields': ('id', 'tenant', 'author_name', 'author_type', 'author_designation', 'author_photo', 'batch_year'),
        }),
        ('Content', {
            'fields': ('content', 'rating', 'achievement'),
        }),
        ('Publishing', {
            'fields': ('is_featured', 'is_published', 'sort_order'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def type_badge(self, obj):
        icons = {'STUDENT': '🎓', 'PARENT': '👨‍👩‍👧', 'TEACHER': '👨‍🏫', 'ALUMNI': '🎖️', 'OTHER': '👤'}
        return format_html('{} {}', icons.get(obj.author_type, '👤'), obj.get_author_type_display())
    type_badge.short_description = 'Type'

    def rating_stars(self, obj):
        return format_html('<span style="color:#f59e0b;">{}</span>', '★' * obj.rating + '☆' * (5 - obj.rating))
    rating_stars.short_description = 'Rating'

    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color:#f59e0b;font-weight:600;">⭐ Featured</span>')
        return format_html('<span style="color:#94a3b8;">—</span>')
    featured_badge.short_description = 'Featured'

    def published_badge(self, obj):
        return colored_status(obj.is_published)
    published_badge.short_description = 'Published'


# ═══════════════════════════════════════════════════════════════════
# TICKER ITEMS (Scrolling Stats Bar)
# ═══════════════════════════════════════════════════════════════════
@admin.register(TickerItem)
class TickerItemAdmin(EnhancedModelAdmin):
    list_display = ('label', 'value', 'icon_preview', 'sort_order', 'active_badge_ti')
    list_filter = ('is_active',)
    search_fields = ('label', 'value')
    list_editable = ('sort_order',)
    actions = [export_as_csv, activate_selected, deactivate_selected]
    fieldsets = (
        ('Ticker Item', {
            'fields': ('id', 'tenant', 'label', 'value', 'icon_class'),
        }),
        ('Display', {
            'fields': ('sort_order', 'is_active'),
        }),
    )

    def icon_preview(self, obj):
        return format_html('<i class="{}"></i> {}', obj.icon_class, obj.icon_class)
    icon_preview.short_description = 'Icon'

    def active_badge_ti(self, obj):
        return colored_status(obj.is_active, 'Active', 'Inactive')
    active_badge_ti.short_description = 'Status'


# ═══════════════════════════════════════════════════════════════════
# FOOTER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
@admin.register(FooterConfig)
class FooterConfigAdmin(EnhancedModelAdmin):
    form = FooterConfigForm
    list_display = ('section_title', 'section_badge', 'sort_order', 'active_badge_fc')
    list_filter = ('section', 'is_active')
    search_fields = ('section_title',)
    list_editable = ('sort_order',)
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'updated_at')
    fieldsets = (
        ('Section', {
            'fields': ('id', 'tenant', 'section', 'section_title', 'sort_order', 'is_active'),
        }),
        ('Links & social', {
            'fields': ('links_json', 'social_links_json'),
        }),
        ('Contact & legal', {
            'fields': ('contact_email', 'contact_phone', 'contact_address', 'copyright_text', 'newsletter_text'),
        }),
        ('Audit', {
            'fields': ('updated_at',),
            'classes': ('collapse',),
        }),
    )

    def section_badge(self, obj):
        icons = {'QUICK_LINKS': '🔗', 'RESOURCES': '📚', 'CONTACT': '📞', 'SOCIAL': '📱', 'LEGAL': '⚖️', 'NEWSLETTER': '📧', 'CUSTOM': '⚙️'}
        return format_html('{} {}', icons.get(obj.section, '📄'), obj.get_section_display())
    section_badge.short_description = 'Section'

    def active_badge_fc(self, obj):
        return colored_status(obj.is_active)
    active_badge_fc.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# COMMUNICATION MODELS (Moved from Communication app)
# ═══════════════════════════════════════════════════════════════════

# Unregister from communication app first (if registered)
try:
    admin.site.unregister(Announcement)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(DirectMessage)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(Notification)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(SupportTicket)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(TicketMessage)
except admin.sites.NotRegistered:
    pass


@admin.register(Announcement)
class AnnouncementAdminSC(EnhancedModelAdmin):
    list_display = ('title', 'type_badge_ann', 'target_badge', 'published_badge_ann', 'created_at')
    list_filter = ('announcement_type', 'target_audience', 'is_published')
    search_fields = ('title', 'content')
    date_hierarchy = 'created_at'
    actions = [export_as_csv, activate_selected, deactivate_selected]
    fieldsets = (
        ('Content', {
            'fields': ('id', 'tenant', 'title', 'summary', 'content', 'content_html', 'thumbnail', 'attachments'),
        }),
        ('Type & targeting', {
            'fields': ('announcement_type', 'target_audience', 'target_batches', 'target_user_ids'),
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_pinned', 'published_at', 'expires_at', 'acknowledgement_required', 'is_deleted'),
        }),
        ('Engagement & author', {
            'fields': ('view_count', 'created_by_id', 'created_by_name', 'created_by_type'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def type_badge_ann(self, obj):
        colors = {'GENERAL': '#64748b', 'ACADEMIC': '#2563eb', 'EXAM': '#ef4444', 'EVENT': '#16a34a', 'MAINTENANCE': '#f59e0b', 'URGENT': '#dc2626'}
        c = colors.get(getattr(obj, 'announcement_type', 'GENERAL'), '#64748b')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', c, obj.get_announcement_type_display())
    type_badge_ann.short_description = 'Type'

    def target_badge(self, obj):
        return format_html('<span style="color:#8b5cf6;">{}</span>', obj.get_target_audience_display())
    target_badge.short_description = 'Target'

    def published_badge_ann(self, obj):
        return colored_status(getattr(obj, 'is_published', False))
    published_badge_ann.short_description = 'Published'


@admin.register(DirectMessage)
class DirectMessageAdminSC(EnhancedModelAdmin):
    list_display = ('subject_preview', 'sender_display', 'recipient_display', 'read_badge', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('subject', 'message')
    date_hierarchy = 'created_at'
    actions = [export_as_csv]
    fieldsets = (
        ('Participants', {
            'fields': ('id', 'tenant', 'sender_id', 'sender_type', 'sender_name', 'recipient_id', 'recipient_type', 'recipient_name'),
        }),
        ('Message', {
            'fields': ('subject', 'message', 'attachments'),
        }),
        ('Thread', {
            'fields': ('parent_message', 'thread_id'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_deleted_by_sender', 'is_deleted_by_recipient'),
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def subject_preview(self, obj):
        return format_html('<span style="font-weight:500;">{}</span>', (obj.subject or 'No Subject')[:50])
    subject_preview.short_description = 'Subject'

    def sender_display(self, obj):
        return getattr(obj, 'sender_id', '-')
    sender_display.short_description = 'Sender'

    def recipient_display(self, obj):
        return getattr(obj, 'recipient_id', '-')
    recipient_display.short_description = 'Recipient'

    def read_badge(self, obj):
        if getattr(obj, 'is_read', False):
            return format_html('<span style="color:#22c55e;">✓ Read</span>')
        return format_html('<span style="color:#f59e0b;">● Unread</span>')
    read_badge.short_description = 'Status'


@admin.register(Notification)
class NotificationAdminSC(EnhancedModelAdmin):
    list_display = ('title', 'type_badge_notif', 'user_display', 'read_badge_notif', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('title', 'message')
    date_hierarchy = 'created_at'
    actions = [export_as_csv]
    fieldsets = (
        ('Recipient', {
            'fields': ('id', 'tenant', 'user_id', 'user_type'),
        }),
        ('Content', {
            'fields': ('notification_type', 'channel', 'title', 'message', 'action_url', 'action_data'),
        }),
        ('Source', {
            'fields': ('source_type', 'source_id'),
            'classes': ('collapse',),
        }),
        ('Delivery & read state', {
            'fields': ('is_read', 'read_at', 'is_delivered', 'delivered_at', 'delivery_error', 'expires_at'),
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def type_badge_notif(self, obj):
        return format_html('<span style="background:#e0e7ff;color:#4f46e5;padding:2px 6px;border-radius:4px;font-size:11px;">{}</span>', getattr(obj, 'notification_type', '-'))
    type_badge_notif.short_description = 'Type'

    def user_display(self, obj):
        return getattr(obj, 'user_id', '-')
    user_display.short_description = 'User'

    def read_badge_notif(self, obj):
        if getattr(obj, 'is_read', False):
            return format_html('<span style="color:#22c55e;">✓</span>')
        return format_html('<span style="color:#f59e0b;">●</span>')
    read_badge_notif.short_description = 'Read'


@admin.register(SupportTicket)
class SupportTicketAdminSC(EnhancedModelAdmin):
    list_display = ('ticket_number', 'title', 'status_badge_tk', 'priority_badge_tk', 'submitted_by_name', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'title', 'description')
    date_hierarchy = 'created_at'
    actions = [export_as_csv]
    fieldsets = (
        ('Ticket', {
            'fields': ('id', 'tenant', 'ticket_number', 'title', 'description', 'category', 'priority', 'status'),
        }),
        ('Submitter', {
            'fields': ('submitted_by_id', 'submitted_by_type', 'submitted_by_name', 'submitted_by_email'),
        }),
        ('Assignment', {
            'fields': ('assigned_to_id', 'assigned_to_type', 'assigned_at'),
        }),
        ('SLA & resolution', {
            'fields': ('first_response_at', 'resolved_at', 'resolved_by', 'resolution_note', 'satisfaction_rating', 'sla_breached'),
        }),
        ('Attachments & extensions', {
            'fields': ('attachments', 'ticket_meta', 'ext_ticket_1'),
            'classes': ('collapse',),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge_tk(self, obj):
        colors = {'OPEN': '#22c55e', 'IN_PROGRESS': '#f59e0b', 'RESOLVED': '#2563eb', 'CLOSED': '#64748b'}
        c = colors.get(getattr(obj, 'status', ''), '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', c, getattr(obj, 'status', '-'))
    status_badge_tk.short_description = 'Status'

    def priority_badge_tk(self, obj):
        colors = {'LOW': '#94a3b8', 'MEDIUM': '#2563eb', 'HIGH': '#f59e0b', 'CRITICAL': '#ef4444'}
        c = colors.get(getattr(obj, 'priority', ''), '#64748b')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', c, getattr(obj, 'priority', '-'))
    priority_badge_tk.short_description = 'Priority'


@admin.register(TicketMessage)
class TicketMessageAdminSC(EnhancedModelAdmin):
    list_display = ('ticket_display', 'message_preview', 'sender_display_tm', 'is_internal_note', 'created_at')
    list_filter = ('is_internal_note',)
    search_fields = ('message',)
    date_hierarchy = 'created_at'
    actions = [export_as_csv]
    fieldsets = (
        ('Message', {
            'fields': ('id', 'tenant', 'ticket', 'sender_id', 'sender_type', 'sender_name', 'message', 'attachments'),
        }),
        ('Internal', {
            'fields': ('is_internal_note',),
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def ticket_display(self, obj):
        return getattr(obj.ticket, 'ticket_number', '-') if hasattr(obj, 'ticket') else '-'
    ticket_display.short_description = 'Ticket'

    def message_preview(self, obj):
        return (obj.message or '')[:60] + '...' if len(obj.message or '') > 60 else (obj.message or '-')
    message_preview.short_description = 'Message'

    def sender_display_tm(self, obj):
        return getattr(obj, 'sender_id', '-')
    sender_display_tm.short_description = 'Sender'


# ═══════════════════════════════════════════════════════════════════
# UNREGISTER ITEMS THAT ARE NOW PART OF WEBSITE SETTINGS
# ═══════════════════════════════════════════════════════════════════
# FounderInfo is now managed through Website Settings → Founders & Team section
try:
    admin.site.unregister(FounderInfo)
except admin.sites.NotRegistered:
    pass
