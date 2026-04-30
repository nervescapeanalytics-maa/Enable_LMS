from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from attendance.models import Attendance, AttendanceCorrectionRequest, AttendanceSummary
from core.admin_utils import (
    EnhancedModelAdmin, ImportExportMixin, export_as_csv,
    export_as_json, colored_status, activate_selected, deactivate_selected,
)


# ═══════════════════════════════════════════════════════════════════
# CUSTOM ACTIONS
# ═══════════════════════════════════════════════════════════════════
@admin.action(description="✅ Mark selected as Present")
def mark_present(modeladmin, request, queryset):
    count = queryset.update(status='PRESENT')
    modeladmin.message_user(request, f"Marked {count} record(s) as Present.")


@admin.action(description="❌ Mark selected as Absent")
def mark_absent(modeladmin, request, queryset):
    count = queryset.update(status='ABSENT')
    modeladmin.message_user(request, f"Marked {count} record(s) as Absent.")


@admin.action(description="⏰ Mark selected as Late")
def mark_late(modeladmin, request, queryset):
    count = queryset.update(status='LATE')
    modeladmin.message_user(request, f"Marked {count} record(s) as Late.")


@admin.action(description="🏖 Mark selected as Leave")
def mark_leave(modeladmin, request, queryset):
    count = queryset.update(status='LEAVE')
    modeladmin.message_user(request, f"Marked {count} record(s) as Leave.")


# ═══════════════════════════════════════════════════════════════════
# ATTENDANCE — Master View
# ═══════════════════════════════════════════════════════════════════
@admin.register(Attendance)
class AttendanceAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = (
        'user_type_badge', 'user_id_short', 'attendance_date',
        'status_colored', 'source_badge', 'batch',
        'check_in_display', 'check_out_display',
        'watch_display', 'corrected_badge',
    )
    list_filter = ('user_type', 'status', 'source', 'is_corrected', 'attendance_date')
    search_fields = ('user_id',)
    date_hierarchy = 'attendance_date'
    actions = [
        export_as_csv, export_as_json,
        mark_present, mark_absent, mark_late, mark_leave,
    ]
    list_per_page = 50
    readonly_fields = ('id', 'marked_at')

    # ── Summary cards on the changelist (today's KPIs) ─────────────────
    def changelist_view(self, request, extra_context=None):
        from django.utils import timezone as tz
        today = tz.localdate()
        qs = Attendance.objects.filter(attendance_date=today)
        agg = qs.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            leave=Count('id', filter=Q(status='LEAVE')),
        )
        total = agg['total'] or 0
        pct = round((agg['present'] or 0) * 100.0 / total, 1) if total else 0.0
        cards = [
            {'title': "Today's %", 'value': f'{pct}%', 'icon': 'fa-percent', 'color': '#10b981',
             'sub': f"{agg['present']}/{total} present"},
            {'title': 'Present', 'value': agg['present'] or 0, 'icon': 'fa-check-circle', 'color': '#3b82f6',
             'sub': f'as of {today:%b %d}'},
            {'title': 'Absent',  'value': agg['absent']  or 0, 'icon': 'fa-times-circle', 'color': '#ef4444',
             'sub': f'as of {today:%b %d}'},
            {'title': 'Late',    'value': agg['late']    or 0, 'icon': 'fa-clock',        'color': '#f59e0b',
             'sub': f"+{agg['leave'] or 0} on leave"},
        ]
        extra_context = extra_context or {}
        extra_context['attendance_summary_cards'] = cards
        return super().changelist_view(request, extra_context=extra_context)

    # ── Auto-fill batch / month / year on save ─────────────────────────
    def save_model(self, request, obj, form, change):
        # Derive month / year from attendance_date when missing
        if obj.attendance_date:
            if not obj.month:
                obj.month = obj.attendance_date.month
            if not obj.year:
                obj.year = obj.attendance_date.year
        # For teacher attendance, auto-fill batch from the teacher's
        # primary teaching batch when the admin leaves it blank.
        if (obj.user_type == 'TEACHER') and (not obj.batch_id) and obj.user_id:
            try:
                from academics.models import Batch
                primary = (
                    Batch.objects
                    .filter(teachers__id=obj.user_id, status='ACTIVE')
                    .order_by('-created_at')
                    .first()
                ) or (
                    Batch.objects.filter(teachers__id=obj.user_id).first()
                )
                if primary:
                    obj.batch = primary
            except Exception:
                pass
        super().save_model(request, obj, form, change)

    fieldsets = (
        ('Attendance Record', {
            'fields': ('id', 'tenant', 'user_type', 'user_id', 'batch', 'attendance_date', 'month', 'year', 'academic_session'),
        }),
        ('Status', {
            'fields': ('status', 'check_in_time', 'check_out_time', 'source', 'remarks'),
        }),
        ('Live Class Auto-Capture', {
            'fields': ('live_class', 'watch_duration_seconds', 'watch_percentage'),
            'classes': ('collapse',),
        }),
        ('Audit Trail', {
            'fields': ('marked_by', 'marked_by_type', 'marked_at'),
            'classes': ('collapse',),
        }),
        ('Correction History', {
            'fields': ('is_corrected', 'original_status', 'corrected_by', 'corrected_at', 'correction_reason'),
            'classes': ('collapse',),
        }),
        ('Extension Fields', {
            'fields': ('attendance_meta', 'source_reference_id', 'ext_att_1', 'ext_att_2'),
            'classes': ('collapse',),
        }),
    )

    def user_type_badge(self, obj):
        ut = getattr(obj, 'user_type', '')
        if ut == 'STUDENT':
            return format_html(
                '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;'
                'color:#60a5fa;background:rgba(59,130,246,0.12);">'
                '<i class="fas fa-user-graduate" style="margin-right:4px;"></i>Student</span>'
            )
        elif ut == 'TEACHER':
            return format_html(
                '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;'
                'color:#34d399;background:rgba(16,185,129,0.12);">'
                '<i class="fas fa-chalkboard-teacher" style="margin-right:4px;"></i>Teacher</span>'
            )
        return format_html('<span style="color:#94a3b8;">{}</span>', ut)
    user_type_badge.short_description = 'Type'
    user_type_badge.admin_order_field = 'user_type'

    def user_id_short(self, obj):
        """Resolve user_id UUID to actual student/teacher name."""
        uid = getattr(obj, 'user_id', None)
        if not uid:
            return '-'
        uid_str = str(uid)
        user_type = getattr(obj, 'user_type', '')
        name = None
        try:
            if user_type == 'STUDENT':
                from accounts.models import Student
                stu = Student.objects.filter(id=uid).values_list('first_name', 'last_name').first()
                if stu:
                    name = f"{stu[0]} {stu[1]}".strip()
            elif user_type == 'TEACHER':
                from accounts.models import Teacher
                tch = Teacher.objects.filter(id=uid).values_list('first_name', 'last_name').first()
                if tch:
                    name = f"{tch[0]} {tch[1]}".strip()
        except Exception:
            pass
        if name:
            return format_html(
                '<span style="font-size:0.82rem;color:#1e293b;font-weight:600;" title="{}">{}</span>',
                uid_str, name
            )
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#475569;" title="{}">{}</span>',
            uid_str, uid_str[:8]
        )
    user_id_short.short_description = 'User'

    def status_colored(self, obj):
        s = getattr(obj, 'status', '')
        colors = {
            'PRESENT': ('#10b981', 'rgba(16,185,129,0.12)'),
            'ABSENT': ('#ef4444', 'rgba(239,68,68,0.12)'),
            'LATE': ('#f59e0b', 'rgba(245,158,11,0.12)'),
            'HALF_DAY': ('#3b82f6', 'rgba(59,130,246,0.12)'),
            'LEAVE': ('#8b5cf6', 'rgba(139,92,246,0.12)'),
            'HOLIDAY': ('#22d3ee', 'rgba(34,211,238,0.12)'),
            'EXCUSED': ('#a855f7', 'rgba(168,85,247,0.12)'),
        }
        fg, bg = colors.get(s, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        icon_map = {
            'PRESENT': '✔', 'ABSENT': '✖', 'LATE': '⏰',
            'HALF_DAY': '½', 'LEAVE': '🏖', 'HOLIDAY': '🎉', 'EXCUSED': '✓',
        }
        icon = icon_map.get(s, '')
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:6px;'
            'font-size:0.72rem;font-weight:700;color:{};background:{};border:1px solid {}22;">{} {}</span>',
            fg, bg, fg, icon, s.replace('_', ' ').title() if s else '-'
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'

    def source_badge(self, obj):
        s = getattr(obj, 'source', 'MANUAL')
        source_styles = {
            'MANUAL': ('#94a3b8', 'rgba(148,163,184,0.12)', 'fas fa-hand-pointer'),
            'LIVE_CLASS': ('#ef4444', 'rgba(239,68,68,0.12)', 'fas fa-video'),
            'BIOMETRIC': ('#10b981', 'rgba(16,185,129,0.12)', 'fas fa-fingerprint'),
            'QR_CODE': ('#8b5cf6', 'rgba(139,92,246,0.12)', 'fas fa-qrcode'),
            'GEOFENCE': ('#f59e0b', 'rgba(245,158,11,0.12)', 'fas fa-map-marker-alt'),
            'SYSTEM': ('#3b82f6', 'rgba(59,130,246,0.12)', 'fas fa-robot'),
        }
        fg, bg, icon = source_styles.get(s, ('#94a3b8', 'rgba(148,163,184,0.12)', 'fas fa-circle'))
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:5px;'
            'font-size:0.72rem;font-weight:600;color:{};background:{};">'
            '<i class="{}" style="font-size:0.65rem;"></i> {}</span>',
            fg, bg, icon, s.replace('_', ' ').title()
        )
    source_badge.short_description = 'Source'

    def check_in_display(self, obj):
        t = getattr(obj, 'check_in_time', None)
        if t:
            return format_html('<span style="color:#10b981;font-size:0.82rem;font-family:monospace;">{}</span>', t.strftime('%H:%M'))
        return format_html('<span style="color:#475569;">—</span>')
    check_in_display.short_description = 'In'

    def check_out_display(self, obj):
        t = getattr(obj, 'check_out_time', None)
        if t:
            return format_html('<span style="color:#ef4444;font-size:0.82rem;font-family:monospace;">{}</span>', t.strftime('%H:%M'))
        return format_html('<span style="color:#475569;">—</span>')
    check_out_display.short_description = 'Out'

    def watch_display(self, obj):
        pct = getattr(obj, 'watch_percentage', None)
        dur = getattr(obj, 'watch_duration_seconds', None)
        if pct is not None:
            color = '#10b981' if pct >= 75 else '#f59e0b' if pct >= 50 else '#ef4444'
            dur_str = f"{dur // 60}m" if dur else ''
            return format_html(
                '<div style="display:flex;align-items:center;gap:6px;">'
                '<div style="width:40px;height:5px;background:rgba(99,102,241,0.1);border-radius:3px;overflow:hidden;">'
                '<div style="width:{}%;height:100%;background:{};border-radius:3px;"></div></div>'
                '<span style="font-size:0.75rem;color:{};font-weight:600;">{}%</span>'
                '<span style="font-size:0.7rem;color:#64748b;">{}</span></div>',
                min(int(pct), 100), color, color, pct, dur_str
            )
        return format_html('<span style="color:#475569;">—</span>')
    watch_display.short_description = 'Watch'

    def corrected_badge(self, obj):
        if getattr(obj, 'is_corrected', False):
            return format_html(
                '<span style="color:#f59e0b;font-weight:600;" title="Original: {}">'
                '<i class="fas fa-edit"></i> Corrected</span>',
                getattr(obj, 'original_status', '')
            )
        return ''
    corrected_badge.short_description = 'Corrected'


# ═══════════════════════════════════════════════════════════════════
# CORRECTION REQUEST
# ═══════════════════════════════════════════════════════════════════
@admin.action(description="✅ Approve selected corrections")
def approve_corrections(modeladmin, request, queryset):
    for correction in queryset.filter(status='PENDING'):
        attendance = correction.attendance
        attendance.original_status = attendance.status
        attendance.status = correction.requested_status
        attendance.is_corrected = True
        attendance.corrected_by = request.user.pk if hasattr(request.user, 'pk') else None
        from django.utils import timezone as tz
        attendance.corrected_at = tz.now()
        attendance.correction_reason = correction.reason
        attendance.save()
        correction.status = 'APPROVED'
        correction.reviewed_at = tz.now()
        correction.save()
    modeladmin.message_user(request, f"Approved {queryset.count()} correction(s).")


@admin.action(description="❌ Reject selected corrections")
def reject_corrections(modeladmin, request, queryset):
    from django.utils import timezone as tz
    count = queryset.filter(status='PENDING').update(status='REJECTED', reviewed_at=tz.now())
    modeladmin.message_user(request, f"Rejected {count} correction(s).")


@admin.register(AttendanceCorrectionRequest)
class AttendanceCorrectionRequestAdmin(EnhancedModelAdmin):
    list_display = ('attendance', 'requested_status_badge', 'reason_short', 'request_status_badge', 'created_display')
    list_filter = ('status', 'requested_status')
    search_fields = ('reason',)
    actions = [export_as_csv, approve_corrections, reject_corrections]
    readonly_fields = ('id', 'created_at', 'reviewed_at')
    fieldsets = (
        ('Request', {
            'fields': ('id', 'tenant', 'attendance', 'requested_by', 'requested_by_type', 'requested_status', 'reason', 'supporting_document'),
        }),
        ('Review', {
            'fields': ('status', 'review_comment', 'reviewed_by', 'reviewed_at'),
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def requested_status_badge(self, obj):
        s = getattr(obj, 'requested_status', '')
        colors = {'PRESENT': '#10b981', 'ABSENT': '#ef4444', 'LATE': '#f59e0b', 'HALF_DAY': '#3b82f6', 'LEAVE': '#8b5cf6'}
        c = colors.get(s, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;color:{};background:{}22;font-weight:600;">{}</span>',
            c, c, s.replace('_', ' ').title() if s else '-'
        )
    requested_status_badge.short_description = 'Requested'

    def reason_short(self, obj):
        reason = getattr(obj, 'reason', '') or ''
        return reason[:60] + '...' if len(reason) > 60 else reason
    reason_short.short_description = 'Reason'

    def request_status_badge(self, obj):
        s = getattr(obj, 'status', '')
        colors = {'PENDING': ('#f59e0b', 'rgba(245,158,11,0.12)'), 'APPROVED': ('#10b981', 'rgba(16,185,129,0.12)'), 'REJECTED': ('#ef4444', 'rgba(239,68,68,0.12)')}
        fg, bg = colors.get(s, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, s.title() if s else '-'
        )
    request_status_badge.short_description = 'Status'


# ═══════════════════════════════════════════════════════════════════
# ATTENDANCE SUMMARY
# ═══════════════════════════════════════════════════════════════════
@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(EnhancedModelAdmin):
    list_display = (
        'user_type_badge', 'user_id_short', 'month_year',
        'working_days', 'present_badge', 'absent_badge',
        'late_badge', 'leave_badge', 'percentage_bar',
    )
    list_filter = ('user_type', 'year', 'month')
    search_fields = ('user_id',)
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'last_calculated_at')
    fieldsets = (
        ('Scope', {
            'fields': ('id', 'tenant', 'user_id', 'user_type', 'batch', 'academic_session', 'month', 'year'),
        }),
        ('Counts', {
            'fields': (
                'total_working_days', 'present_days', 'absent_days', 'late_days',
                'half_days', 'leave_days', 'holiday_days', 'attendance_percentage',
            ),
        }),
        ('Calculation', {
            'fields': ('last_calculated_at',),
            'classes': ('collapse',),
        }),
    )

    def user_type_badge(self, obj):
        ut = getattr(obj, 'user_type', '')
        if ut == 'STUDENT':
            return format_html('<span style="color:#60a5fa;font-weight:600;">Student</span>')
        return format_html('<span style="color:#34d399;font-weight:600;">Teacher</span>')
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        uid = str(getattr(obj, 'user_id', ''))
        return format_html('<span style="font-family:monospace;font-size:0.78rem;color:#475569;">{}</span>', uid[:8])
    user_id_short.short_description = 'User'

    def month_year(self, obj):
        import calendar
        m = getattr(obj, 'month', 1)
        y = getattr(obj, 'year', 2026)
        return format_html('<span style="color:#1e293b;font-weight:600;">{} {}</span>', calendar.month_abbr[m], y)
    month_year.short_description = 'Period'

    def working_days(self, obj):
        return format_html('<span style="color:#475569;">{}</span>', getattr(obj, 'total_working_days', 0))
    working_days.short_description = 'Working'

    def present_badge(self, obj):
        return format_html('<span style="color:#10b981;font-weight:700;">{}</span>', getattr(obj, 'present_days', 0))
    present_badge.short_description = 'P'

    def absent_badge(self, obj):
        return format_html('<span style="color:#ef4444;font-weight:700;">{}</span>', getattr(obj, 'absent_days', 0))
    absent_badge.short_description = 'A'

    def late_badge(self, obj):
        return format_html('<span style="color:#f59e0b;font-weight:700;">{}</span>', getattr(obj, 'late_days', 0))
    late_badge.short_description = 'L'

    def leave_badge(self, obj):
        return format_html('<span style="color:#8b5cf6;font-weight:700;">{}</span>', getattr(obj, 'leave_days', 0))
    leave_badge.short_description = 'Lv'

    def percentage_bar(self, obj):
        pct = getattr(obj, 'attendance_percentage', None) or 0
        color = '#10b981' if pct >= 75 else '#f59e0b' if pct >= 50 else '#ef4444'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="flex:1;height:6px;background:rgba(99,102,241,0.1);border-radius:3px;overflow:hidden;max-width:80px;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:3px;"></div></div>'
            '<span style="font-size:0.82rem;color:{};font-weight:700;">{}%</span></div>',
            min(int(pct), 100), color, color, pct
        )
    percentage_bar.short_description = 'Attendance %'
