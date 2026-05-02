from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from assessments.models import (
    Test, TestSection, Question, TestAttempt,
    TestAttemptAnswer, TestFeedback, OfflineTestMarks
)
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status
from assessments.permissions import (
    can_manage_exams, is_admin_full, get_logged_in_admin,
)
from assessments import importers as _exam_importers


def _export_zip_action(modeladmin, request, queryset):
    """Admin action: export the parent Test(s) of selected sections as ZIP."""
    test_ids = list(queryset.values_list('test_id', flat=True).distinct())
    if not test_ids:
        messages.error(request, 'No tests resolved from the selection.')
        return None
    if len(test_ids) > 1:
        messages.error(request, 'Pick sections from a single Test to export. (Got {} tests.)'.format(len(test_ids)))
        return None
    test = Test.objects.get(id=test_ids[0])
    blob = _exam_importers.export_test_zip(test)
    safe = (test.test_code or 'test').replace('/', '_').replace(' ', '_')
    resp = HttpResponse(blob, content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="{safe}_questions.zip"'
    return resp
_export_zip_action.short_description = 'Export ZIP (questions + images) for the parent Test'


def _export_zip_test_action(modeladmin, request, queryset):
    """Admin action on Test: export selected Test as ZIP."""
    if queryset.count() != 1:
        messages.error(request, 'Pick exactly one test to export.')
        return None
    test = queryset.first()
    blob = _exam_importers.export_test_zip(test)
    safe = (test.test_code or 'test').replace('/', '_').replace(' ', '_')
    resp = HttpResponse(blob, content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="{safe}_questions.zip"'
    return resp
_export_zip_test_action.short_description = 'Export ZIP (questions + images)'


class ExamRBACMixin:
    """
    Phase 1 RBAC for exam-related admin pages.

    * Teachers: blocked from view/add/change/delete (defense-in-depth; teachers
      do not normally have Django admin login, but if they ever did via a
      permissions misconfiguration, they would still be locked out here).
    * Students: blocked.
    * Staff (admin row WITH staff_role): can view + change + add IF the
      staff_role has can_manage_exams = True. Cannot delete.
    * Admin (admin row WITHOUT staff_role, or SUPER_ADMIN): full access.
    """
    def _exam_has_access(self, request, write: bool = False) -> bool:
        sess_type = request.session.get('user_type')
        # Allow legacy Django superuser logins through (request.user)
        if getattr(request.user, 'is_superuser', False):
            return True
        if sess_type in (None, '', 'TEACHER', 'STUDENT'):
            return False
        admin_user = get_logged_in_admin(request)
        if admin_user is None:
            return False
        if is_admin_full(admin_user):
            return True
        return can_manage_exams(admin_user)

    def has_view_permission(self, request, obj=None):
        return self._exam_has_access(request)

    def has_add_permission(self, request):
        return self._exam_has_access(request, write=True)

    def has_change_permission(self, request, obj=None):
        return self._exam_has_access(request, write=True)

    def has_delete_permission(self, request, obj=None):
        # Only full admin can delete
        if getattr(request.user, 'is_superuser', False):
            return True
        admin_user = get_logged_in_admin(request)
        return is_admin_full(admin_user)

    def has_module_permission(self, request):
        return self._exam_has_access(request)


class TestSectionInline(admin.TabularInline):
    model = TestSection
    extra = 0
    fields = ('section_name', 'section_order', 'total_questions', 'max_marks')
    show_change_link = True


@admin.register(Test)
class TestAdmin(ExamRBACMixin, ImportExportMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = (
        'test_code', 'title', 'type_badge', 'exam_target',
        'status_badge', 'total_marks', 'duration_display', 'start_datetime',
    )
    list_filter = ('status', 'test_type', 'exam_target', 'difficulty_level')
    search_fields = ('test_code', 'title')
    date_hierarchy = 'start_datetime'
    inlines = [TestSectionInline]
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected, _export_zip_test_action]
    readonly_fields = ('id', 'created_at', 'updated_at', 'published_at')
    fieldsets = (
        ('Identification', {
            'fields': (
                'id', 'tenant', 'test_code', 'title', 'description', 'test_type', 'exam_target',
                'difficulty_level', 'subject', 'chapter', 'batch', 'teacher', 'created_by',
                'created_by_type', 'status', 'instructions', 'total_questions',
            ),
        }),
        ('Scoring', {
            'fields': (
                'total_marks', 'total_duration_minutes', 'passing_marks', 'passing_percent',
                'positive_marks_per_question', 'negative_marks_per_question', 'partial_marking',
                'max_attempts',
            ),
        }),
        ('Schedule & access', {
            'fields': (
                'start_datetime', 'end_datetime', 'buffer_time_minutes', 'access_mode',
                'access_password', 'show_timer',
            ),
        }),
        ('Results display', {
            'fields': (
                'show_correct_answers', 'show_explanations', 'show_rank', 'show_percentile',
                'result_display_mode', 'result_release_datetime',
            ),
        }),
        ('Question presentation', {
            'fields': (
                'shuffle_questions', 'shuffle_options', 'allow_backward', 'allow_review',
            ),
        }),
        ('Proctoring', {
            'fields': (
                'prevent_tab_switch', 'max_tab_switches', 'prevent_copy_paste',
                'prevent_screenshot', 'full_screen_required', 'enable_proctoring',
                'webcam_required',
            ),
        }),
        ('Late submission', {
            'fields': ('late_submission_allowed', 'late_submission_penalty_percent'),
        }),
        ('Lifecycle & extensions', {
            'fields': (
                'is_deleted', 'published_at', 'published_by', 'test_meta',
                'ext_test_1', 'ext_test_2', 'ext_test_3', 'ext_test_4', 'ext_test_5',
                'created_at', 'updated_at',
            ),
        }),
    )

    def type_badge(self, obj):
        colors = {
            'PRACTICE': '#3b82f6', 'MOCK': '#8b5cf6', 'LIVE': '#ef4444',
            'ASSIGNMENT': '#f59e0b', 'QUIZ': '#10b981',
        }
        c = colors.get(getattr(obj, 'test_type', ''), '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, getattr(obj, 'test_type', '-')
        )
    type_badge.short_description = 'Type'

    def duration_display(self, obj):
        mins = getattr(obj, 'duration_minutes', None)
        if mins:
            h, m = divmod(mins, 60)
            if h:
                return format_html('<span style="color:#94a3b8;">{}h {}m</span>', h, m)
            return format_html('<span style="color:#94a3b8;">{}m</span>', m)
        return '-'
    duration_display.short_description = 'Duration'


@admin.register(TestSection)
class TestSectionAdmin(ExamRBACMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    change_list_template = 'admin/assessments/testsection_changelist.html'
    list_display = ('test', 'section_name', 'section_order', 'total_questions', 'max_marks')
    list_filter = ('test',)
    actions = [export_as_csv, _export_zip_action]
    readonly_fields = ('id',)
    fieldsets = (
        (None, {
            'fields': (
                'id', 'tenant', 'test', 'section_name', 'section_order', 'total_questions',
                'mandatory_questions', 'max_marks', 'duration_minutes', 'instructions', 'subject',
            ),
        }),
    )


@admin.register(Question)
class QuestionAdmin(ExamRBACMixin, ImportExportMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = (
        'question_code', 'type_badge', 'difficulty_badge',
        'batch_display', 'subject', 'topic', 'test', 'active_badge',
    )
    list_filter = ('question_type', 'difficulty', 'is_active', 'subject', 'topic', 'test__batch')
    search_fields = ('question_code', 'question_text', 'topic__name', 'test__batch__name')
    list_select_related = ('subject', 'topic', 'test', 'test__batch')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    list_per_page = 30
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'total_attempts', 'correct_attempts',
        'success_rate', 'average_time_seconds',
    )
    fieldsets = (
        ('Links & identity', {
            'fields': (
                'id', 'tenant', 'test', 'section', 'subject', 'chapter', 'topic',
                'question_code', 'question_type', 'difficulty',
            ),
        }),
        ('Content', {
            'fields': (
                'question_text', 'question_text_html', 'question_image',
                'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
                'option_a_image', 'option_b_image', 'option_c_image', 'option_d_image',
                'option_e_image',
            ),
        }),
        ('Answer & scoring', {
            'fields': (
                'correct_answer', 'correct_answer_value', 'numerical_tolerance',
                'answer_explanation', 'positive_marks', 'negative_marks', 'partial_marks',
            ),
        }),
        ('Structure & state', {
            'fields': (
                'question_order', 'parent_question', 'tags', 'is_active', 'is_deleted',
            ),
        }),
        ('Statistics', {
            'fields': (
                'total_attempts', 'correct_attempts', 'success_rate', 'average_time_seconds',
            ),
        }),
        ('Extensions', {
            'fields': (
                'question_meta', 'ext_question_1', 'ext_question_2', 'ext_question_3',
                'created_at', 'updated_at',
            ),
        }),
    )

    def type_badge(self, obj):
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:rgba(99,102,241,0.1);color:#a5b4fc;font-weight:600;">{}</span>',
            getattr(obj, 'question_type', '-')
        )
    type_badge.short_description = 'Type'

    def difficulty_badge(self, obj):
        colors = {'EASY': '#10b981', 'MEDIUM': '#f59e0b', 'HARD': '#ef4444'}
        d = getattr(obj, 'difficulty', '')
        c = colors.get(d, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;background:{}22;color:{};font-weight:600;">{}</span>',
            c, c, d or '-'
        )
    difficulty_badge.short_description = 'Difficulty'

    def active_badge(self, obj):
        return colored_status(obj.is_active)
    active_badge.short_description = 'Active'

    def batch_display(self, obj):
        b = getattr(getattr(obj, 'test', None), 'batch', None)
        return getattr(b, 'name', '—') if b else '—'
    batch_display.short_description = 'Batch'
    batch_display.admin_order_field = 'test__batch__name'


# Note: TestAttempt and TestAttemptAnswer are intentionally NOT registered with
# the Django admin (per product requirement — these are operational records,
# not authoring artefacts). The classes below are kept for code reference but
# never call `admin.site.register()` on them.
class TestAttemptAdmin(ExamRBACMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = (
        'test', 'student', 'attempt_number', 'status_badge',
        'score_display', 'percentage_display', 'result_badge',
    )
    list_filter = ('status', 'result')
    search_fields = ('student__first_name', 'student__last_name', 'test__title')
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'started_at', 'submitted_at')
    fieldsets = (
        ('Core', {
            'fields': (
                'id', 'tenant', 'test', 'student', 'attempt_number', 'status',
            ),
        }),
        ('Timing', {
            'fields': (
                'started_at', 'submitted_at', 'time_taken_seconds', 'remaining_time_seconds',
                'time_limit_reached',
            ),
        }),
        ('Progress & scores', {
            'fields': (
                'total_questions', 'attempted', 'correct', 'incorrect', 'skipped',
                'marked_for_review', 'raw_score', 'total_marks', 'percentage', 'percentile',
                'rank', 'result', 'section_scores',
            ),
        }),
        ('Proctoring & device', {
            'fields': (
                'tab_switch_count', 'copy_paste_attempts', 'proctoring_violations',
                'auto_terminated', 'termination_reason', 'ip_address', 'user_agent',
                'device_id',
            ),
        }),
        ('Extensions', {
            'fields': ('attempt_meta', 'ext_attempt_1', 'ext_attempt_2'),
        }),
    )

    def score_display(self, obj):
        return format_html(
            '<span style="font-weight:700;color:#1e293b;">{}</span>',
            getattr(obj, 'raw_score', '-')
        )
    score_display.short_description = 'Score'

    def percentage_display(self, obj):
        pct = getattr(obj, 'percentage', None)
        if pct is not None:
            color = '#10b981' if pct >= 60 else '#f59e0b' if pct >= 33 else '#ef4444'
            return format_html(
                '<span style="font-weight:700;color:{};">{}%</span>', color, pct
            )
        return '-'
    percentage_display.short_description = '%'

    def result_badge(self, obj):
        r = getattr(obj, 'result', '')
        if r:
            return colored_status(r)
        return '-'
    result_badge.short_description = 'Result'


class TestAttemptAnswerAdmin(ExamRBACMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = ('attempt', 'question', 'status_badge', 'correct_badge', 'marks_awarded', 'time_spent_seconds')
    list_filter = ('status', 'is_correct')
    actions = [export_as_csv]
    readonly_fields = ('id',)
    fieldsets = (
        (None, {
            'fields': (
                'id', 'tenant', 'attempt', 'question',
                'student_answer', 'student_answer_text', 'student_answer_value',
                'is_correct', 'marks_awarded', 'status', 'time_spent_seconds',
                'visit_count', 'first_answered_at', 'last_answered_at', 'answer_change_count',
                'answer_meta',
            ),
        }),
    )

    def correct_badge(self, obj):
        return colored_status(obj.is_correct)
    correct_badge.short_description = 'Correct'


@admin.register(TestFeedback)
class TestFeedbackAdmin(ExamRBACMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = ('test', 'student', 'overall_rating', 'difficulty_rating')
    actions = [export_as_csv]
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': (
                'id', 'tenant', 'test', 'student', 'attempt',
                'overall_rating', 'difficulty_rating', 'clarity_rating', 'comments',
                'created_at',
            ),
        }),
    )


@admin.register(OfflineTestMarks)
class OfflineTestMarksAdmin(ExamRBACMixin, ImportExportMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    list_display = ('student', 'test_name', 'test_date', 'marks_obtained', 'total_marks', 'percentage_display')
    actions = [export_as_csv, export_as_json]
    readonly_fields = ('id', 'entered_at', 'verified_at')
    fieldsets = (
        (None, {
            'fields': (
                'id', 'tenant', 'student', 'subject', 'test_name', 'test_date',
                'marks_obtained', 'total_marks', 'percentage', 'grade', 'remarks',
                'entered_by', 'entered_at', 'verified_by', 'verified_at',
            ),
        }),
    )

    def percentage_display(self, obj):
        pct = getattr(obj, 'percentage', None)
        if pct is not None:
            color = '#10b981' if pct >= 60 else '#f59e0b' if pct >= 33 else '#ef4444'
            return format_html('<span style="font-weight:700;color:{};">{}%</span>', color, pct)
        return '-'
    percentage_display.short_description = '%'
