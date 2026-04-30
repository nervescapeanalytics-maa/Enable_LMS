"""
Friendly Admin Forms for System Configuration
==============================================
Replaces raw JSON textareas with visual, user-friendly widgets.
"""
from django import forms
from system_config.models import (
    SystemSetting, FeatureFlag, MFAPolicy,
    MaintenanceWindow, FounderInfo,
    AIFeatureConfig, ClassLinkConfig,
    IntegrationConfig, WebsiteSetting, ReportTemplate,
    FooterConfig,
)
from system_config.widgets import (
    TagListWidget, EmailListWidget, KeyValueWidget,
    SocialLinksWidget, LinksListWidget, FiltersWidget,
    SchedulePickerWidget,
)

USER_TYPE_CHOICES = ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT', 'STAFF']
FEATURE_CHOICES = [
    'Login', 'Dashboard', 'Assessments', 'Attendance',
    'LMS', 'AI Features', 'Communication', 'Reports',
    'Live Classes', 'Materials', 'Payments',
]

REPORT_COLUMN_CHOICES = [
    'student_name', 'student_id', 'roll_number', 'email', 'phone',
    'class_name', 'section', 'center', 'batch',
    'attendance_percentage', 'present_count', 'absent_count', 'late_count',
    'exam_name', 'total_marks', 'obtained_marks', 'percentage', 'grade', 'rank',
    'teacher_name', 'subject', 'department',
    'fee_amount', 'paid_amount', 'due_amount', 'payment_date', 'payment_status',
    'date', 'date_from', 'date_to', 'academic_year', 'semester',
    'status', 'remarks', 'created_at', 'updated_at',
]

REPORT_GROUP_CHOICES = [
    'class_name', 'section', 'center', 'batch',
    'subject', 'department', 'teacher_name',
    'academic_year', 'semester', 'month', 'week',
    'status', 'grade', 'payment_status',
]

REPORT_SORT_CHOICES = [
    'student_name', 'roll_number', 'percentage', 'rank',
    'attendance_percentage', 'date', 'created_at',
    'total_marks', 'obtained_marks', 'fee_amount',
    'teacher_name', 'class_name', 'center',
]

# Per-report-type column suggestions (from corresponding DB tables)
REPORT_TYPE_COLUMNS = {
    'STUDENT': [
        'student_name', 'student_id', 'roll_number', 'email', 'phone',
        'class_name', 'section', 'batch', 'center',
        'admission_date', 'date_of_birth', 'gender', 'status',
        'parent_name', 'parent_phone', 'address',
        'academic_year', 'semester', 'created_at',
    ],
    'TEACHER': [
        'teacher_name', 'teacher_id', 'email', 'phone',
        'subject', 'department', 'designation', 'qualification',
        'date_of_joining', 'experience_years', 'status',
        'classes_assigned', 'center', 'created_at',
    ],
    'ATTENDANCE': [
        'student_name', 'roll_number', 'class_name', 'section', 'batch',
        'attendance_date', 'status', 'attendance_percentage',
        'present_count', 'absent_count', 'late_count', 'leave_count',
        'teacher_name', 'subject', 'center', 'month', 'week',
    ],
    'EXAM': [
        'student_name', 'roll_number', 'exam_name', 'subject',
        'total_marks', 'obtained_marks', 'percentage', 'grade', 'rank',
        'class_name', 'section', 'batch', 'center',
        'exam_date', 'academic_year', 'semester', 'status',
    ],
    'CENTER': [
        'center_name', 'center_code', 'address', 'city', 'state',
        'student_count', 'teacher_count', 'batch_count',
        'active_classes', 'attendance_rate', 'avg_score',
        'status', 'established_date', 'contact_person', 'phone',
    ],
    'FINANCIAL': [
        'student_name', 'roll_number', 'fee_type', 'fee_amount',
        'paid_amount', 'due_amount', 'discount',
        'payment_date', 'payment_mode', 'payment_status',
        'receipt_number', 'class_name', 'batch', 'center',
        'academic_year', 'semester',
    ],
    'COMBINED': [
        'student_name', 'student_id', 'roll_number', 'email', 'phone',
        'class_name', 'section', 'batch', 'center',
        'attendance_percentage', 'present_count', 'absent_count',
        'exam_name', 'total_marks', 'obtained_marks', 'percentage', 'grade', 'rank',
        'teacher_name', 'subject', 'department',
        'fee_amount', 'paid_amount', 'due_amount', 'payment_status',
        'academic_year', 'semester', 'status', 'created_at',
    ],
}

REPORT_TYPE_FILTERS = {
    'STUDENT': ['class_name', 'section', 'batch', 'center', 'status', 'gender', 'academic_year'],
    'TEACHER': ['department', 'subject', 'designation', 'center', 'status'],
    'ATTENDANCE': ['class_name', 'section', 'batch', 'center', 'status', 'date_from', 'date_to', 'month'],
    'EXAM': ['exam_name', 'class_name', 'section', 'batch', 'center', 'subject', 'academic_year'],
    'CENTER': ['city', 'state', 'status'],
    'FINANCIAL': ['class_name', 'batch', 'center', 'payment_status', 'fee_type', 'academic_year', 'date_from', 'date_to'],
    'COMBINED': ['class_name', 'section', 'batch', 'center', 'academic_year', 'semester', 'status', 'date_from', 'date_to'],
}

REPORT_TYPE_GROUP_BY = {
    'STUDENT': ['class_name', 'section', 'batch', 'center', 'gender', 'status'],
    'TEACHER': ['department', 'subject', 'designation', 'center'],
    'ATTENDANCE': ['class_name', 'section', 'batch', 'center', 'month', 'week', 'status'],
    'EXAM': ['class_name', 'section', 'batch', 'center', 'subject', 'grade'],
    'CENTER': ['city', 'state', 'status'],
    'FINANCIAL': ['class_name', 'batch', 'center', 'payment_status', 'fee_type'],
    'COMBINED': ['class_name', 'section', 'batch', 'center', 'academic_year'],
}

REPORT_TYPE_SORT_BY = {
    'STUDENT': ['student_name', 'roll_number', 'class_name', 'admission_date', 'created_at'],
    'TEACHER': ['teacher_name', 'date_of_joining', 'department', 'subject'],
    'ATTENDANCE': ['student_name', 'roll_number', 'attendance_percentage', 'attendance_date'],
    'EXAM': ['student_name', 'roll_number', 'percentage', 'rank', 'total_marks', 'obtained_marks'],
    'CENTER': ['center_name', 'student_count', 'teacher_count', 'attendance_rate'],
    'FINANCIAL': ['student_name', 'fee_amount', 'paid_amount', 'due_amount', 'payment_date'],
    'COMBINED': ['student_name', 'roll_number', 'percentage', 'attendance_percentage', 'created_at'],
}


# ═══════════════════════════════════════════════════════════════════
# SYSTEM SETTING
# ═══════════════════════════════════════════════════════════════════
class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = '__all__'
        widgets = {
            'setting_json': KeyValueWidget(
                key_placeholder='Setting name',
                value_placeholder='Setting value',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# FEATURE FLAG
# ═══════════════════════════════════════════════════════════════════
class FeatureFlagForm(forms.ModelForm):
    class Meta:
        model = FeatureFlag
        fields = '__all__'
        widgets = {
            'allowed_user_types': TagListWidget(
                placeholder='Select user type…',
                suggestions=USER_TYPE_CHOICES,
            ),
            'allowed_user_ids': TagListWidget(
                placeholder='Enter user ID…',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# MFA POLICY
# ═══════════════════════════════════════════════════════════════════
class MFAPolicyForm(forms.ModelForm):
    class Meta:
        model = MFAPolicy
        fields = '__all__'
        widgets = {
            'applies_to_user_types': TagListWidget(
                placeholder='Select user type…',
                suggestions=USER_TYPE_CHOICES,
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# MAINTENANCE WINDOW
# ═══════════════════════════════════════════════════════════════════
class MaintenanceWindowForm(forms.ModelForm):
    class Meta:
        model = MaintenanceWindow
        fields = '__all__'
        widgets = {
            'affected_features': TagListWidget(
                placeholder='Select feature…',
                suggestions=FEATURE_CHOICES,
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# FOUNDER INFO
# ═══════════════════════════════════════════════════════════════════
class FounderInfoForm(forms.ModelForm):
    class Meta:
        model = FounderInfo
        fields = '__all__'
        widgets = {
            'social_links': SocialLinksWidget(),
        }


# ═══════════════════════════════════════════════════════════════════
# AI FEATURE CONFIG
# ═══════════════════════════════════════════════════════════════════
class AIFeatureConfigForm(forms.ModelForm):
    class Meta:
        model = AIFeatureConfig
        fields = '__all__'
        widgets = {
            'config_json': KeyValueWidget(
                key_placeholder='Parameter name',
                value_placeholder='Parameter value',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# CLASS LINK CONFIG
# ═══════════════════════════════════════════════════════════════════
class ClassLinkConfigForm(forms.ModelForm):
    class Meta:
        model = ClassLinkConfig
        fields = '__all__'
        widgets = {
            'config_json': KeyValueWidget(
                key_placeholder='Config key',
                value_placeholder='Config value',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# INTEGRATION CONFIG
# ═══════════════════════════════════════════════════════════════════
class IntegrationConfigForm(forms.ModelForm):
    class Meta:
        model = IntegrationConfig
        fields = '__all__'
        widgets = {
            'playlist_ids': TagListWidget(
                placeholder='Enter YouTube playlist ID…',
            ),
            'config_json': KeyValueWidget(
                key_placeholder='Parameter',
                value_placeholder='Value',
            ),
            'usage_stats': KeyValueWidget(
                key_placeholder='Metric',
                value_placeholder='Value',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# WEBSITE SETTING
# ═══════════════════════════════════════════════════════════════════
class WebsiteSettingForm(forms.ModelForm):
    class Meta:
        model = WebsiteSetting
        fields = '__all__'
        widgets = {
            'setting_json': KeyValueWidget(
                key_placeholder='Setting key',
                value_placeholder='Setting value',
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# REPORT TEMPLATE — the key one from the screenshot
# ═══════════════════════════════════════════════════════════════════
class ReportTemplateForm(forms.ModelForm):
    # Override created_by with a dropdown of admin/teacher users
    created_by_user = forms.ChoiceField(
        choices=[],
        required=False,
        label='Created By',
        help_text='Select who is creating this report template',
    )

    class Meta:
        model = ReportTemplate
        fields = '__all__'
        widgets = {
            'filters_json': FiltersWidget(),
            'columns_json': TagListWidget(
                placeholder='Select or type column…',
                suggestions=REPORT_COLUMN_CHOICES,
            ),
            'group_by': TagListWidget(
                placeholder='Select grouping field…',
                suggestions=REPORT_GROUP_CHOICES,
            ),
            'sort_by': TagListWidget(
                placeholder='Select sort field…',
                suggestions=REPORT_SORT_CHOICES,
            ),
            'recipients_email': EmailListWidget(),
            'schedule_cron': SchedulePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build created_by choices from Admin and Teacher models
        choices = [('', '— Select User —')]
        try:
            from accounts.models import Admin, Teacher
            admins = Admin.objects.filter(status='ACTIVE').order_by('first_name')[:50]
            if admins.exists():
                admin_choices = []
                for a in admins:
                    display = f"{a.first_name} {a.last_name}".strip() or a.username or str(a.id)[:8]
                    admin_choices.append((str(a.id), f"{display} (Admin)"))
                choices.append(('Admins', admin_choices))
            teachers = Teacher.objects.filter(status='ACTIVE').order_by('first_name')[:50]
            if teachers.exists():
                teacher_choices = []
                for t in teachers:
                    display = f"{t.first_name} {t.last_name}".strip() or t.username or str(t.id)[:8]
                    teacher_choices.append((str(t.id), f"{display} (Teacher)"))
                choices.append(('Teachers', teacher_choices))
        except Exception:
            pass
        self.fields['created_by_user'].choices = choices

        # Pre-select current value
        if self.instance and self.instance.created_by:
            self.fields['created_by_user'].initial = str(self.instance.created_by)

        # Hide the original created_by UUID field
        if 'created_by' in self.fields:
            self.fields['created_by'].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()
        # Map created_by_user dropdown value → UUID field
        user_val = cleaned.get('created_by_user')
        if user_val:
            import uuid
            try:
                cleaned['created_by'] = uuid.UUID(user_val)
            except (ValueError, TypeError):
                cleaned['created_by'] = None
        else:
            cleaned['created_by'] = None
        return cleaned


# ═══════════════════════════════════════════════════════════════════
# FOOTER CONFIG
# ═══════════════════════════════════════════════════════════════════
class FooterConfigForm(forms.ModelForm):
    class Meta:
        model = FooterConfig
        fields = '__all__'
        widgets = {
            'links_json': LinksListWidget(),
            'social_links_json': SocialLinksWidget(),
        }
