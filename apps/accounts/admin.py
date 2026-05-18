from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils import timezone
from accounts.models import (
    # 1. User Lifecycle
    Student, Teacher, Admin as AdminUser, Parent,
    ParentStudent, UserRoleAssignment,
    # 2. Permissions & Roles
    Role, Permission, RolePermission, StaffRole,
    # 3. Groups & Assignment
    UserGroup, GroupMembership, GroupRoleAssignment,
    # 4. Account Protection
    SecurityPolicy, LoginAttemptLog, TrustedDevice,
    # 5. Audit & Monitoring
    AccessLog, AuditEntry, BehaviorEvent,
    # 6. Compliance
    ComplianceRule, ConsentRecord, DataAccessRequest, RetentionPolicy,
)
from core.admin_utils import (
    EnhancedModelAdmin, ImportExportMixin, export_as_csv,
    export_as_json, activate_selected, deactivate_selected,
    suspend_selected, colored_status,
)


# ═══════════════════════════════════════════════════════════════════
# IDENTITY & USER MANAGEMENT — Admin Configuration
# ═══════════════════════════════════════════════════════════════════
# Sub-features:
#   1. User Lifecycle        — Students, Teachers, Admins, Parents, Role Assignments
#   2. Permissions & Roles   — Permissions, Roles (RBAC), Staff Roles
#   3. Groups & Assignment   — User Groups, Memberships, Group Role Assignments
#   4. Account Protection    — Security Policies, Login Attempts, Trusted Devices
#   5. Audit & Monitoring    — Access Logs, Audit Log Entries, Behavior Events
#   6. Compliance            — Compliance Rules, Consent Records, DSARs, Retention
# ═══════════════════════════════════════════════════════════════════
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# ═══════════════════════════════════════════════════════════════════
# 1. USER LIFECYCLE — Students
# ═══════════════════════════════════════════════════════════════════
@admin.register(Student)
class StudentAdmin(ImportExportMixin, EnhancedModelAdmin):
    change_list_template = 'admin/accounts/student/change_list.html'

    # Import header → field name aliases for friendlier CSV/Excel imports.
    import_field_aliases = {
        'name': 'first_name',
        'full name': 'first_name',
        'first name': 'first_name',
        'last name': 'last_name',
        'surname': 'last_name',
        'mobile': 'phone',
        'mobile number': 'phone',
        'phone number': 'phone',
        'email id': 'email',
        'email address': 'email',
        'school': 'school_name',
        'school name': 'school_name',
        'class': 'student_class',
        'student class': 'student_class',
        'village': 'city',
        'town': 'city',
        'city village': 'city',
        'district': 'district',
        'state name': 'state',
        'parent name': 'parent_name',
        'father name': 'parent_name',
        'guardian name': 'parent_name',
        'parent phone': 'parent_phone',
        'father phone': 'parent_phone',
        'guardian phone': 'parent_phone',
        'parent email': 'parent_email',
        'date of birth': 'date_of_birth',
        'dob': 'date_of_birth',
        'pin': 'pin_code',
        'pincode': 'pin_code',
        'pin code': 'pin_code',
    }

    # ── Columns requested by the schools list (school → student master) ──
    # Order matches the reference spreadsheet exported to admins.
    list_display = (
        'school_name', 'state', 'district', 'city',
        'full_name_display', 'phone',
        'parent_guardian_name', 'parent_guardian_phone',
        'student_code', 'email',
        'student_class', 'gender', 'category',
        'handicap_display', 'date_of_birth',
        'tps_display', 'previous_class_marks',
        'status_badge',
    )
    list_display_links = ('full_name_display', 'student_code')
    list_filter = (
        'status', 'student_class', 'exam_target', 'stream', 'category',
        'gender', 'physically_handicapped', 'tps', 'state',
    )
    search_fields = (
        'student_code', 'first_name', 'last_name', 'email', 'phone',
        'parent_name', 'parent_phone',
        'school_name', 'state', 'district', 'city',
    )
    readonly_fields = (
        'id', 'student_code', 'created_at', 'updated_at', 'last_login_at',
        'status_changed_at',
    )
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected, suspend_selected]

    # ── Edit form: ≤30 active fields + 6 reserved extension fields = 36 ──
    fieldsets = (
        ('Identity', {
            # 7 fields
            'fields': (
                'student_code', 'first_name', 'last_name',
                'email', 'phone', 'avatar_url', 'tenant',
            ),
        }),
        ('Academic', {
            # 8 fields – all dropdowns / foreign keys (no JSON editor)
            'fields': (
                'student_class', 'exam_target', 'stream', 'medium', 'board',
                'school_name', 'batch', 'category',
            ),
        }),
        ('Location', {
            # 4 fields
            'fields': ('state', 'district', 'city', 'pin_code'),
        }),
        ('Personal', {
            # 4 fields
            'fields': ('date_of_birth', 'gender', 'physically_handicapped', 'tps'),
        }),
        ('Previous Academics', {
            # 1 field (placeholder for future grade/marks expansion)
            'fields': ('previous_class_marks',),
        }),
        ('Father / Guardian', {
            # 4 fields
            'fields': (
                'parent_name', 'parent_relation', 'parent_phone', 'parent_email',
            ),
            'classes': ('collapse',),
        }),
        ('Status', {
            # 2 fields
            'fields': ('status', 'status_reason'),
        }),
        ('Reserved for future use', {
            # 6 extension slots — kept for custom per-tenant data.
            # See Student.ext_* docstring for usage guidelines.
            'fields': (
                'ext_string_1', 'ext_string_2',
                'ext_student_1', 'ext_student_2', 'ext_student_3',
                'meta_data',
            ),
            'classes': ('collapse',),
            'description': (
                '<div style="background:rgba(148,163,184,0.08);border:1px solid rgba(148,163,184,0.25);'
                'border-radius:8px;padding:10px 14px;margin:6px 0;font-size:0.82rem;color:#475569;">'
                '<strong>Extension fields</strong> are deliberately unused slots reserved for '
                'tenant-specific future data (e.g. scholarship code, custom badge). They let us '
                'capture new attributes without a database migration. Leave blank unless your '
                'tenant rollout plan requires them. They can be safely removed in a future release '
                'if the schema stabilises.</div>'
            ),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'last_login_at', 'status_changed_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Column helpers ──
    def full_name_display(self, obj):
        initials = f"{obj.first_name[0]}{obj.last_name[0]}" if obj.first_name and obj.last_name else '?'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);'
            'display:flex;align-items:center;justify-content:center;font-size:0.65rem;color:#fff;font-weight:700;">{}</div>'
            '<span style="font-weight:600;color:#1e293b;">{} {}</span></div>',
            initials, obj.first_name, obj.last_name,
        )
    full_name_display.short_description = 'Student Name'
    full_name_display.admin_order_field = 'first_name'

    def parent_guardian_name(self, obj):
        return obj.parent_name or '—'
    parent_guardian_name.short_description = 'Father / Guardian Name'
    parent_guardian_name.admin_order_field = 'parent_name'

    def parent_guardian_phone(self, obj):
        return obj.parent_phone or '—'
    parent_guardian_phone.short_description = 'Father / Guardian Phone'
    parent_guardian_phone.admin_order_field = 'parent_phone'

    def handicap_display(self, obj):
        return 'Yes' if obj.physically_handicapped else 'No'
    handicap_display.short_description = 'Physically Handicapped'
    handicap_display.admin_order_field = 'physically_handicapped'

    def tps_display(self, obj):
        return 'Yes' if obj.tps else 'No'
    tps_display.short_description = 'TPS'
    tps_display.admin_order_field = 'tps'


# ═══════════════════════════════════════════════════════════════════
# 1. USER LIFECYCLE — Teachers
# ═══════════════════════════════════════════════════════════════════
@admin.register(Teacher)
class TeacherAdmin(ImportExportMixin, EnhancedModelAdmin):
    change_list_template = 'admin/accounts/teacher/change_list.html'

    # ── Import header → field aliases (case/space-insensitive) ──
    # Lets imports use natural column names like "State", "Village", "Joining Date".
    import_field_aliases = {
        'state': 'teacher_state',
        'state name': 'teacher_state',
        'city': 'teacher_city',
        'village': 'teacher_city',
        'town': 'teacher_city',
        'city village': 'teacher_city',
        'district': 'teacher_district',
        'district name': 'teacher_district',
        'joining date': 'joining_date',
        'date of joining': 'joining_date',
        'doj': 'joining_date',
        'employee id': 'employee_id',
        'emp id': 'employee_id',
        'teacher code': 'teacher_code',
        'code': 'teacher_code',
        'name': 'first_name',  # legacy single-name column
        'full name': 'first_name',
        'first name': 'first_name',
        'last name': 'last_name',
        'surname': 'last_name',
        'phone number': 'phone',
        'mobile': 'phone',
        'mobile number': 'phone',
        'email id': 'email',
        'email address': 'email',
        'subject': 'subjects',
        'subjects taught': 'subjects',
        'qualification': 'qualification',
        'highest degree': 'highest_degree',
        'experience': 'experience_years',
        'experience years': 'experience_years',
        'employment type': 'employment_type',
        'designation': 'designation',
        'department': 'department',
        'address': 'address',
        'pin': 'pin_code',
        'pin code': 'pin_code',
        'pincode': 'pin_code',
    }

    # Columns requested: code, name, phone, email, designation, subject,
    # status, city/village, district, state, joining date.
    list_display = (
        'teacher_code', 'full_name_display', 'phone', 'email',
        'designation', 'subjects_display', 'status_badge',
        'teacher_city', 'teacher_district', 'teacher_state',
        'joining_date',
    )
    list_display_links = ('teacher_code', 'full_name_display')
    list_filter = ('status', 'employment_type', 'designation', 'teacher_state')
    search_fields = (
        'teacher_code', 'first_name', 'last_name', 'email', 'phone',
        'designation', 'teacher_city', 'teacher_district', 'teacher_state',
    )
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'last_login_at',
        'status_changed_at',
    )
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected, suspend_selected]

    fieldsets = (
        ('Identity', {
            'fields': (
                'teacher_code', 'first_name', 'last_name',
                'email', 'phone', 'avatar_url', 'tenant',
            ),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.25);'
                'border-radius:8px;padding:8px 14px;margin:6px 0;font-size:0.82rem;color:#4f46e5;">'
                '<strong>Teacher Code</strong> format: '
                '<code>&lt;3-letter state&gt;&lt;3-letter district&gt;&lt;4-digit serial&gt;</code> '
                '— e.g. <code>APKRL0001</code> for Andhra Pradesh / Kurnool / #0001.</div>'
            ),
        }),
        ('Professional', {
            'fields': (
                'employment_type', 'designation', 'department', 'joining_date',
                'subjects', 'specialization', 'qualification', 'highest_degree',
                'experience_years',
            ),
        }),
        ('Contact / Location', {
            'fields': (
                'personal_email', 'personal_phone', 'emergency_contact',
                'address', 'teacher_city', 'teacher_district', 'teacher_state',
            ),
        }),
        ('Permissions', {
            'fields': (
                'can_edit_student_profile', 'can_override_attendance',
                'can_override_scores', 'max_batches_allowed',
            ),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'status_reason'),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'last_login_at', 'status_changed_at'),
            'classes': ('collapse',),
        }),
        # Financial, YouTube and Extension Fields sections intentionally removed.
    )

    def full_name_display(self, obj):
        initials = f"{obj.first_name[0]}{obj.last_name[0]}" if obj.first_name and obj.last_name else '?'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);'
            'display:flex;align-items:center;justify-content:center;font-size:0.65rem;color:#fff;font-weight:700;">{}</div>'
            '<span style="font-weight:600;color:#1e293b;">{} {}</span></div>',
            initials, obj.first_name, obj.last_name
        )
    full_name_display.short_description = 'Teacher Name'
    full_name_display.admin_order_field = 'first_name'

    def subjects_display(self, obj):
        val = getattr(obj, 'subjects', None)
        if isinstance(val, list) and val:
            return ', '.join(str(v) for v in val[:3]) + ('…' if len(val) > 3 else '')
        if isinstance(val, str) and val:
            return val
        return '—'
    subjects_display.short_description = 'Subject'


# ═══════════════════════════════════════════════════════════════════
# 1. USER LIFECYCLE — Admins
# ═══════════════════════════════════════════════════════════════════
class AdminRoleInline(admin.TabularInline):
    model = UserRoleAssignment
    extra = 0
    fk_name = None  # not a real FK — handled via get_queryset
    verbose_name = 'Scoped Role'
    verbose_name_plural = 'Scoped Role Assignments'

    def get_queryset(self, request):
        return UserRoleAssignment.objects.none()


class AdminUserAdminForm(forms.ModelForm):
    """
    Custom form for the Admin user model that:
      * Replaces the JSON `permissions_override` textarea with a multi-select
        populated from active Permission rows (stored as a list of codes).
      * Replaces the JSON `managed_branches` textarea with a multi-select
        whose options come from existing Tenant rows + any previously-saved
        branch values (so legacy data is preserved and selectable).
      * Adds a write-only `raw_password` field so operators can set / reset
        the admin's login password from the admin panel without having to
        paste a pre-hashed value into `password_hash`.
    """

    raw_password = forms.CharField(
        label='Set password',
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text=(
            'Enter a plain password to set / reset the login password. '
            'Leave blank on edit to keep the existing password. Required on creation.'
        ),
    )

    permissions_override = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={'size': '10', 'style': 'min-width:420px'}),
        help_text='Direct permission overrides (in addition to those granted by the assigned Role).',
    )

    managed_branches = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={'size': '8', 'style': 'min-width:420px'}),
        help_text='Restrict this admin to a specific list of branches / campuses. Empty = all branches in tenant.',
    )

    class Meta:
        model = AdminUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---- permissions_override choices: every active Permission ----
        perm_choices = list(
            Permission.objects.filter(is_active=True)
            .order_by('module', 'category', 'code')
            .values_list('code', 'name')
        )
        # Preserve any previously-saved code that is no longer active so the
        # operator can see and clear it instead of silently dropping it.
        existing = list(self.initial.get('permissions_override') or [])
        if self.instance and self.instance.pk:
            existing = list(self.instance.permissions_override or [])
        known = {c for c, _ in perm_choices}
        for code in existing:
            if code and code not in known:
                perm_choices.append((code, f'{code} (inactive)'))
        self.fields['permissions_override'].choices = perm_choices
        self.fields['permissions_override'].initial = existing

        # ---- managed_branches choices: tenants + previously-saved values ----
        from tenants.models import Tenant
        branch_choices = []
        seen = set()
        for code, name in Tenant.objects.order_by('name').values_list('code', 'name'):
            if code and code not in seen:
                branch_choices.append((code, f'{name} ({code})'))
                seen.add(code)
        existing_branches = list(self.initial.get('managed_branches') or [])
        if self.instance and self.instance.pk:
            existing_branches = list(self.instance.managed_branches or [])
        for b in existing_branches:
            if b and b not in seen:
                branch_choices.append((b, b))
                seen.add(b)
        self.fields['managed_branches'].choices = branch_choices
        self.fields['managed_branches'].initial = existing_branches

        # ---- raw_password required only on creation ----
        if self.instance and self.instance.pk:
            self.fields['raw_password'].help_text = (
                'Leave blank to keep the existing password. '
                'Enter a new value to reset it (will be hashed before save).'
            )
        else:
            self.fields['raw_password'].required = True

        # password_hash should never be edited by hand
        if 'password_hash' in self.fields:
            self.fields['password_hash'].required = False
            self.fields['password_hash'].widget.attrs['readonly'] = True
            self.fields['password_hash'].help_text = (
                'Stored hash (read-only). Use "Set password" above to change it.'
            )

    def clean_permissions_override(self):
        return list(self.cleaned_data.get('permissions_override') or [])

    def clean_managed_branches(self):
        return list(self.cleaned_data.get('managed_branches') or [])


@admin.register(AdminUser)
class AdminUserAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = AdminUserAdminForm
    list_display = (
        'admin_code', 'full_name_display', 'email', 'admin_type_badge',
        'role_display', 'staff_role_display', 'lockout_display',
        'status_badge', 'created_display',
    )
    list_filter = ('status', 'admin_type', 'role', 'staff_role', 'mfa_enabled')
    search_fields = ('admin_code', 'first_name', 'last_name', 'email', 'phone')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'last_login_at', 'last_activity_at',
        'password_changed_at', 'status_changed_at', 'status_changed_by',
        'email_verified_at', 'phone_verified_at', 'deleted_at',
    )
    list_per_page = 25
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    def save_model(self, request, obj, form, change):
        """Hash any plain password supplied via the `raw_password` field."""
        raw = form.cleaned_data.get('raw_password') if form else None
        if raw:
            obj.set_password(raw)
            obj.force_password_change = False
        elif not change and not obj.password_hash:
            # Defensive: never persist an admin with an empty password hash.
            from django.core.exceptions import ValidationError
            raise ValidationError('A password is required when creating a new Admin.')
        super().save_model(request, obj, form, change)

    fieldsets = (
        ('Identity', {
            'fields': ('id', 'tenant', 'admin_code', 'first_name', 'last_name', 'display_name', 'email', 'phone', 'avatar_url'),
        }),
        ('Role & Access Control', {
            'fields': ('admin_type', 'role', 'staff_role', 'permissions_override', 'managed_branches'),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>Role Hierarchy:</strong> SUPER_ADMIN → TENANT_ADMIN → DEPARTMENT_ADMIN → TEACHER → TEACHING_ASSISTANT → STUDENT<br>'
                'Higher roles automatically inherit all lower-level permissions. '
                'Assign a <strong>Role</strong> for RBAC permissions and a <strong>Staff Role</strong> for admin panel access control.'
                '</div>'
            ),
        }),
        ('Security & Authentication', {
            'fields': ('raw_password', 'password_hash', 'password_changed_at', 'mfa_enabled', 'mfa_method', 'mfa_enforced_by_admin',
                       'force_password_change',
                       'require_ip_whitelist', 'allowed_ips', 'session_timeout_minutes'),
            'classes': ('collapse',),
        }),
        ('Lockout & Password Policy', {
            'fields': ('failed_login_count', 'locked_until', 'last_password_change', 'password_expires_at'),
            'description': (
                '<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);'
                'border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:0.82rem;color:#f87171;">'
                'Max 5 failed attempts → 30-min lockout. Passwords expire every 90 days.'
                '</div>'
            ),
            'classes': ('collapse',),
        }),
        ('Preferences', {
            'fields': ('theme', 'accent_color', 'admin_timezone', 'time_format'),
            'classes': ('collapse',),
        }),
        ('Preferences (Extended)', {
            'fields': ('dashboard_layout', 'default_view', 'admin_config', 'admin_date_format'),
            'classes': ('collapse',),
        }),
        ('Status & Timestamps', {
            'fields': ('status', 'status_reason', 'email_verified', 'email_verified_at',
                       'phone_verified', 'phone_verified_at',
                       'status_changed_at', 'status_changed_by', 'deleted_at',
                       'created_at', 'updated_at', 'last_login_at', 'last_activity_at'),
        }),
        ('Extension Fields', {
            'fields': ('meta_data', 'ext_string_1', 'ext_string_2', 'ext_text_1', 'ext_json_1',
                       'ext_decimal_1', 'ext_admin_1', 'ext_admin_2', 'ext_admin_3'),
            'classes': ('collapse',),
        }),
    )

    def full_name_display(self, obj):
        initials = f"{obj.first_name[0]}{obj.last_name[0]}" if obj.first_name and obj.last_name else '?'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#f59e0b,#d97706);'
            'display:flex;align-items:center;justify-content:center;font-size:0.65rem;color:#fff;font-weight:700;">{}</div>'
            '<span style="font-weight:600;color:#1e293b;">{} {}</span></div>',
            initials, obj.first_name, obj.last_name
        )
    full_name_display.short_description = 'Name'

    def admin_type_badge(self, obj):
        at = getattr(obj, 'admin_type', '')
        type_colors = {
            'SUPER_ADMIN': ('#ef4444', 'rgba(239,68,68,0.12)'),
            'TENANT_ADMIN': ('#f59e0b', 'rgba(245,158,11,0.12)'),
            'DEPARTMENT_ADMIN': ('#06b6d4', 'rgba(6,182,212,0.12)'),
            'BRANCH_ADMIN': ('#3b82f6', 'rgba(59,130,246,0.12)'),
            'ACADEMIC_ADMIN': ('#10b981', 'rgba(16,185,129,0.12)'),
            'FINANCE_ADMIN': ('#8b5cf6', 'rgba(139,92,246,0.12)'),
            'SUPPORT_ADMIN': ('#22d3ee', 'rgba(34,211,238,0.12)'),
        }
        fg, bg = type_colors.get(at, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, at.replace('_', ' ').title() if at else '-'
        )
    admin_type_badge.short_description = 'Type'

    def role_display(self, obj):
        role = getattr(obj, 'role', None)
        if role:
            return format_html(
                '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:6px;'
                'font-size:0.72rem;font-weight:600;color:#a5b4fc;background:rgba(99,102,241,0.1);">'
                '<i class="fas fa-shield-alt" style="font-size:0.65rem;"></i> {}</span>',
                role.name
            )
        return format_html('<span style="color:#475569;">No Role</span>')
    role_display.short_description = 'Role'

    def staff_role_display(self, obj):
        sr = getattr(obj, 'staff_role', None)
        if sr:
            colors = {'SUPER_ADMIN': '#ef4444', 'ADMIN': '#f59e0b', 'OPERATOR': '#10b981'}
            c = colors.get(sr.level, '#94a3b8')
            return format_html(
                '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;'
                'color:{};background:{}22;">{}</span>',
                c, c, sr.name
            )
        return format_html('<span style="color:#475569;">—</span>')
    staff_role_display.short_description = 'Staff Role'

    def lockout_display(self, obj):
        if obj.locked_until and obj.locked_until > timezone.now():
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:600;'
                'color:#ef4444;background:rgba(239,68,68,0.12);">'
                '<i class="fas fa-lock"></i> Locked</span>'
            )
        if obj.failed_login_count and obj.failed_login_count > 0:
            return format_html(
                '<span style="color:#f59e0b;font-size:0.82rem;">{}/5 fails</span>',
                obj.failed_login_count
            )
        return format_html('<span style="color:#10b981;font-size:0.82rem;">OK</span>')
    lockout_display.short_description = 'Lockout'


# ═══════════════════════════════════════════════════════════════════
# 1. USER LIFECYCLE — Parents
# ═══════════════════════════════════════════════════════════════════
@admin.register(Parent)
class ParentAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('parent_code', 'first_name', 'last_name', 'email', 'relationship', 'status_badge')
    list_filter = ('status', 'relationship')
    search_fields = ('parent_code', 'first_name', 'last_name', 'email')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'last_login_at', 'last_activity_at',
        'password_changed_at', 'status_changed_at', 'status_changed_by',
        'email_verified_at', 'phone_verified_at', 'deleted_at',
    )
    fieldsets = (
        ('Identity', {
            'fields': (
                'id', 'tenant', 'parent_code', 'first_name', 'last_name', 'display_name',
                'email', 'phone', 'avatar_url',
            ),
        }),
        ('Relationship', {
            'fields': ('relationship', 'primary_student'),
        }),
        ('Permissions', {
            'fields': (
                'receive_notifications', 'can_view_attendance', 'can_view_results',
                'can_view_fee_details', 'can_communicate_teacher',
            ),
        }),
        ('Security', {
            'fields': (
                'password_hash', 'password_changed_at', 'force_password_change',
                'mfa_enabled', 'mfa_method', 'mfa_enforced_by_admin',
            ),
            'classes': ('collapse',),
        }),
        ('Status & Timestamps', {
            'fields': (
                'status', 'status_reason', 'status_changed_at', 'status_changed_by',
                'email_verified', 'email_verified_at', 'phone_verified', 'phone_verified_at',
                'created_at', 'updated_at', 'deleted_at', 'last_login_at', 'last_activity_at',
            ),
        }),
        ('Extension Fields', {
            'fields': (
                'meta_data', 'ext_string_1', 'ext_string_2', 'ext_text_1', 'ext_json_1',
                'ext_decimal_1', 'ext_parent_1', 'ext_parent_2',
            ),
            'classes': ('collapse',),
        }),
    )


# ═══════════════════════════════════════════════════════════════════
# 2. PERMISSIONS & ROLES — Roles
# ═══════════════════════════════════════════════════════════════════
class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ('permission',)
    readonly_fields = ('created_date',)
    verbose_name = 'Permission'
    verbose_name_plural = 'Permissions (auto-inherited when role is assigned)'
    can_delete = True

    def created_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%d %b %Y')
        return '-'
    created_date.short_description = 'Created'

    def get_fields(self, request, obj=None):
        return ('permission', 'created_date')


@admin.register(Role)
class RoleAdmin(EnhancedModelAdmin):
    list_display = (
        'code', 'name', 'type_badge', 'applies_to_badge', 'level_display',
        'parent_role_display', 'perm_count', 'assignment_count', 'active_badge',
    )
    list_filter = ('role_type', 'applies_to', 'is_active')
    search_fields = ('code', 'name')
    inlines = [RolePermissionInline]
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Role Identity', {
            'fields': ('tenant', 'code', 'name', 'description', 'created_by'),
        }),
        ('Classification', {
            'fields': ('role_type', 'applies_to', 'level'),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>Hierarchy Levels:</strong> '
                'SUPER_ADMIN (100) → TENANT_ADMIN (90) → DEPARTMENT_ADMIN (80) → '
                'TEACHER (50) → TEACHING_ASSISTANT (40) → STUDENT (10)<br>'
                'Higher levels inherit all permissions from lower levels.'
                '</div>'
            ),
        }),
        ('Inheritance', {
            'fields': ('parent_role',),
            'description': 'Selecting a parent role means this role automatically inherits all permissions from the parent. Permissions flow: Parent → Child.',
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Timestamps & Meta', {
            'fields': ('created_at', 'updated_at', 'role_meta', 'ext_role_1'),
            'classes': ('collapse',),
        }),
    )

    def type_badge(self, obj):
        rt = getattr(obj, 'role_type', '')
        colors = {
            'SYSTEM': ('#ef4444', 'rgba(239,68,68,0.12)'),
            'TENANT_DEFAULT': ('#f59e0b', 'rgba(245,158,11,0.12)'),
            'CUSTOM': ('#8b5cf6', 'rgba(139,92,246,0.12)'),
        }
        fg, bg = colors.get(rt, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, rt.replace('_', ' ').title() if rt else '-'
        )
    type_badge.short_description = 'Type'

    def applies_to_badge(self, obj):
        at = getattr(obj, 'applies_to', '')
        colors = {
            'ADMIN': ('#fbbf24', 'rgba(245,158,11,0.12)'),
            'TEACHER': ('#34d399', 'rgba(16,185,129,0.12)'),
            'TEACHING_ASSISTANT': ('#22d3ee', 'rgba(34,211,238,0.12)'),
            'STUDENT': ('#60a5fa', 'rgba(59,130,246,0.12)'),
            'PARENT': ('#c084fc', 'rgba(192,132,252,0.12)'),
            'ALL': ('#94a3b8', 'rgba(148,163,184,0.12)'),
        }
        fg, bg = colors.get(at, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, at
        )
    applies_to_badge.short_description = 'For'

    def level_display(self, obj):
        level = getattr(obj, 'level', 0) or 0
        color = '#ef4444' if level >= 90 else '#f59e0b' if level >= 50 else '#10b981' if level >= 10 else '#94a3b8'
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};'
            'background:{}22;font-family:monospace;">L{}</span>',
            color, color, level
        )
    level_display.short_description = 'Level'
    level_display.admin_order_field = 'level'

    def parent_role_display(self, obj):
        parent = getattr(obj, 'parent_role', None)
        if parent:
            return format_html(
                '<span style="display:inline-flex;align-items:center;gap:4px;color:#a5b4fc;font-size:0.82rem;">'
                '<i class="fas fa-arrow-up" style="font-size:0.65rem;"></i> {}</span>',
                parent.name
            )
        return format_html('<span style="color:#475569;">Root</span>')
    parent_role_display.short_description = 'Inherits From'

    def perm_count(self, obj):
        count = obj.role_permissions.count()
        parent = obj.parent_role
        inherited = 0
        visited = set()
        while parent and parent.pk not in visited:
            visited.add(parent.pk)
            inherited += parent.role_permissions.count()
            parent = parent.parent_role
        if inherited > 0:
            return format_html(
                '<span style="color:#10b981;font-weight:600;">{}</span>'
                '<span style="color:#64748b;font-size:0.75rem;"> (+{} inherited)</span>',
                count, inherited
            )
        return format_html('<span style="color:#10b981;font-weight:600;">{}</span>', count)
    perm_count.short_description = 'Permissions'

    def assignment_count(self, obj):
        count = obj.user_assignments.filter(is_active=True).count()
        return format_html('<span style="color:#6366f1;font-weight:600;">{}</span>', count)
    assignment_count.short_description = 'Users'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# 2. PERMISSIONS & ROLES — Permissions
# ═══════════════════════════════════════════════════════════════════
@admin.register(Permission)
class PermissionAdmin(EnhancedModelAdmin):
    list_display = ('code', 'name', 'module_badge', 'category_badge', 'action_badge', 'scope_badge', 'active_badge')
    list_filter = ('module', 'action', 'scope', 'is_active')
    search_fields = ('code', 'name', 'description')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    list_per_page = 50
    readonly_fields = ('id',)
    fieldsets = (
        ('Definition', {
            'fields': ('id', 'code', 'name', 'description'),
        }),
        ('Classification', {
            'fields': ('module', 'category', 'action', 'resource', 'scope'),
        }),
        ('Rules', {
            'fields': ('requires', 'is_active', 'permission_meta'),
        }),
    )

    def module_badge(self, obj):
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            obj.module
        )
    module_badge.short_description = 'Module'

    def category_badge(self, obj):
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'background:rgba(139,92,246,0.1);color:#c084fc;font-weight:500;">{}</span>',
            obj.category
        )
    category_badge.short_description = 'Category'

    def action_badge(self, obj):
        action_colors = {
            'CREATE': '#10b981', 'READ': '#3b82f6', 'UPDATE': '#f59e0b',
            'DELETE': '#ef4444', 'EXECUTE': '#8b5cf6', 'APPROVE': '#22d3ee', 'EXPORT': '#94a3b8',
        }
        c = action_colors.get(getattr(obj, 'action', ''), '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;color:{};background:{}22;font-weight:700;">{}</span>',
            c, c, getattr(obj, 'action', '-')
        )
    action_badge.short_description = 'Action'

    def scope_badge(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:0.82rem;font-weight:500;">{}</span>',
            getattr(obj, 'scope', '-')
        )
    scope_badge.short_description = 'Scope'

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', True))
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# 2. PERMISSIONS & ROLES — Staff Roles
# ═══════════════════════════════════════════════════════════════════
@admin.register(StaffRole)
class StaffRoleAdmin(EnhancedModelAdmin):
    list_display = ('name', 'level_badge', 'permissions_summary', 'scope_info', 'active_sr_badge', 'staff_count', 'updated_at')
    list_filter = ('level', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    actions = [export_as_csv, activate_selected, deactivate_selected]

    def get_form(self, request, obj=None, **kwargs):
        """Replace JSONField textareas for allowed_centers/batches with multi-select dropdowns."""
        from django import forms as _forms
        from django.contrib.admin.widgets import FilteredSelectMultiple as _FSM

        # Build dynamic choices
        try:
            from academics.models import Batch as _Batch
            batch_choices = [(str(b.id), f"{b.code} — {b.name}") for b in _Batch.objects.all().order_by('code')]
        except Exception:
            batch_choices = []
        try:
            from accounts.models import Student as _Student
            center_qs = _Student.objects.exclude(school_name__isnull=True).exclude(school_name='').values_list('school_name', flat=True).distinct().order_by('school_name')
            center_choices = [(name, name) for name in center_qs]
        except Exception:
            center_choices = []

        BaseForm = super().get_form(request, obj, **kwargs)

        class _StaffRoleForm(BaseForm):
            allowed_centers = _forms.MultipleChoiceField(
                choices=center_choices, required=False,
                widget=_FSM('Centers / Schools', is_stacked=False),
                help_text='Pick one or more centers. Leave empty for unrestricted access.',
            )
            allowed_batches = _forms.MultipleChoiceField(
                choices=batch_choices, required=False,
                widget=_FSM('Batches', is_stacked=False),
                help_text='Pick one or more batches. Leave empty for unrestricted access.',
            )

            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                if self.instance and self.instance.pk:
                    self.fields['allowed_centers'].initial = self.instance.allowed_centers or []
                    self.fields['allowed_batches'].initial = [str(x) for x in (self.instance.allowed_batches or [])]

            def save(self, commit=True):
                obj = super().save(commit=False)
                obj.allowed_centers = list(self.cleaned_data.get('allowed_centers') or [])
                obj.allowed_batches = list(self.cleaned_data.get('allowed_batches') or [])
                if commit:
                    obj.save()
                    self.save_m2m()
                return obj

        return _StaffRoleForm
    fieldsets = (
        ('Role Info', {
            'fields': ('tenant', 'name', 'level', 'description', 'is_active', 'created_by')
        }),
        ('Management Permissions', {
            'fields': (
                'can_manage_students', 'can_manage_teachers', 'can_manage_exams',
                'can_manage_attendance', 'can_manage_content', 'can_manage_finance',
            ),
        }),
        ('System Permissions', {
            'fields': (
                'can_manage_settings', 'can_manage_integrations', 'can_view_reports',
                'can_export_data', 'can_manage_roles', 'can_view_audit',
                'can_manage_website', 'can_manage_ai',
            ),
        }),
        ('Scope Restrictions', {
            'fields': ('allowed_centers', 'allowed_batches'),
            'classes': ('collapse',),
            'description': 'Leave empty for unrestricted access. JSON array of IDs to limit scope.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def level_badge(self, obj):
        colors = {'SUPER_ADMIN': '#ef4444', 'ADMIN': '#2563eb', 'OPERATOR': '#16a34a'}
        labels = {'SUPER_ADMIN': '👑 Super Admin', 'ADMIN': '🛡️ Admin', 'OPERATOR': '⚙️ Operator'}
        c = colors.get(obj.level, '#64748b')
        return format_html('<span style="background:{};color:#fff;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:600;">{}</span>', c, labels.get(obj.level, obj.level))
    level_badge.short_description = 'Level'

    def permissions_summary(self, obj):
        perm_fields = [
            'can_manage_students', 'can_manage_teachers', 'can_manage_exams',
            'can_manage_attendance', 'can_manage_content', 'can_manage_finance',
            'can_manage_settings', 'can_manage_integrations', 'can_view_reports',
            'can_export_data', 'can_manage_roles', 'can_view_audit',
            'can_manage_website', 'can_manage_ai',
        ]
        count = sum(1 for f in perm_fields if getattr(obj, f, False))
        return format_html('<span style="color:#8b5cf6;font-weight:600;">{}/14</span> permissions', count)
    permissions_summary.short_description = 'Permissions'

    def scope_info(self, obj):
        centers = obj.allowed_centers or []
        batches = obj.allowed_batches or []
        if not centers and not batches:
            return format_html('<span style="color:#22c55e;">Unrestricted</span>')
        parts = []
        if centers:
            parts.append(f'{len(centers)} centers')
        if batches:
            parts.append(f'{len(batches)} batches')
        return format_html('<span style="color:#f59e0b;">{}</span>', ', '.join(parts))
    scope_info.short_description = 'Scope'

    def active_sr_badge(self, obj):
        return colored_status(obj.is_active)
    active_sr_badge.short_description = 'Active'

    def staff_count(self, obj):
        count = obj.staff_admins.count()
        return format_html('<span style="color:#6366f1;font-weight:600;">{}</span>', count)
    staff_count.short_description = 'Staff'


# ═══════════════════════════════════════════════════════════════════
# 1/3. USER LIFECYCLE — User Role Assignments
# ═══════════════════════════════════════════════════════════════════
@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(EnhancedModelAdmin):
    list_display = (
        'user_type_badge', 'user_id_short', 'role_badge', 'scope_badge',
        'temporal_badge', 'effective_badge', 'created_display',
    )
    list_filter = ('user_type', 'scope_type', 'is_active')
    search_fields = ('user_id', 'role__name', 'role__code')
    raw_id_fields = ('role',)
    list_per_page = 30
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User Binding', {
            'fields': ('tenant', 'user_id', 'user_type'),
        }),
        ('Role & Scope', {
            'fields': ('role', 'scope_type', 'scope_id'),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>Scope Types:</strong> '
                'GLOBAL (entire platform) → TENANT (single tenant) → DEPARTMENT → COURSE / BATCH<br>'
                'Set <strong>scope_id</strong> to the UUID of the scoped entity for DEPARTMENT/COURSE/BATCH.'
                '</div>'
            ),
        }),
        ('Temporal (Optional)', {
            'fields': ('valid_from', 'valid_until'),
            'description': 'Leave blank for permanent assignment. Set dates for temporary/guest roles.',
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_active', 'assigned_by', 'created_at', 'updated_at'),
        }),
    )

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': ('#60a5fa', 'rgba(59,130,246,0.12)'),
            'TEACHER': ('#34d399', 'rgba(16,185,129,0.12)'),
            'ADMIN': ('#fbbf24', 'rgba(245,158,11,0.12)'),
            'PARENT': ('#c084fc', 'rgba(192,132,252,0.12)'),
        }
        fg, bg = type_colors.get(obj.user_type, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.user_type
        )
    user_type_badge.short_description = 'User Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;" title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User ID'

    def role_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:6px;'
            'font-size:0.72rem;font-weight:600;color:#a5b4fc;background:rgba(99,102,241,0.1);">'
            '<i class="fas fa-shield-alt" style="font-size:0.65rem;"></i> {}</span>',
            obj.role.name if obj.role else '—'
        )
    role_badge.short_description = 'Role'

    def scope_badge(self, obj):
        scope_colors = {
            'GLOBAL': '#ef4444', 'TENANT': '#f59e0b', 'DEPARTMENT': '#3b82f6',
            'COURSE': '#8b5cf6', 'BATCH': '#10b981',
        }
        c = scope_colors.get(obj.scope_type, '#94a3b8')
        label = obj.scope_type
        if obj.scope_id:
            label += f' ({str(obj.scope_id)[:8]}…)'
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, label
        )
    scope_badge.short_description = 'Scope'

    def temporal_badge(self, obj):
        if obj.valid_from or obj.valid_until:
            now = timezone.now()
            if obj.valid_until and now > obj.valid_until:
                return format_html('<span style="color:#ef4444;font-size:0.78rem;">Expired</span>')
            if obj.valid_from and now < obj.valid_from:
                return format_html('<span style="color:#f59e0b;font-size:0.78rem;">Pending</span>')
            end = obj.valid_until.strftime('%d %b %Y') if obj.valid_until else '∞'
            return format_html('<span style="color:#10b981;font-size:0.78rem;">Until {}</span>', end)
        return format_html('<span style="color:#94a3b8;font-size:0.78rem;">Permanent</span>')
    temporal_badge.short_description = 'Duration'

    def effective_badge(self, obj):
        if obj.is_effective:
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:600;'
                'color:#10b981;background:rgba(16,185,129,0.12);">Active</span>'
            )
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:600;'
            'color:#ef4444;background:rgba(239,68,68,0.12);">Inactive</span>'
        )
    effective_badge.short_description = 'Effective'


# ═══════════════════════════════════════════════════════════════════
# 5. AUDIT & MONITORING — Access Logs
# ═══════════════════════════════════════════════════════════════════
@admin.register(AccessLog)
class AccessLogAdmin(EnhancedModelAdmin):
    list_display = (
        'timestamp_display', 'user_type_badge', 'user_id_short',
        'decision_badge', 'action', 'resource', 'ip_address',
    )
    list_filter = ('decision', 'user_type', 'action')
    search_fields = ('user_id', 'resource', 'action', 'ip_address', 'reason')
    readonly_fields = [f.name for f in AccessLog._meta.fields]
    date_hierarchy = 'timestamp'
    list_per_page = 50
    actions = [export_as_csv, export_as_json]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def timestamp_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;">{}</span>',
            obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        )
    timestamp_display.short_description = 'Time'
    timestamp_display.admin_order_field = 'timestamp'

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': '#60a5fa', 'TEACHER': '#34d399', 'ADMIN': '#fbbf24', 'PARENT': '#c084fc',
        }
        c = type_colors.get(obj.user_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, obj.user_type
        )
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;" title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User'

    def decision_badge(self, obj):
        if obj.decision == 'ALLOW':
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:700;'
                'color:#10b981;background:rgba(16,185,129,0.12);">ALLOW</span>'
            )
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;font-weight:700;'
            'color:#ef4444;background:rgba(239,68,68,0.12);">DENY</span>'
        )
    decision_badge.short_description = 'Decision'


# ═══════════════════════════════════════════════════════════════════
# 3. GROUPS & ROLE ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════

class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1
    fields = ('user_type', 'user_id', 'is_active', 'added_at')
    readonly_fields = ('added_at',)


class GroupRoleAssignmentInline(admin.TabularInline):
    model = GroupRoleAssignment
    extra = 1
    raw_id_fields = ('role',)
    fields = ('role', 'scope_type', 'scope_id', 'is_active')


@admin.register(UserGroup)
class UserGroupAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = (
        'code', 'name', 'type_badge', 'member_count',
        'role_count', 'active_badge', 'created_display',
    )
    list_filter = ('group_type', 'is_active')
    search_fields = ('code', 'name', 'description')
    inlines = [GroupMembershipInline, GroupRoleAssignmentInline]
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Group Identity', {
            'fields': ('tenant', 'code', 'name', 'description'),
        }),
        ('Classification', {
            'fields': ('group_type',),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>Group Types:</strong> '
                'DEPARTMENT (org-unit mapping) · BATCH (student batch mapping) · '
                'CUSTOM (ad-hoc groups) · SYSTEM (auto-managed)<br>'
                'Add <strong>Members</strong> below, then assign <strong>Roles</strong> — '
                'all members inherit the group\'s roles automatically.'
                '</div>'
            ),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def type_badge(self, obj):
        colors = {
            'DEPARTMENT': ('#3b82f6', 'rgba(59,130,246,0.12)'),
            'BATCH': ('#10b981', 'rgba(16,185,129,0.12)'),
            'CUSTOM': ('#8b5cf6', 'rgba(139,92,246,0.12)'),
            'SYSTEM': ('#f59e0b', 'rgba(245,158,11,0.12)'),
        }
        fg, bg = colors.get(obj.group_type, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.get_group_type_display()
        )
    type_badge.short_description = 'Type'

    def member_count(self, obj):
        count = obj.memberships.filter(is_active=True).count()
        return format_html(
            '<span style="color:#6366f1;font-weight:600;">{}</span>', count
        )
    member_count.short_description = 'Members'

    def role_count(self, obj):
        count = obj.role_assignments.filter(is_active=True).count()
        return format_html(
            '<span style="color:#10b981;font-weight:600;">{}</span>', count
        )
    role_count.short_description = 'Roles'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


@admin.register(GroupMembership)
class GroupMembershipAdmin(EnhancedModelAdmin):
    list_display = (
        'group', 'user_type_badge', 'user_id_short', 'active_badge', 'added_at',
    )
    list_filter = ('user_type', 'is_active', 'group')
    search_fields = ('user_id', 'group__name', 'group__code')
    raw_id_fields = ('group',)
    readonly_fields = ('id', 'added_at')
    actions = [export_as_csv, activate_selected, deactivate_selected]

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'group', 'user_id', 'user_type', 'is_active'),
        }),
        ('Audit', {
            'fields': ('added_by', 'added_at'),
        }),
    )

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': ('#60a5fa', 'rgba(59,130,246,0.12)'),
            'TEACHER': ('#34d399', 'rgba(16,185,129,0.12)'),
            'ADMIN': ('#fbbf24', 'rgba(245,158,11,0.12)'),
            'PARENT': ('#c084fc', 'rgba(192,132,252,0.12)'),
        }
        fg, bg = type_colors.get(obj.user_type, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.user_type
        )
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;"'
            ' title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


@admin.register(GroupRoleAssignment)
class GroupRoleAssignmentAdmin(EnhancedModelAdmin):
    list_display = (
        'group', 'role_badge', 'scope_badge', 'active_badge', 'created_display',
    )
    list_filter = ('scope_type', 'is_active')
    search_fields = ('group__name', 'role__name', 'role__code')
    raw_id_fields = ('group', 'role')
    readonly_fields = ('id', 'created_at')
    actions = [export_as_csv, activate_selected, deactivate_selected]

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'group', 'role', 'scope_type', 'scope_id', 'is_active'),
        }),
        ('Audit', {
            'fields': ('assigned_by', 'created_at'),
        }),
    )

    def role_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;'
            'border-radius:6px;font-size:0.72rem;font-weight:600;color:#a5b4fc;'
            'background:rgba(99,102,241,0.1);">'
            '<i class="fas fa-shield-alt" style="font-size:0.65rem;"></i> {}</span>',
            obj.role.name if obj.role else '—'
        )
    role_badge.short_description = 'Role'

    def scope_badge(self, obj):
        scope_colors = {
            'GLOBAL': '#ef4444', 'TENANT': '#f59e0b', 'DEPARTMENT': '#3b82f6',
            'COURSE': '#8b5cf6', 'BATCH': '#10b981',
        }
        c = scope_colors.get(obj.scope_type, '#94a3b8')
        label = obj.scope_type
        if obj.scope_id:
            label += f' ({str(obj.scope_id)[:8]}…)'
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, label
        )
    scope_badge.short_description = 'Scope'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# 4. ACCOUNT PROTECTION & LOGIN GOVERNANCE
# ═══════════════════════════════════════════════════════════════════

@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(EnhancedModelAdmin):
    list_display = (
        'name', 'applies_to_badge', 'password_summary',
        'mfa_summary', 'session_summary', 'lockout_summary',
        'active_badge', 'priority',
    )
    list_filter = ('applies_to', 'is_active', 'mfa_required')
    search_fields = ('name', 'description')
    actions = [export_as_csv, activate_selected, deactivate_selected]

    fieldsets = (
        ('Policy Identity', {
            'fields': ('tenant', 'name', 'description', 'applies_to', 'priority'),
        }),
        ('Password Policy', {
            'fields': (
                'min_password_length', 'require_uppercase', 'require_lowercase',
                'require_digits', 'require_special_chars', 'password_expiry_days',
                'password_history_count', 'prevent_common_passwords',
            ),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                'Define password complexity and rotation requirements. '
                'Password history prevents reuse of the last N passwords.'
                '</div>'
            ),
        }),
        ('Multi-Factor Authentication', {
            'fields': ('mfa_required', 'mfa_required_for_admins', 'allowed_mfa_methods'),
            'description': (
                '<div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#6ee7b7;">'
                'Allowed MFA methods: <code>["TOTP", "SMS", "EMAIL"]</code>'
                '</div>'
            ),
        }),
        ('Session Policy', {
            'fields': (
                'max_concurrent_sessions', 'session_timeout_minutes',
                'idle_timeout_minutes',
            ),
        }),
        ('Lockout Policy', {
            'fields': (
                'max_failed_attempts', 'lockout_duration_minutes',
                'progressive_lockout',
            ),
            'description': (
                '<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);'
                'border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:0.82rem;color:#f87171;">'
                'Progressive lockout doubles the duration on each subsequent lockout event.'
                '</div>'
            ),
        }),
        ('IP & Device Policy', {
            'fields': (
                'ip_whitelist_enabled', 'ip_whitelist',
                'geo_restriction_enabled', 'allowed_countries',
                'device_trust_enabled',
            ),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    def applies_to_badge(self, obj):
        colors = {
            'ALL': ('#94a3b8', 'rgba(148,163,184,0.12)'),
            'ADMIN': ('#fbbf24', 'rgba(245,158,11,0.12)'),
            'TEACHER': ('#34d399', 'rgba(16,185,129,0.12)'),
            'STUDENT': ('#60a5fa', 'rgba(59,130,246,0.12)'),
        }
        fg, bg = colors.get(obj.applies_to, ('#94a3b8', 'rgba(148,163,184,0.12)'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.get_applies_to_display()
        )
    applies_to_badge.short_description = 'Applies To'

    def password_summary(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:0.82rem;">Min {} · Expire {}d · History {}</span>',
            obj.min_password_length, obj.password_expiry_days, obj.password_history_count
        )
    password_summary.short_description = 'Password'

    def mfa_summary(self, obj):
        if obj.mfa_required:
            return format_html(
                '<span style="color:#10b981;font-weight:600;font-size:0.82rem;">'
                '&#128274; Required</span>'
            )
        if obj.mfa_required_for_admins:
            return format_html(
                '<span style="color:#f59e0b;font-size:0.82rem;">Admins Only</span>'
            )
        return format_html('<span style="color:#64748b;font-size:0.82rem;">Optional</span>')
    mfa_summary.short_description = 'MFA'

    def session_summary(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:0.82rem;">'
            'Max {} · Timeout {}m · Idle {}m</span>',
            obj.max_concurrent_sessions, obj.session_timeout_minutes,
            obj.idle_timeout_minutes
        )
    session_summary.short_description = 'Sessions'

    def lockout_summary(self, obj):
        prog = '↑' if obj.progressive_lockout else ''
        return format_html(
            '<span style="color:#f87171;font-size:0.82rem;">'
            '{} attempts → {}m {}</span>',
            obj.max_failed_attempts, obj.lockout_duration_minutes, prog
        )
    lockout_summary.short_description = 'Lockout'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


@admin.register(LoginAttemptLog)
class LoginAttemptLogAdmin(EnhancedModelAdmin):
    list_display = (
        'timestamp_display', 'result_badge', 'username_attempted',
        'user_type', 'ip_display', 'risk_badge', 'device_short',
    )
    list_filter = ('result', 'user_type')
    search_fields = ('username_attempted', 'user_id', 'ip_address')
    readonly_fields = [f.name for f in LoginAttemptLog._meta.fields]
    date_hierarchy = 'attempted_at'
    list_per_page = 50
    actions = [export_as_csv, export_as_json]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def timestamp_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;">{}</span>',
            obj.attempted_at.strftime('%Y-%m-%d %H:%M:%S')
        )
    timestamp_display.short_description = 'Time'
    timestamp_display.admin_order_field = 'attempted_at'

    def result_badge(self, obj):
        if obj.result == 'SUCCESS':
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
                'font-weight:700;color:#10b981;background:rgba(16,185,129,0.12);">SUCCESS</span>'
            )
        color = '#ef4444'
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;">{}</span>',
            color, color, obj.result.replace('FAILED_', '')
        )
    result_badge.short_description = 'Result'

    def ip_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;'
            'padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            obj.ip_address or '-'
        )
    ip_display.short_description = 'IP'

    def risk_badge(self, obj):
        score = obj.risk_score
        if score >= 80:
            c = '#ef4444'
        elif score >= 50:
            c = '#f59e0b'
        elif score >= 20:
            c = '#3b82f6'
        else:
            c = '#10b981'
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;font-family:monospace;">{}</span>',
            c, c, score
        )
    risk_badge.short_description = 'Risk'

    def device_short(self, obj):
        fp = obj.device_fingerprint
        if fp:
            return format_html(
                '<span style="font-family:monospace;font-size:0.75rem;color:#64748b;"'
                ' title="{}">{}&hellip;</span>',
                fp, fp[:12]
            )
        return format_html('<span style="color:#475569;">—</span>')
    device_short.short_description = 'Device'


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(EnhancedModelAdmin):
    list_display = (
        'device_name', 'user_type_badge', 'user_id_short',
        'device_type', 'browser', 'os_name',
        'active_badge', 'trusted_at', 'last_used_at',
    )
    list_filter = ('user_type', 'is_active', 'device_type')
    search_fields = ('device_name', 'user_id', 'device_fingerprint')
    readonly_fields = ('trusted_at',)
    actions = [export_as_csv, activate_selected, deactivate_selected]

    fieldsets = (
        ('Device Info', {
            'fields': (
                'tenant', 'device_name', 'device_fingerprint',
                'device_type', 'browser', 'os_name',
            ),
        }),
        ('User Binding', {
            'fields': ('user_id', 'user_type'),
        }),
        ('Trust Status', {
            'fields': (
                'is_active', 'trusted_at', 'expires_at', 'last_used_at',
                'revoked_at', 'revoked_reason',
            ),
        }),
    )

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': '#60a5fa', 'TEACHER': '#34d399',
            'ADMIN': '#fbbf24', 'PARENT': '#c084fc',
        }
        c = type_colors.get(obj.user_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, obj.user_type
        )
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;"'
            ' title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


# ═══════════════════════════════════════════════════════════════════
# 5. AUDIT & MONITORING — Audit Log Entries
# ═══════════════════════════════════════════════════════════════════

@admin.register(AuditEntry)
class AuditEntryAdmin(EnhancedModelAdmin):
    list_display = (
        'action_badge', 'resource_type', 'username', 'ip_display',
        'severity_badge', 'security_badge', 'created_display',
    )
    list_filter = ('action', 'severity', 'is_security_event', 'resource_type')
    search_fields = ('username', 'resource_type', 'action_description', 'ip_address')
    readonly_fields = [f.name for f in AuditEntry._meta.fields]
    date_hierarchy = 'created_at'
    actions = [export_as_csv, export_as_json]
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def action_badge(self, obj):
        a = getattr(obj, 'action', '')
        colors = {
            'CREATE': '#10b981', 'UPDATE': '#3b82f6', 'DELETE': '#ef4444',
            'LOGIN': '#8b5cf6', 'LOGOUT': '#64748b', 'VIEW': '#94a3b8',
            'EXPORT': '#f59e0b', 'IMPORT': '#22d3ee',
        }
        c = colors.get(a, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;'
            'background:{}22;color:{};font-weight:700;">{}</span>',
            c, c, a or '-'
        )
    action_badge.short_description = 'Action'

    def ip_display(self, obj):
        ip = getattr(obj, 'ip_address', '')
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;'
            'padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            ip or '-'
        )
    ip_display.short_description = 'IP'

    def severity_badge(self, obj):
        s = getattr(obj, 'severity', '')
        colors = {
            'LOW': '#10b981', 'MEDIUM': '#3b82f6',
            'HIGH': '#f59e0b', 'CRITICAL': '#ef4444',
        }
        c = colors.get(s, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;'
            'background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, s or '-'
        )
    severity_badge.short_description = 'Severity'

    def security_badge(self, obj):
        if getattr(obj, 'is_security_event', False):
            return format_html(
                '<span style="color:#ef4444;font-weight:700;">&#128274; Security</span>'
            )
        return format_html('<span style="color:#64748b;">-</span>')
    security_badge.short_description = 'Security'


# ═══════════════════════════════════════════════════════════════════
# 5. AUDIT & MONITORING — Behavior Events
# ═══════════════════════════════════════════════════════════════════

@admin.register(BehaviorEvent)
class BehaviorEventAdmin(EnhancedModelAdmin):
    list_display = (
        'timestamp_display', 'category_badge', 'event_action',
        'user_type_badge', 'user_id_short', 'ip_display',
        'anomaly_badge',
    )
    list_filter = ('event_category', 'user_type', 'is_anomalous')
    search_fields = ('user_id', 'event_action', 'ip_address')
    readonly_fields = [f.name for f in BehaviorEvent._meta.fields]
    date_hierarchy = 'occurred_at'
    list_per_page = 50
    actions = [export_as_csv, export_as_json]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def timestamp_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;">{}</span>',
            obj.occurred_at.strftime('%Y-%m-%d %H:%M:%S')
        )
    timestamp_display.short_description = 'Time'
    timestamp_display.admin_order_field = 'occurred_at'

    def category_badge(self, obj):
        cat_colors = {
            'AUTH': '#8b5cf6', 'NAVIGATION': '#3b82f6',
            'DATA_ACCESS': '#10b981', 'DATA_MODIFICATION': '#f59e0b',
            'EXPORT': '#ef4444', 'COMMUNICATION': '#22d3ee',
            'ASSESSMENT': '#6366f1', 'ATTENDANCE': '#ec4899',
            'ADMIN_ACTION': '#f97316', 'SYSTEM': '#64748b',
        }
        c = cat_colors.get(obj.event_category, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;">{}</span>',
            c, c, obj.event_category
        )
    category_badge.short_description = 'Category'

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': '#60a5fa', 'TEACHER': '#34d399',
            'ADMIN': '#fbbf24', 'PARENT': '#c084fc',
        }
        c = type_colors.get(obj.user_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, obj.user_type
        )
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;"'
            ' title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User'

    def ip_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;'
            'padding:2px 6px;background:rgba(99,102,241,0.06);border-radius:4px;">{}</span>',
            obj.ip_address or '-'
        )
    ip_display.short_description = 'IP'

    def anomaly_badge(self, obj):
        if obj.is_anomalous:
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
                'font-weight:700;color:#ef4444;background:rgba(239,68,68,0.12);">'
                '&#9888; {:.0f}%</span>',
                obj.anomaly_score * 100
            )
        return format_html(
            '<span style="color:#10b981;font-size:0.82rem;">Normal</span>'
        )
    anomaly_badge.short_description = 'Anomaly'


# ═══════════════════════════════════════════════════════════════════
# 6. COMPLIANCE
# ═══════════════════════════════════════════════════════════════════

@admin.register(ComplianceRule)
class ComplianceRuleAdmin(EnhancedModelAdmin):
    list_display = (
        'code', 'name', 'regulation_badge', 'requirements_summary',
        'enforcement_badge', 'active_badge', 'effective_period',
    )
    list_filter = ('regulation_type', 'is_active', 'auto_enforce')
    search_fields = ('code', 'name', 'description')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    fieldsets = (
        ('Rule Identity', {
            'fields': ('tenant', 'code', 'name', 'description'),
        }),
        ('Regulation', {
            'fields': ('regulation_type', 'applicable_data_types', 'applicable_user_types'),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>Supported Regulations:</strong> '
                'GDPR · FERPA · COPPA · IT Act (India) · DPDP Act (India) · Internal Policy<br>'
                '<strong>Data Types:</strong> JSON array e.g. '
                '<code>["personal_data", "academic_records", "financial_data"]</code>'
                '</div>'
            ),
        }),
        ('Requirements', {
            'fields': (
                'data_retention_days', 'requires_consent', 'requires_encryption',
                'requires_anonymization', 'requires_audit_trail',
            ),
        }),
        ('Enforcement', {
            'fields': ('auto_enforce', 'enforcement_action'),
        }),
        ('Validity Period', {
            'fields': ('effective_from', 'effective_until'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    def regulation_badge(self, obj):
        colors = {
            'GDPR': '#3b82f6', 'FERPA': '#8b5cf6', 'COPPA': '#ec4899',
            'IT_ACT': '#f59e0b', 'DPDP': '#10b981',
            'INTERNAL': '#64748b', 'CUSTOM': '#94a3b8',
        }
        c = colors.get(obj.regulation_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;">{}</span>',
            c, c, obj.get_regulation_type_display()
        )
    regulation_badge.short_description = 'Regulation'

    def requirements_summary(self, obj):
        icons = []
        if obj.requires_consent:
            icons.append('&#9989; Consent')
        if obj.requires_encryption:
            icons.append('&#128274; Encrypt')
        if obj.requires_anonymization:
            icons.append('&#128100; Anonymize')
        if obj.requires_audit_trail:
            icons.append('&#128221; Audit')
        return format_html(
            '<span style="font-size:0.78rem;color:#94a3b8;">{}</span>',
            ' · '.join(icons) if icons else 'None'
        )
    requirements_summary.short_description = 'Requirements'

    def enforcement_badge(self, obj):
        if obj.auto_enforce:
            return format_html(
                '<span style="color:#ef4444;font-weight:700;font-size:0.82rem;">'
                '&#9889; Auto</span>'
            )
        return format_html('<span style="color:#64748b;font-size:0.82rem;">Manual</span>')
    enforcement_badge.short_description = 'Enforce'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'

    def effective_period(self, obj):
        start = obj.effective_from.strftime('%d %b %Y') if obj.effective_from else '—'
        end = obj.effective_until.strftime('%d %b %Y') if obj.effective_until else '∞'
        return format_html(
            '<span style="color:#94a3b8;font-size:0.82rem;">{} → {}</span>',
            start, end
        )
    effective_period.short_description = 'Period'


@admin.register(ConsentRecord)
class ConsentRecordAdmin(EnhancedModelAdmin):
    list_display = (
        'consent_type', 'version', 'user_type_badge', 'user_id_short',
        'status_badge_consent', 'collection_method', 'granted_at',
    )
    list_filter = ('consent_type', 'is_granted', 'user_type', 'collection_method')
    search_fields = ('user_id', 'consent_type', 'consent_text')
    readonly_fields = ('granted_at',)
    date_hierarchy = 'granted_at'
    list_per_page = 50
    actions = [export_as_csv, export_as_json]

    fieldsets = (
        ('Consent Details', {
            'fields': ('tenant', 'consent_type', 'consent_text', 'version'),
        }),
        ('User', {
            'fields': ('user_id', 'user_type'),
        }),
        ('Status', {
            'fields': (
                'is_granted', 'granted_at', 'revoked_at',
                'ip_address', 'collection_method', 'expires_at',
            ),
        }),
    )

    def user_type_badge(self, obj):
        type_colors = {
            'STUDENT': '#60a5fa', 'TEACHER': '#34d399',
            'ADMIN': '#fbbf24', 'PARENT': '#c084fc',
        }
        c = type_colors.get(obj.user_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:600;color:{};background:{}22;">{}</span>',
            c, c, obj.user_type
        )
    user_type_badge.short_description = 'Type'

    def user_id_short(self, obj):
        short = str(obj.user_id)[:8]
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#94a3b8;"'
            ' title="{}">{}&hellip;</span>',
            obj.user_id, short
        )
    user_id_short.short_description = 'User'

    def status_badge_consent(self, obj):
        if obj.is_granted:
            return format_html(
                '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
                'font-weight:700;color:#10b981;background:rgba(16,185,129,0.12);">'
                '&#9989; Granted</span>'
            )
        return format_html(
            '<span style="padding:3px 8px;border-radius:5px;font-size:0.72rem;'
            'font-weight:700;color:#ef4444;background:rgba(239,68,68,0.12);">'
            '&#10060; Revoked</span>'
        )
    status_badge_consent.short_description = 'Consent'


@admin.register(DataAccessRequest)
class DataAccessRequestAdmin(EnhancedModelAdmin):
    list_display = (
        'request_type_badge', 'requester_email', 'user_type',
        'status_badge_dsar', 'requested_at', 'due_date_display',
    )
    list_filter = ('request_type', 'status', 'user_type')
    search_fields = ('requester_email', 'user_id', 'description')
    readonly_fields = ('requested_at',)
    date_hierarchy = 'requested_at'
    list_per_page = 30
    actions = [export_as_csv, export_as_json]

    fieldsets = (
        ('Request Details', {
            'fields': (
                'tenant', 'request_type', 'description', 'data_categories',
            ),
            'description': (
                '<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:0.85rem;color:#a5b4fc;">'
                '<strong>DSAR Types:</strong> '
                'Data Access · Rectification · Erasure (Right to be Forgotten) · '
                'Portability · Restrict Processing · Object to Processing<br>'
                'Regulatory deadline is typically 30 days from receipt.'
                '</div>'
            ),
        }),
        ('Requester', {
            'fields': ('user_id', 'user_type', 'requester_email'),
        }),
        ('Processing', {
            'fields': (
                'status', 'requested_at', 'due_date',
                'assigned_to', 'completed_at', 'response_notes',
            ),
        }),
    )

    def request_type_badge(self, obj):
        colors = {
            'ACCESS': '#3b82f6', 'RECTIFICATION': '#f59e0b',
            'ERASURE': '#ef4444', 'PORTABILITY': '#8b5cf6',
            'RESTRICTION': '#22d3ee', 'OBJECTION': '#ec4899',
        }
        c = colors.get(obj.request_type, '#94a3b8')
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;">{}</span>',
            c, c, obj.get_request_type_display()
        )
    request_type_badge.short_description = 'Type'

    def status_badge_dsar(self, obj):
        status_colors = {
            'RECEIVED': '#3b82f6', 'IDENTITY_VERIFICATION': '#f59e0b',
            'IN_PROGRESS': '#8b5cf6', 'COMPLETED': '#10b981',
            'REJECTED': '#ef4444', 'APPEALED': '#ec4899',
        }
        c = status_colors.get(obj.status, '#94a3b8')
        return format_html(
            '<span style="padding:3px 10px;border-radius:6px;font-size:0.72rem;'
            'font-weight:700;color:{};background:{}22;">{}</span>',
            c, c, obj.get_status_display()
        )
    status_badge_dsar.short_description = 'Status'

    def due_date_display(self, obj):
        if obj.due_date:
            now = timezone.now()
            if now > obj.due_date and obj.status not in ('COMPLETED', 'REJECTED'):
                return format_html(
                    '<span style="color:#ef4444;font-weight:700;font-size:0.82rem;">'
                    '&#9888; OVERDUE — {}</span>',
                    obj.due_date.strftime('%d %b %Y')
                )
            return format_html(
                '<span style="color:#94a3b8;font-size:0.82rem;">{}</span>',
                obj.due_date.strftime('%d %b %Y')
            )
        return format_html('<span style="color:#64748b;">—</span>')
    due_date_display.short_description = 'Due'


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(EnhancedModelAdmin):
    list_display = (
        'resource_type', 'retention_days', 'action_on_expiry', 'active_badge',
    )
    list_filter = ('is_active',)
    actions = [export_as_csv]

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))


# ═══════════════════════════════════════════════════════════════════════════════
# UNREGISTER SECURITY/AUDIT/COMPLIANCE MODELS FROM ADMIN SIDEBAR
# These are hidden from the main admin to reduce clutter - accessible via API only
# ═══════════════════════════════════════════════════════════════════════════════
try:
    admin.site.unregister(SecurityPolicy)
    admin.site.unregister(LoginAttemptLog)
    admin.site.unregister(TrustedDevice)
    admin.site.unregister(AccessLog)
    admin.site.unregister(AuditEntry)
    admin.site.unregister(BehaviorEvent)
    admin.site.unregister(ComplianceRule)
    admin.site.unregister(ConsentRecord)
    admin.site.unregister(DataAccessRequest)
    admin.site.unregister(RetentionPolicy)
except admin.sites.NotRegistered:
    pass
    active_badge.short_description = 'Active'

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM ADMIN ROLES (RBAC) — Permissions Matrix UI
# ═══════════════════════════════════════════════════════════════════════════════
from accounts.models import StaffRolePermission, UserStaffRole  # noqa: E402
from django.shortcuts import render, redirect  # noqa: E402
from django.urls import path as _path, reverse as _reverse  # noqa: E402
from django.contrib.admin.views.decorators import staff_member_required  # noqa: E402
from django.contrib.contenttypes.models import ContentType  # noqa: E402
from django.apps import apps as _apps  # noqa: E402


@admin.register(UserStaffRole)
class UserStaffRoleAdmin(EnhancedModelAdmin):
    """Assign Django auth users to a StaffRole."""
    list_display = ('user', 'role', 'is_active', 'assigned_at', 'note')
    list_filter = ('is_active', 'role')
    search_fields = ('user__username', 'user__email', 'role__name', 'note')
    autocomplete_fields = ('role',)
    readonly_fields = ('assigned_at',)
    list_per_page = 50


@admin.register(StaffRolePermission)
class StaffRolePermissionAdmin(EnhancedModelAdmin):
    """Per-(role, model) permission rows. Most users edit via the matrix UI."""
    list_display = (
        'role', 'app_label', 'model_name',
        'can_view', 'can_add', 'can_change', 'can_delete', 'can_export',
        'updated_at',
    )
    list_filter = ('can_view', 'can_add', 'can_change', 'can_delete', 'role')
    search_fields = ('role__name', 'app_label', 'model_name')
    list_per_page = 100

    change_list_template = 'admin/accounts/staffrolepermission/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            _path(
                'matrix/',
                self.admin_site.admin_view(staff_permissions_matrix_view),
                name='accounts_staffrolepermission_matrix',
            ),
        ]
        return custom + urls


# ── StaffRole admin already has search_fields above, autocomplete works ───────


# ─── Matrix UI ────────────────────────────────────────────────────────
# Lists all admin-registered models down the side, all StaffRoles across the
# top, and lets superusers tick view/add/change/delete/export per cell.

EXCLUDED_APPS = {'auth', 'contenttypes', 'sessions', 'admin', 'authtoken'}


def _matrix_models():
    """Yield (app_label, model_name, verbose_name) for every model registered in admin."""
    rows = []
    for model, model_admin in admin.site._registry.items():
        if model._meta.app_label in EXCLUDED_APPS:
            continue
        rows.append((
            model._meta.app_label,
            model._meta.model_name,
            f"{model._meta.app_config.verbose_name} → {model._meta.verbose_name_plural.title()}",
        ))
    rows.sort()
    return rows


def staff_permissions_matrix_view(request):
    """Read/edit per-(StaffRole × model) permissions in a single grid."""
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Only superusers can edit role permissions.')

    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        if not role_id:
            return redirect(request.path)
        # Build a quick lookup of submitted permissions
        # Form field name format: perm__<app>__<model>__<action> = '1'
        submitted = {}
        for key, value in request.POST.items():
            if not key.startswith('perm__'):
                continue
            try:
                _, app, model, action = key.split('__')
            except ValueError:
                continue
            slot = submitted.setdefault((app, model), {})
            slot[action] = (value == '1')
        # Apply
        from accounts.models import StaffRole as SR
        try:
            role = SR.objects.get(id=role_id)
        except SR.DoesNotExist:
            return redirect(request.path)
        for (app, model), actions in submitted.items():
            obj, _ = StaffRolePermission.objects.get_or_create(
                role=role, app_label=app, model_name=model,
            )
            obj.can_view = bool(actions.get('view'))
            obj.can_add = bool(actions.get('add'))
            obj.can_change = bool(actions.get('change'))
            obj.can_delete = bool(actions.get('delete'))
            obj.can_export = bool(actions.get('export'))
            # Drop entirely-empty rows to keep the table tidy
            if not any([obj.can_view, obj.can_add, obj.can_change, obj.can_delete, obj.can_export]):
                obj.delete()
            else:
                obj.save()
        from django.contrib import messages as _m
        _m.success(request, f"Permissions for '{role.name}' saved.")
        return redirect(f'{request.path}?role={role_id}')

    from accounts.models import StaffRole as SR
    roles = list(SR.objects.filter(is_active=True).order_by('name'))
    selected_role_id = request.GET.get('role') or (str(roles[0].id) if roles else '')
    selected_role = None
    perms = {}
    if selected_role_id:
        try:
            selected_role = SR.objects.get(id=selected_role_id)
            for p in StaffRolePermission.objects.filter(role=selected_role):
                perms[(p.app_label, p.model_name)] = p
        except SR.DoesNotExist:
            pass
    rows = _matrix_models()
    grouped = {}
    for app, model, label in rows:
        p = perms.get((app, model))
        cell = {
            'app': app,
            'model': model,
            'label': label,
            'view': bool(p and p.can_view),
            'add': bool(p and p.can_add),
            'change': bool(p and p.can_change),
            'delete': bool(p and p.can_delete),
            'export': bool(p and p.can_export),
        }
        grouped.setdefault(app, []).append(cell)
    grouped_rows = [
        {'app': app, 'cells': cells} for app, cells in sorted(grouped.items())
    ]
    context = {
        'title': 'Staff Permissions Matrix',
        'roles': roles,
        'selected_role': selected_role,
        'grouped_rows': grouped_rows,
        'opts': StaffRolePermission._meta,
        'has_permission': request.user.is_authenticated,
        **admin.site.each_context(request),
    }
    return render(request, 'admin/accounts/staff_permissions_matrix.html', context)
