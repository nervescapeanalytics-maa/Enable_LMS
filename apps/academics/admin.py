from django.contrib import admin
from django.utils.html import format_html
from academics.models import (
    AcademicSession, Group, Category, Subject, SubjectSection,
    Chapter, Topic, Batch, Users, BatchTeacher,
    Language, State, City, Religion, School,
)
from academics.forms import UsersAdminForm
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status


class UsersInline(admin.TabularInline):
    model = Users
    extra = 0
    fields = ('name', 'email', 'phone', 'is_active', 'enrolled_at')
    readonly_fields = ('enrolled_at',)
    show_change_link = True


class BatchTeacherInline(admin.TabularInline):
    model = BatchTeacher
    extra = 0
    fields = ('teacher', 'subject', 'is_primary')
    show_change_link = True


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ('name', 'class_level', 'display_order', 'status')
    show_change_link = True


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    fields = ('name', 'display_order', 'status')
    show_change_link = True


@admin.register(AcademicSession)
class AcademicSessionAdmin(EnhancedModelAdmin):
    list_display = ('session_name', 'current_badge', 'status_badge', 'start_date', 'end_date')
    list_filter = ('is_current', 'status')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'session_name'),
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
        }),
        ('Status', {
            'fields': ('is_current', 'status'),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def current_badge(self, obj):
        if obj.is_current:
            return format_html('<span style="color:#10b981;font-weight:700;">&#9679; Current</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    current_badge.short_description = 'Current'


@admin.register(Group)
class GroupAdmin(EnhancedModelAdmin):
    list_display = ('name', 'status_badge')
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name', 'description'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Category)
class CategoryAdmin(EnhancedModelAdmin):
    list_display = (
        'name', 'group', 'show_in_student', 'student_count',
        'status_badge', 'created_at',
    )
    list_display_links = ('name',)
    list_filter = ('status', 'show_in_student', 'group')
    search_fields = ('name', 'group__name')
    list_per_page = 50
    show_full_result_count = False
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name', 'group'),
        }),
        ('Visibility & status', {
            'fields': ('show_in_student', 'status'),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def student_count(self, obj):
        """Number of Students (modern FK) referencing this category."""
        try:
            from accounts.models import Student
            return Student.objects.filter(category=obj).count()
        except Exception:
            return 0
    student_count.short_description = 'Students'


@admin.register(Subject)
class SubjectAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('name', 'code', 'subject_type_badge', 'status_badge')
    list_filter = ('subject_type', 'status')
    search_fields = ('name', 'code')
    inlines = [ChapterInline]
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name', 'code', 'subject_type'),
        }),
        ('Content', {
            'fields': ('description',),
        }),
        ('Presentation', {
            'fields': ('display_order', 'color', 'icon_url'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def subject_type_badge(self, obj):
        colors = {'THEORY': '#3b82f6', 'PRACTICAL': '#10b981', 'BOTH': '#8b5cf6'}
        c = colors.get(getattr(obj, 'subject_type', ''), '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, getattr(obj, 'subject_type', '-')
        )
    subject_type_badge.short_description = 'Type'


@admin.register(Chapter)
class ChapterAdmin(EnhancedModelAdmin):
    list_display = ('name', 'subject', 'class_level', 'display_order', 'status_badge')
    list_filter = ('subject', 'status')
    search_fields = ('name',)
    inlines = [TopicInline]
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'subject', 'name', 'code'),
        }),
        ('Academic', {
            'fields': ('class_level', 'description', 'display_order', 'estimated_hours', 'weightage'),
        }),
        ('Organization', {
            'fields': ('group', 'session'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Topic)
class TopicAdmin(EnhancedModelAdmin):
    list_display = ('name', 'chapter', 'display_order', 'status_badge')
    list_filter = ('status',)
    search_fields = ('name',)
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'chapter', 'name', 'code'),
        }),
        ('Content', {
            'fields': ('description',),
        }),
        ('Ordering & weight', {
            'fields': ('display_order', 'weightage'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Batch)
class BatchAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = (
        'code', 'name', 'class_level', 'exam_target',
        'enrolled_count', 'status_badge', 'start_date', 'end_date',
    )
    list_filter = ('status', 'exam_target', 'class_level')
    search_fields = ('code', 'name')
    inlines = [BatchTeacherInline]
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = ('id', 'created_at', 'updated_at', 'enrolled_count')
    list_per_page = 50
    show_full_result_count = False

    META_EXAMPLE = (
        '{\n'
        '  "room": "Lab-2",\n'
        '  "timing": "Mon-Fri 18:00-20:00",\n'
        '  "fee_plan": "annual",\n'
        '  "tags": ["scholarship", "foundation"]\n'
        '}'
    )

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name', 'code', 'description'),
        }),
        ('Academic Details', {
            'fields': ('class_level', 'exam_target'),
        }),
        ('Organization', {
            'fields': ('group', 'session'),
            'description': (
                '<div style="background:rgba(132,79,193,0.08);border:1px solid rgba(132,79,193,0.25);'
                'border-radius:8px;padding:10px 14px;margin:6px 0;font-size:0.82rem;color:#6D28D9;">'
                '<strong>Group</strong> lets you cluster related batches under a common label '
                '(e.g. <code>JEE Mains Weekday</code>, <code>NEET Dropper</code>, '
                '<code>Foundation IX-X</code>). Reports, notifications and fee plans can then be '
                'driven at the group level instead of per batch — useful when you run multiple '
                'parallel sections that share curriculum, teachers or pricing.</div>'
            ),
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'enrolled_count'),
            'description': 'Live enrolment count is read from the Student table.',
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Metadata (optional free-form JSON)', {
            'fields': ('meta_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': (
                '<div style="background:rgba(132,79,193,0.06);border:1px solid rgba(132,79,193,0.18);'
                'border-radius:8px;padding:10px 14px;margin:6px 0;font-size:0.82rem;color:#475569;">'
                '<strong>Metadata</strong> accepts a JSON object for anything that does not fit the '
                'structured fields above. Suggested keys: '
                '<code>room</code>, <code>timing</code>, <code>fee_plan</code>, <code>tags</code>. '
                'Example:<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;'
                'margin-top:8px;font-size:0.75rem;">' + META_EXAMPLE + '</pre></div>'
            ),
        }),
        # 'teachers' M2M managed via BatchTeacher inline.
        # 'max_students' and extension slots intentionally hidden from the form.
    )

    def enrolled_count(self, obj):
        """Live enrolment count.

        Unifies the legacy `academics.Users` table (where the 40k+ historic
        enrolments live, related_name='users') with the modern
        `accounts.Student` FK. Whichever side has data wins — if both do, we
        sum them so nothing is under-counted.
        """
        try:
            legacy = obj.users.filter(is_active=True).count()
        except Exception:
            legacy = 0
        try:
            from accounts.models import Student
            modern = Student.objects.filter(batch=obj).exclude(status='INACTIVE').count()
        except Exception:
            modern = 0
        total = legacy + modern
        color = '#6D28D9' if total else '#94a3b8'
        return format_html(
            '<span style="font-weight:700;color:{};">{}</span>'
            '<span style="color:#64748b;font-size:0.75rem;"> students</span>',
            color, total,
        )
    enrolled_count.short_description = 'Enrolled'


@admin.register(Users)
class UsersAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = UsersAdminForm
    list_display = (
        'uid', 'name', 'father_name', 'batch', 'category',
        'email', 'phone', 'phone1', 'gender', 'dob',
        'city_name', 'userid', 'active_badge', 'enrolled_at',
    )
    list_display_links = ('uid', 'name')
    list_filter = ('is_active', 'batch', 'gender', 'category', 'handicapped')
    search_fields = (
        'name', 'father_name', 'email', 'phone', 'phone1',
        'userid', 'batch__name', 'city_name',
    )
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'uid', 'enrolled_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'batch'),
        }),
        ('Student Profile', {
            'fields': ('uid', 'name', 'father_name', 'dob', 'gender',
                       'phone', 'phone1', 'email', 'userid'),
        }),
        ('Academic & Location', {
            'fields': ('school_id', 'state_id', 'city_id', 'city_name',
                       'previous_class_marks', 'other_school'),
        }),
        ('Status & Accessibility', {
            'fields': ('category', 'tps', 'handicapped', 'is_active'),
        }),
    )

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'


@admin.register(BatchTeacher)
class BatchTeacherAdmin(EnhancedModelAdmin):
    list_display = (
        'teacher', 'teacher_email', 'teacher_phone',
        'batch', 'subject', 'primary_badge', 'assigned_at',
    )
    list_display_links = ('teacher',)
    list_filter = ('is_primary', 'batch', 'subject')
    search_fields = (
        'teacher__first_name', 'teacher__last_name', 'teacher__email',
        'teacher__phone', 'teacher__teacher_code',
        'batch__name', 'batch__code', 'subject__name',
    )
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv]
    readonly_fields = ('id', 'assigned_at')

    def teacher_email(self, obj):
        return getattr(obj.teacher, 'email', '-') if obj.teacher_id else '-'
    teacher_email.short_description = 'Email'
    teacher_email.admin_order_field = 'teacher__email'

    def teacher_phone(self, obj):
        return getattr(obj.teacher, 'phone', '-') if obj.teacher_id else '-'
    teacher_phone.short_description = 'Phone'
    teacher_phone.admin_order_field = 'teacher__phone'
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'batch', 'teacher', 'subject'),
        }),
        ('Assignment', {
            'fields': ('is_primary', 'assigned_at'),
        }),
    )

    def primary_badge(self, obj):
        if obj.is_primary:
            return format_html('<span style="color:#f59e0b;font-weight:700;">&#9733; Primary</span>')
        return format_html('<span style="color:#64748b;">-</span>')
    primary_badge.short_description = 'Primary'


@admin.register(Language)
class LanguageAdmin(EnhancedModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_display_links = ('name',)
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv]
    fields = ('id', 'name', 'code', 'is_active')
    readonly_fields = ('id',)


@admin.register(State)
class StateAdmin(EnhancedModelAdmin):
    list_display = ('name', 'code')
    list_display_links = ('name',)
    search_fields = ('name', 'code')
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv]
    fields = ('id', 'name', 'code')
    readonly_fields = ('id',)


@admin.register(City)
class CityAdmin(EnhancedModelAdmin):
    list_display = ('name', 'state', 'state_code')
    list_display_links = ('name',)
    list_filter = ('state',)
    search_fields = ('name', 'state__name', 'state__code')
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv]
    fields = ('id', 'name', 'state')
    readonly_fields = ('id',)

    def state_code(self, obj):
        return getattr(obj.state, 'code', '-') if obj.state_id else '-'
    state_code.short_description = 'State Code'
    state_code.admin_order_field = 'state__code'


@admin.register(Religion)
class ReligionAdmin(EnhancedModelAdmin):
    list_display = ('name', 'status')
    search_fields = ('name',)
    actions = [export_as_csv]
    fields = ('id', 'name', 'status')
    readonly_fields = ('id',)


@admin.register(SubjectSection)
class SubjectSectionAdmin(EnhancedModelAdmin):
    list_display = ('name', 'subject', 'status')
    list_filter = ('status', 'subject')
    search_fields = ('name',)
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'subject', 'name', 'status'),
        }),
        ('Metadata', {
            'fields': ('meta_data', 'created_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(School)
class SchoolAdmin(ImportExportMixin, EnhancedModelAdmin):
    # Requested columns: State, City/Village, District (city FK), School Name.
    list_display = ('state', 'city_village', 'district', 'name')
    list_display_links = ('name',)
    list_filter = ('state',)
    search_fields = ('name', 'city_name', 'city__name', 'state__name')
    list_per_page = 50
    show_full_result_count = False
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name'),
        }),
        ('Location', {
            'fields': ('state', 'city', 'city_name'),
            'description': (
                '<strong>City</strong> (FK) = the district / registered city. '
                '<strong>City/Village</strong> is free-text for the specific locality.'
            ),
        }),
        ('Classification (optional)', {
            'fields': ('school_type', 'religion', 'status', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def city_village(self, obj):
        return obj.city_name or '—'
    city_village.short_description = 'City / Village'
    city_village.admin_order_field = 'city_name'

    def district(self, obj):
        return obj.city.name if obj.city_id else '—'
    district.short_description = 'District'
    district.admin_order_field = 'city__name'
