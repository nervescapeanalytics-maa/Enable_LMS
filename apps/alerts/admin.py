from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from alerts.models import AlertRule, AlertLog
from core.admin_utils import EnhancedModelAdmin, export_as_csv, export_as_json


@admin.register(AlertRule)
class AlertRuleAdmin(EnhancedModelAdmin):
    list_display = ('name', 'category_badge', 'rule_type_display', 'severity_badge',
                    'threshold', 'time_window_minutes', 'notify_method', 'active_badge')
    list_filter = ('category', 'severity', 'is_active', 'notify_method')
    search_fields = ('name', 'description')
    actions = [export_as_csv, export_as_json, 'activate_rules', 'deactivate_rules']
    list_per_page = 25

    fieldsets = (
        (None, {
            'fields': ('tenant', 'name', 'description'),
        }),
        ('Rule Configuration', {
            'fields': ('category', 'rule_type', 'threshold', 'time_window_minutes', 'severity'),
        }),
        ('Notifications', {
            'fields': ('notify_method', 'notify_emails'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    def category_badge(self, obj):
        colors = {
            'SESSION_TRACKING': '#6366f1',
            'ATTENDANCE': '#f59e0b',
            'LIVE_CLASSES': '#ef4444',
            'ASSESSMENTS': '#3b82f6',
            'SECURITY': '#dc2626',
            'SYSTEM': '#64748b',
        }
        c = colors.get(obj.category, '#64748b')
        return format_html(
            '<span style="padding:3px 10px;border-radius:5px;font-size:0.72rem;'
            'background:{}18;color:{};font-weight:600;">{}</span>',
            c, c, obj.get_category_display()
        )
    category_badge.short_description = 'Category'

    def rule_type_display(self, obj):
        return obj.get_rule_type_display()
    rule_type_display.short_description = 'Rule Type'

    def severity_badge(self, obj):
        colors = {'INFO': '#3b82f6', 'WARNING': '#f59e0b', 'CRITICAL': '#ef4444'}
        c = colors.get(obj.severity, '#64748b')
        icons = {'INFO': 'fa-info-circle', 'WARNING': 'fa-exclamation-triangle', 'CRITICAL': 'fa-exclamation-circle'}
        icon = icons.get(obj.severity, 'fa-bell')
        return format_html(
            '<span style="padding:3px 10px;border-radius:5px;font-size:0.72rem;'
            'background:{}18;color:{};font-weight:600;">'
            '<i class="fas {}"></i> {}</span>',
            c, c, icon, obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'

    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="padding:3px 10px;border-radius:5px;font-size:0.72rem;'
                'background:rgba(16,185,129,0.15);color:#15803d;font-weight:600;">'
                '<i class="fas fa-check-circle"></i> Active</span>')
        return format_html(
            '<span style="padding:3px 10px;border-radius:5px;font-size:0.72rem;'
            'background:rgba(239,68,68,0.15);color:#dc2626;font-weight:600;">'
            '<i class="fas fa-times-circle"></i> Inactive</span>')
    active_badge.short_description = 'Status'

    @admin.action(description='✅ Activate selected rules')
    def activate_rules(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='🚫 Deactivate selected rules')
    def deactivate_rules(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(AlertLog)
class AlertLogAdmin(EnhancedModelAdmin):
    list_display = ('rule_name', 'severity_badge', 'message_short', 'triggered_at',
                    'acknowledged_badge', 'email_badge')
    list_filter = ('severity', 'is_acknowledged', 'is_email_sent', 'rule__category')
    search_fields = ('message', 'rule__name')
    date_hierarchy = 'triggered_at'
    actions = [export_as_csv, export_as_json, 'acknowledge_selected']
    list_per_page = 50
    readonly_fields = ('id', 'triggered_at')

    # Hide the Tools (Command Palette) button entirely on Alert Logs.
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['enf_disable_tools'] = True
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'rule'),
        }),
        ('Alert Details', {
            'fields': ('severity', 'message', 'details', 'triggered_at'),
        }),
        ('Acknowledgement', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at'),
        }),
        ('Notification', {
            'fields': ('is_email_sent',),
        }),
    )

    def rule_name(self, obj):
        return obj.rule.name
    rule_name.short_description = 'Rule'
    rule_name.admin_order_field = 'rule__name'

    def severity_badge(self, obj):
        colors = {'INFO': '#3b82f6', 'WARNING': '#f59e0b', 'CRITICAL': '#ef4444'}
        c = colors.get(obj.severity, '#64748b')
        return format_html(
            '<span style="padding:3px 10px;border-radius:5px;font-size:0.72rem;'
            'background:{}18;color:{};font-weight:600;">{}</span>',
            c, c, obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'

    def message_short(self, obj):
        msg = obj.message or ''
        short = msg[:80] + '…' if len(msg) > 80 else msg
        return format_html('<span title="{}">{}</span>', msg, short)
    message_short.short_description = 'Message'

    def acknowledged_badge(self, obj):
        if obj.is_acknowledged:
            return format_html(
                '<span style="color:#15803d;font-weight:600;">'
                '<i class="fas fa-check"></i> {}</span>',
                obj.acknowledged_by or 'Yes')
        return format_html('<span style="color:#f59e0b;"><i class="fas fa-clock"></i> Pending</span>')
    acknowledged_badge.short_description = 'Acknowledged'

    def email_badge(self, obj):
        if obj.is_email_sent:
            return format_html('<span style="color:#15803d;"><i class="fas fa-envelope-open"></i> Sent</span>')
        return format_html('<span style="color:#94a3b8;">-</span>')
    email_badge.short_description = 'Email'

    @admin.action(description='✅ Acknowledge selected alerts')
    def acknowledge_selected(self, request, queryset):
        queryset.filter(is_acknowledged=False).update(
            is_acknowledged=True,
            acknowledged_by=str(request.user),
            acknowledged_at=timezone.now(),
        )


# ═══════════════════════════════════════════════════════════════════
# MONITORING DASHBOARD — Frontend / Backend / DB / Non-tech KPIs
# ═══════════════════════════════════════════════════════════════════
from django.shortcuts import render  # noqa: E402
from django.urls import path as _path  # noqa: E402
from django.db import connection as _db  # noqa: E402
from datetime import timedelta as _td  # noqa: E402


def _safe_count(qs):
    try:
        return qs.count()
    except Exception:
        return 0


def _safe_aggregate(qs, **agg):
    try:
        return qs.aggregate(**agg)
    except Exception:
        return {k: 0 for k in agg}


from django.views.decorators.clickjacking import xframe_options_sameorigin


@xframe_options_sameorigin
def monitoring_dashboard_view(request):
    """KPI dashboard covering frontend, backend, DB, alerts and non-technical metrics."""
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    now = timezone.now()
    last_1h = now - _td(hours=1)
    last_24h = now - _td(hours=24)
    last_7d = now - _td(days=7)

    # ─── Database row counts (non-tech business KPIs) ───
    counts = {}
    try:
        from accounts.models import Student, Teacher, LoginAttemptLog, AccessLog, AuditEntry
        counts['students_total']      = _safe_count(Student.objects.all())
        counts['students_active']     = _safe_count(Student.objects.filter(status='ACTIVE'))
        counts['students_inactive']   = counts['students_total'] - counts['students_active']
        counts['teachers_total']      = _safe_count(Teacher.objects.all())
        counts['teachers_active']     = _safe_count(Teacher.objects.filter(status='ACTIVE'))
        counts['logins_24h']          = _safe_count(LoginAttemptLog.objects.filter(timestamp__gte=last_24h))
        counts['login_fail_24h']      = _safe_count(LoginAttemptLog.objects.filter(timestamp__gte=last_24h, success=False))
        counts['login_success_24h']   = counts['logins_24h'] - counts['login_fail_24h']
        counts['access_logs_1h']      = _safe_count(AccessLog.objects.filter(timestamp__gte=last_1h))
        counts['access_logs_24h']     = _safe_count(AccessLog.objects.filter(timestamp__gte=last_24h))
        counts['access_denied_24h']   = _safe_count(AccessLog.objects.filter(timestamp__gte=last_24h, decision='DENY'))
        counts['audit_24h']           = _safe_count(AuditEntry.objects.filter(timestamp__gte=last_24h))
    except Exception:
        pass

    try:
        from classes.models import Class as _Class, Batch as _Batch
        counts['classes_total']       = _safe_count(_Class.objects.all())
        counts['batches_total']       = _safe_count(_Batch.objects.all())
    except Exception:
        counts.setdefault('classes_total', 0)
        counts.setdefault('batches_total', 0)

    try:
        from attendance.models import AttendanceRecord
        counts['attendance_today']    = _safe_count(AttendanceRecord.objects.filter(date=now.date()))
        counts['attendance_present']  = _safe_count(AttendanceRecord.objects.filter(date=now.date(), status='PRESENT'))
        if counts['attendance_today']:
            counts['attendance_pct']  = round(counts['attendance_present'] * 100.0 / counts['attendance_today'], 1)
        else:
            counts['attendance_pct']  = 0
    except Exception:
        counts['attendance_today'] = counts['attendance_present'] = counts['attendance_pct'] = 0

    try:
        from assessments.models import Test
        counts['tests_total']         = _safe_count(Test.objects.all())
    except Exception:
        counts['tests_total'] = 0

    # ─── Alerts ───
    alerts = {
        'rules_total':        _safe_count(AlertRule.objects.all()),
        'rules_active':       _safe_count(AlertRule.objects.filter(is_active=True)),
        'logs_24h':           _safe_count(AlertLog.objects.filter(triggered_at__gte=last_24h)),
        'critical_24h':       _safe_count(AlertLog.objects.filter(triggered_at__gte=last_24h, severity='CRITICAL')),
        'unacknowledged':     _safe_count(AlertLog.objects.filter(is_acknowledged=False)),
        'recent':             list(AlertLog.objects.select_related('rule').order_by('-triggered_at')[:10]),
    }

    # ─── Database health (server-level, PostgreSQL specific where possible) ───
    db_stats = {}
    try:
        with _db.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            db_stats['active_connections'] = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM pg_stat_activity")
            db_stats['total_connections'] = cur.fetchone()[0]
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_stats['db_size'] = cur.fetchone()[0]
            # Top 5 largest tables
            cur.execute("""
                SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                       n_live_tup AS rows
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 8
            """)
            db_stats['top_tables'] = [
                {'name': r[0], 'size': r[1], 'rows': r[2]} for r in cur.fetchall()
            ]
    except Exception as e:
        db_stats['error'] = str(e)

    # ─── Backend / Django / Cache health ───
    backend = {}
    try:
        from django.core.cache import cache
        cache.set('_monitoring_ping', '1', 5)
        backend['cache'] = 'OK' if cache.get('_monitoring_ping') == '1' else 'DOWN'
    except Exception as e:
        backend['cache'] = f'ERROR: {e}'

    try:
        # Celery / broker
        from kombu import Connection
        from django.conf import settings as _settings
        broker = getattr(_settings, 'CELERY_BROKER_URL', None) or 'redis://redis:6379/0'
        with Connection(broker, connect_timeout=2) as _c:
            _c.connect()
        backend['celery_broker'] = 'OK'
    except Exception as e:
        backend['celery_broker'] = f'DOWN ({e})'

    try:
        # Number of registered Django models (rough surface area)
        from django.apps import apps as _apps2
        backend['models_registered'] = len(_apps2.get_models())
    except Exception:
        pass

    # ─── Frontend usage signals ───
    frontend = {}
    try:
        from sessions_tracking.models import UserSession
        frontend['sessions_active']   = _safe_count(UserSession.objects.filter(ended_at__isnull=True))
        frontend['sessions_24h']      = _safe_count(UserSession.objects.filter(started_at__gte=last_24h))
    except Exception:
        frontend['sessions_active'] = frontend['sessions_24h'] = 'n/a'

    context = {
        'title': 'Monitoring & Alerting Dashboard',
        'now': now,
        'counts': counts,
        'alerts': alerts,
        'db_stats': db_stats,
        'backend': backend,
        'frontend': frontend,
        'has_permission': True,
        'opts': AlertLog._meta,
        **admin.site.each_context(request),
    }
    return render(request, 'admin/alerts/monitoring_dashboard.html', context)


# ─── Hook a custom URL into the Alerts app admin (via AlertLog get_urls) ───
_orig_get_urls = AlertLogAdmin.get_urls
def _alertlog_get_urls(self):
    urls = _orig_get_urls(self)
    custom = [
        _path(
            'monitoring/',
            self.admin_site.admin_view(monitoring_dashboard_view),
            name='alerts_alertlog_monitoring',
        ),
    ]
    return custom + urls
AlertLogAdmin.get_urls = _alertlog_get_urls
AlertLogAdmin.change_list_template = 'admin/alerts/alertlog_change_list.html'


# Mirror the dashboard onto AlertRule, plus an "Evaluate now" trigger.
def _evaluate_now_view(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    from alerts.tasks import evaluate_alert_rules
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    try:
        triggered = evaluate_alert_rules()
        messages.success(request, f'Alert evaluation completed — {triggered} alert(s) triggered.')
    except Exception as exc:
        messages.error(request, f'Evaluation failed: {exc}')
    return redirect('..')


_orig_rule_get_urls = AlertRuleAdmin.get_urls
def _alertrule_get_urls(self):
    urls = _orig_rule_get_urls(self)
    custom = [
        _path(
            'monitoring/',
            self.admin_site.admin_view(monitoring_dashboard_view),
            name='alerts_alertrule_monitoring',
        ),
        _path(
            'evaluate-now/',
            self.admin_site.admin_view(_evaluate_now_view),
            name='alerts_alertrule_evaluate_now',
        ),
    ]
    return custom + urls
AlertRuleAdmin.get_urls = _alertrule_get_urls
AlertRuleAdmin.change_list_template = 'admin/alerts/alertrule_change_list.html'
