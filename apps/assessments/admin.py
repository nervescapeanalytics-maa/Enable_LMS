from django.contrib import admin
from django import forms
from django.http import HttpResponse
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from assessments.models import (
    Test, TestSection, Question, TestAttempt,
    TestAttemptAnswer, TestFeedback, OfflineTestMarks
)


# ---------------------------------------------------------------------------
# Section name suggestions (presented as a datalist-backed dropdown so admins
# can either pick a common subject or type a custom value).
# ---------------------------------------------------------------------------
SECTION_NAME_CHOICES = [
    'Mathematics',
    'Physics',
    'Chemistry',
    'Biology',
    'Botany',
    'Zoology',
    'English',
    'Logical Reasoning',
    'Quantitative Aptitude',
    'General Knowledge',
    'Computer Science',
    'Section A',
    'Section B',
    'Section C',
]


class _SectionNameSelectWidget(forms.TextInput):
    """Free-text input bound to a <datalist> for autosuggest dropdown."""

    def render(self, name, value, attrs=None, renderer=None):
        from django.utils.safestring import mark_safe
        attrs = (attrs or {}).copy()
        attrs.setdefault('list', 'lms-section-names')
        attrs.setdefault('placeholder', 'Pick or type — Mathematics, Physics, …')
        html = super().render(name, value, attrs, renderer)
        opts = ''.join(f'<option value="{c}">' for c in SECTION_NAME_CHOICES)
        return mark_safe(f'{html}<datalist id="lms-section-names">{opts}</datalist>')


class TestSectionAdminForm(forms.ModelForm):
    class Meta:
        model = TestSection
        fields = '__all__'
        widgets = {'section_name': _SectionNameSelectWidget()}


# Help text describing JSON test_meta use cases — surfaced in the admin form.
TEST_META_HELP = (
    'JSON metadata for this test. Common use cases:\n'
    '  • {"category": "mock_test", "round": 1}\n'
    '  • {"category": "practice_test", "topic_focus": "kinematics"}\n'
    '  • {"category": "sectional_test", "subject": "physics"}\n'
    '  • {"category": "full_length", "exam": "JEE_MAIN"}\n'
    '  • {"category": "diagnostic", "purpose": "baseline"}\n'
    'Used by analytics + AI insights to classify and benchmark.'
)

# Predefined categories shown as a dropdown — mapped to test_meta['category'].
TEST_META_CATEGORY_CHOICES = [
    ('', '— Not set —'),
    ('mock_test', 'Mock Test (full-pattern simulation)'),
    ('practice_test', 'Practice Test (skill drills)'),
    ('sectional_test', 'Sectional Test (single subject)'),
    ('full_length', 'Full-Length Paper (full pattern)'),
    ('diagnostic', 'Diagnostic Test (baseline / placement)'),
    ('chapter_test', 'Chapter Test (topic mastery)'),
    ('weekly_test', 'Weekly Test (recurring)'),
    ('revision', 'Revision (recap)'),
    ('previous_year', 'Previous-Year Paper'),
]


class TestAdminForm(forms.ModelForm):
    """Replaces the raw JSON `test_meta` textarea with a friendly dropdown.

    The dropdown maps to `test_meta['category']`. Other keys in `test_meta`
    (e.g. `subject`, `round`, `exam`) are preserved untouched.
    """

    test_meta_category = forms.ChoiceField(
        required=False,
        choices=TEST_META_CATEGORY_CHOICES,
        label='Test category (test_meta)',
        help_text='Select the test category. Stored under test_meta["category"].',
    )

    class Meta:
        model = Test
        fields = '__all__'
        exclude = ('test_meta',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = (self.instance.test_meta or {}) if self.instance else {}
        if isinstance(existing, dict):
            self.fields['test_meta_category'].initial = existing.get('category', '')

    def save(self, commit=True):
        instance = super().save(commit=False)
        meta = instance.test_meta if isinstance(instance.test_meta, dict) else {}
        cat = self.cleaned_data.get('test_meta_category') or ''
        if cat:
            meta['category'] = cat
        else:
            meta.pop('category', None)
        instance.test_meta = meta or None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
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
    form = TestSectionAdminForm
    extra = 0
    fields = ('section_name', 'section_order', 'total_questions', 'max_marks')
    show_change_link = True


@admin.register(Test)
class TestAdmin(ExamRBACMixin, ImportExportMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    form = TestAdminForm
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
                'is_deleted', 'published_at', 'published_by', 'test_meta_category',
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'test_meta' and formfield is not None:
            formfield.help_text = TEST_META_HELP
        return formfield

    def save_formset(self, request, form, formset, change):
        """Auto-populate tenant on inline TestSection rows from the parent Test.

        The admin form does not expose a `tenant` field on the inline, so new
        sections would otherwise hit a NotNullViolation on save.
        """
        instances = formset.save(commit=False)
        parent_tenant_id = getattr(form.instance, 'tenant_id', None)
        for obj in instances:
            if isinstance(obj, TestSection) and not obj.tenant_id and parent_tenant_id:
                obj.tenant_id = parent_tenant_id
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


@admin.register(TestSection)
class TestSectionAdmin(ExamRBACMixin, EnhancedModelAdmin):
    enf_hide_tools = True
    form = TestSectionAdminForm
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

    # ------------------------------------------------------------------
    # Custom admin URLs: direct ZIP export + ZIP import (no /staff/ redirect)
    # ------------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('export-zip/', self.admin_site.admin_view(self.export_zip_view),
                 name='assessments_testsection_export_zip'),
            path('import-zip/', self.admin_site.admin_view(self.import_zip_view),
                 name='assessments_testsection_import_zip'),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        # Inject the list of tests into the changelist context so the
        # toolbar's Export/Import dropdowns can be populated inline.
        extra_context = extra_context or {}
        extra_context['available_tests'] = (
            Test.objects.filter(is_deleted=False)
            .order_by('-created_at')
            .values('id', 'test_code', 'title')[:300]
        )
        # Recent ZIP import history (latest 15) for the inline panel
        try:
            from .models import ZipImportLog
            extra_context['zip_import_history'] = list(
                ZipImportLog.objects.select_related('test')
                .order_by('-uploaded_at')[:15]
            )
        except Exception:
            extra_context['zip_import_history'] = []
        return super().changelist_view(request, extra_context=extra_context)

    def export_zip_view(self, request):
        """Stream a ZIP for the selected test directly — no redirect."""
        if not self._exam_has_access(request, write=False):
            return HttpResponse('Forbidden', status=403)
        test_id = request.POST.get('test_id') or request.GET.get('test_id')
        if not test_id:
            messages.error(request, 'Pick a test to export.')
            return redirect('admin:assessments_testsection_changelist')
        try:
            test = Test.objects.get(id=test_id, is_deleted=False)
        except Test.DoesNotExist:
            messages.error(request, 'Test not found.')
            return redirect('admin:assessments_testsection_changelist')
        try:
            blob = _exam_importers.export_test_zip(test)
        except Exception as e:  # noqa: BLE001
            messages.error(request, f'Export failed: {e}')
            return redirect('admin:assessments_testsection_changelist')
        safe = (test.test_code or 'test').replace('/', '_').replace(' ', '_')
        resp = HttpResponse(blob, content_type='application/zip')
        resp['Content-Disposition'] = f'attachment; filename="{safe}_questions.zip"'
        return resp

    def import_zip_view(self, request):
        """Accept a ZIP upload + target test inline — no redirect to /staff/."""
        if not self._exam_has_access(request, write=True):
            return HttpResponse('Forbidden', status=403)
        if request.method != 'POST':
            messages.error(request, 'Use the Import ZIP form.')
            return redirect('admin:assessments_testsection_changelist')
        test_id = request.POST.get('test_id')
        f = request.FILES.get('file')
        if not test_id or not f:
            messages.error(request, 'Both a target test and a ZIP file are required.')
            return redirect('admin:assessments_testsection_changelist')
        try:
            test = Test.objects.get(id=test_id, is_deleted=False)
        except Test.DoesNotExist:
            messages.error(request, 'Test not found.')
            return redirect('admin:assessments_testsection_changelist')

        from .models import ZipImportLog
        actor = get_logged_in_admin(request) or request.user
        actor_label = getattr(actor, 'email', None) or getattr(actor, 'username', None) or str(actor)
        actor_id = getattr(actor, 'id', None)
        log_kwargs = dict(
            tenant=test.tenant, test=test,
            file_name=getattr(f, 'name', 'upload.zip')[:255],
            file_size_bytes=getattr(f, 'size', 0) or 0,
            uploaded_by=actor_id if isinstance(actor_id, (int, str)) and len(str(actor_id)) <= 36 else None,
            uploaded_by_label=str(actor_label)[:200],
        )
        try:
            ext = (f.name.rsplit('.', 1)[-1] if '.' in f.name else '').lower()
            if ext != 'zip':
                ZipImportLog.objects.create(
                    status=ZipImportLog.Status.REJECTED,
                    error_message='File must be a .zip archive.', **log_kwargs)
                messages.error(request, 'File must be a .zip archive.')
                return redirect('admin:assessments_testsection_changelist')
            rows = _exam_importers.parse_zip_with_assets(f)
            cleaned, errors = _exam_importers.validate_rows(
                rows, test=test, tenant=test.tenant,
            )
            if errors:
                ZipImportLog.objects.create(
                    status=ZipImportLog.Status.REJECTED,
                    rows_total=len(rows),
                    error_message=f'{len(errors)} validation error(s). First: {errors[0].get("message", "?")[:500]}',
                    **log_kwargs)
                messages.error(
                    request,
                    f'Import rejected — {len(errors)} validation error(s). '
                    f'First: {errors[0].get("message", "?")}',
                )
                return redirect('admin:assessments_testsection_changelist')
            result = _exam_importers.apply_rows(
                cleaned, test=test, tenant=test.tenant,
                actor=actor, request=request,
            )
            ZipImportLog.objects.create(
                status=ZipImportLog.Status.SUCCESS,
                rows_total=result.get('total', 0),
                rows_created=result.get('created', 0),
                rows_updated=result.get('updated', 0),
                **log_kwargs)
            messages.success(
                request,
                f'Imported {result["total"]} questions into "{test.title}" '
                f'({result["created"]} new, {result["updated"]} updated).',
            )
        except Exception as e:  # noqa: BLE001
            try:
                ZipImportLog.objects.create(
                    status=ZipImportLog.Status.FAILED,
                    error_message=str(e)[:1000], **log_kwargs)
            except Exception:
                pass
            messages.error(request, f'Import failed: {e}')
        return redirect('admin:assessments_testsection_changelist')


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


# ---------------------------------------------------------------------------
# ZIP Import History — read-only admin (visible under Exams & Assessments)
# ---------------------------------------------------------------------------
from .models import ZipImportLog


@admin.register(ZipImportLog)
class ZipImportLogAdmin(EnhancedModelAdmin):
    list_display = ('file_name', 'test', 'status_badge', 'rows_total',
                    'rows_created', 'rows_updated', 'uploaded_by_label',
                    'uploaded_at')
    list_filter = ('status', 'uploaded_at')
    search_fields = ('file_name', 'uploaded_by_label', 'test__test_code', 'test__title')
    readonly_fields = tuple(
        f.name for f in ZipImportLog._meta.fields
    )
    list_per_page = 30

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def status_badge(self, obj):
        colors = {
            'SUCCESS': ('#ecfdf5', '#065f46', '#a7f3d0', '✓'),
            'REJECTED': ('#fffbeb', '#92400e', '#fde68a', '⚠'),
            'FAILED': ('#fef2f2', '#991b1b', '#fecaca', '✗'),
        }
        bg, fg, br, ic = colors.get(obj.status, ('#f3f4f6', '#374151', '#e5e7eb', '·'))
        return format_html(
            '<span style="background:{};color:{};border:1px solid {};padding:2px 9px;'
            'border-radius:99px;font-size:11.5px;font-weight:600;">{} {}</span>',
            bg, fg, br, ic, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
