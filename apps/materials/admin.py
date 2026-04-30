from django.contrib import admin
from django import forms as django_forms
from django.utils.html import format_html
from materials.models import StudyMaterial, MaterialAccess, PhotoGallery, Scholarship, TopperStudent
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status


# ═══════════════════════════════════════════════════════════════════
# STUDY MATERIAL — Simplified for non-technical school admins
# ═══════════════════════════════════════════════════════════════════

MATERIAL_TYPE_CHOICES = [
    ('NOTES', '📄 PDF Notes'),
    ('EBOOK', '📖 eBook'),
    ('VIDEO', '🎬 Video Lecture (YouTube Link)'),
    ('TEST_PAPER', '📝 Test Paper'),
    ('QUESTION_PAPER', '📋 Question Paper (Previous Year)'),
    ('PRACTICE', '✏️ Practice Questions'),
    ('ASSIGNMENT', '📌 Assignment'),
]

CONTENT_CATEGORY_CHOICES = [
    ('', '-- Select Category --'),
    ('NOTES', '📄 Notes'),
    ('VIDEOS', '🎬 Videos'),
    ('TEST_PAPERS', '📝 Test Papers'),
    ('QUESTION_BANK', '📋 Question Bank'),
    ('ASSIGNMENTS', '📌 Assignments'),
]

DIFFICULTY_CHOICES = [
    ('', '-- Select Difficulty --'),
    ('BEGINNER', '🟢 Easy'),
    ('INTERMEDIATE', '🟡 Medium'),
    ('ADVANCED', '🔴 Hard'),
]

TAG_CHOICES = [
    ('Important', '⭐ Important'),
    ('Revision', '🔄 Revision'),
    ('NEET', '🏥 NEET'),
    ('JEE', '🔬 JEE'),
    ('Easy', '🟢 Easy'),
    ('Medium', '🟡 Medium'),
    ('Hard', '🔴 Hard'),
]

TARGET_AUDIENCE_CHOICES = [
    ('STUDENT', '👨‍🎓 Students'),
    ('TEACHER', '👨‍🏫 Teachers'),
    ('ALL', '👥 All'),
]


class StudyMaterialAdminForm(django_forms.ModelForm):
    """Simplified form for non-technical admins (teachers, coordinators).
    Structure: Class → Subject → Chapter → Content Category → Item."""

    material_type = django_forms.ChoiceField(
        choices=MATERIAL_TYPE_CHOICES,
        label='Content Type',
        help_text='What type of material is this?',
    )
    content_category = django_forms.ChoiceField(
        choices=CONTENT_CATEGORY_CHOICES,
        required=False,
        label='Content Category',
        help_text='Group this material under a category for easier navigation.',
    )
    difficulty_level = django_forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        required=False,
        label='Difficulty Level',
    )
    target_audience = django_forms.ChoiceField(
        choices=TARGET_AUDIENCE_CHOICES,
        initial='STUDENT',
        label='Who is this for?',
    )
    tags = django_forms.MultipleChoiceField(
        choices=TAG_CHOICES,
        required=False,
        widget=django_forms.CheckboxSelectMultiple,
        label='Tags',
        help_text='Tick all that apply.',
    )

    class Meta:
        model = StudyMaterial
        fields = '__all__'
        exclude = ('file_size_bytes', 'file_mime_type', 'file_hash',
                   'video_embed_url', 'video_duration_seconds',
                   'requires_enrollment', 'is_deleted',
                   'material_meta', 'ext_material_1', 'ext_material_2', 'ext_material_3')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make mandatory fields per system prompt
        if 'title' in self.fields:
            self.fields['title'].required = True
            self.fields['title'].widget.attrs['placeholder'] = 'e.g. Class11_Physics_Kinematics_Notes_MotionBasics'
            self.fields['title'].help_text = 'Use clear naming: Class_Subject_Chapter_Type_Title'
        if 'subject' in self.fields:
            self.fields['subject'].required = True
            self.fields['subject'].help_text = 'Required — select the subject this material belongs to.'
        if 'chapter' in self.fields:
            self.fields['chapter'].required = True
            self.fields['chapter'].help_text = 'Required — select the chapter.'
        if 'description' in self.fields:
            self.fields['description'].widget.attrs.update({
                'placeholder': 'Brief description of the content',
                'rows': 2,
            })
        if 'file_url' in self.fields:
            self.fields['file_url'].widget.attrs['placeholder'] = 'https://drive.google.com/file/... or direct link'
            self.fields['file_url'].help_text = 'Direct link to PDF, DOCX, XLSX, or other file.'
        if 'video_url' in self.fields:
            self.fields['video_url'].widget.attrs['placeholder'] = 'https://www.youtube.com/watch?v=...'
            self.fields['video_url'].help_text = 'YouTube or video URL. Students watch this directly.'
        if 'thumbnail_url' in self.fields:
            self.fields['thumbnail_url'].widget.attrs['placeholder'] = 'https://example.com/image.jpg'
            self.fields['thumbnail_url'].help_text = 'Preview image URL (optional).'

        # Pre-select tags for existing instances
        if self.instance and self.instance.pk:
            current_tags = self.instance.tags or []
            self.initial['tags'] = current_tags
            # Load content_category from material_meta
            meta = self.instance.material_meta or {}
            if isinstance(meta, dict):
                self.initial['content_category'] = meta.get('content_category', '')

    def clean_tags(self):
        return list(self.cleaned_data.get('tags', []))

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get('material_type')
        file_url = cleaned_data.get('file_url')
        video_url = cleaned_data.get('video_url')

        # For video types, require video_url
        if material_type == 'VIDEO' and not video_url:
            self.add_error('video_url', 'Video URL is required for Video Lectures.')
        # For non-video types, require file_url
        if material_type in ('NOTES', 'EBOOK', 'TEST_PAPER', 'QUESTION_PAPER', 'PRACTICE', 'ASSIGNMENT'):
            if not file_url and not video_url:
                self.add_error('file_url', 'Please provide a file URL or video URL.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tags = self.cleaned_data.get('tags', [])
        # Store content_category in material_meta JSON
        meta = instance.material_meta or {}
        if not isinstance(meta, dict):
            meta = {}
        content_cat = self.cleaned_data.get('content_category', '')
        if content_cat:
            meta['content_category'] = content_cat
        instance.material_meta = meta
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(StudyMaterial)
class StudyMaterialAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = StudyMaterialAdminForm
    list_display = (
        'title', 'subject', 'chapter', 'type_badge', 'content_category_display',
        'batch', 'difficulty_badge', 'tags_display', 'published_badge', 'view_count_display',
    )
    list_filter = ('material_type', 'difficulty_level', 'target_audience', 'is_published', 'batch', 'subject')
    search_fields = ('title', 'material_code')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'published_at',
        'view_count',
        'download_count',
        'rating',
        'rating_count',
    )
    fieldsets = (
        ('Content Details', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📚 <b>Study Material Management</b> — Upload PDFs, eBooks, videos, test papers, and question banks '
                'for Class 9–12 students (NEET/JEE).<br>'
                '💡 <b>Naming:</b> Use clear names like <code>Class11_Physics_Kinematics_Notes_MotionBasics</code>'
                '</div>'
            ),
            'fields': (
                'tenant',
                'title',
                'description',
                'material_type',
                'content_category',
                'thumbnail_url',
            ),
        }),
        ('Class → Subject → Chapter', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📖 <b>Required:</b> Link this material to a Subject and Chapter. '
                'Students navigate by Class → Subject → Chapter to find materials.'
                '</div>'
            ),
            'fields': (
                'subject',
                'chapter',
                'topic',
                'batch',
                'target_audience',
            ),
        }),
        ('Difficulty & Tags', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🏷️ Help students filter materials by difficulty and exam type.'
                '</div>'
            ),
            'fields': (
                'difficulty_level',
                'tags',
            ),
        }),
        ('Upload / Link', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📎 <b>PDFs/Notes/eBooks:</b> Paste the file URL (Google Drive, direct link)<br>'
                '🎬 <b>Video Lectures:</b> Paste the YouTube link<br>'
                '📁 <b>Allowed formats:</b> PDF, DOCX, XLSX, MP4, YouTube Links'
                '</div>'
            ),
            'fields': (
                'file_url',
                'file_name',
                'video_url',
                'youtube_video_id',
            ),
        }),
        ('Publishing & Access', {
            'fields': (
                'is_published',
                'is_downloadable',
                'is_free',
                'is_active',
                'allowed_batches',
            ),
        }),
        ('Stats (auto-tracked)', {
            'fields': (
                'view_count',
                'download_count',
                'rating',
                'rating_count',
                'published_at',
            ),
            'classes': ('collapse',),
        }),
        ('Uploader', {
            'fields': (
                'uploaded_by_id',
                'uploaded_by_name',
                'uploaded_by_type',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def type_badge(self, obj):
        icons = {
            'EBOOK': '📖', 'VIDEO': '🎬', 'QUESTION_PAPER': '📝', 'NOTES': '📄',
            'ASSIGNMENT': '📋', 'REFERENCE': '📚', 'SOLUTION': '✅',
            'TRAINING_VIDEO': '🎓', 'PRESENTATION': '📊',
        }
        colors = {
            'EBOOK': '#ef4444', 'VIDEO': '#3b82f6', 'QUESTION_PAPER': '#f59e0b',
            'NOTES': '#10b981', 'ASSIGNMENT': '#8b5cf6', 'REFERENCE': '#6366f1',
            'SOLUTION': '#22c55e', 'TRAINING_VIDEO': '#0ea5e9', 'PRESENTATION': '#f97316',
        }
        t = getattr(obj, 'material_type', '')
        icon = icons.get(t, '📄')
        c = colors.get(t, '#94a3b8')
        label = obj.get_material_type_display() if hasattr(obj, 'get_material_type_display') else t
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            c, icon, label
        )
    type_badge.short_description = 'Type'

    def difficulty_badge(self, obj):
        d = getattr(obj, 'difficulty_level', '')
        badges = {
            'BEGINNER': ('🟢', '#22c55e', 'Easy'),
            'INTERMEDIATE': ('🟡', '#f59e0b', 'Medium'),
            'ADVANCED': ('🔴', '#ef4444', 'Hard'),
        }
        if d in badges:
            icon, color, label = badges[d]
            return format_html('<span style="color:{};font-weight:600;">{} {}</span>', color, icon, label)
        return format_html('<span style="color:#94a3b8;">—</span>')
    difficulty_badge.short_description = 'Difficulty'

    def published_badge(self, obj):
        return colored_status(getattr(obj, 'is_published', False))
    published_badge.short_description = 'Published'

    def view_count_display(self, obj):
        count = getattr(obj, 'view_count', 0) or 0
        return format_html(
            '<span style="font-weight:600;color:#94a3b8;">{}</span>',
            count
        )
    view_count_display.short_description = 'Views'

    def content_category_display(self, obj):
        meta = getattr(obj, 'material_meta', None) or {}
        cat = meta.get('content_category', '') if isinstance(meta, dict) else ''
        if cat:
            labels = dict(CONTENT_CATEGORY_CHOICES)
            return format_html('<span style="color:#6366f1;font-weight:600;">{}</span>', labels.get(cat, cat))
        return format_html('<span style="color:#94a3b8;">—</span>')
    content_category_display.short_description = 'Category'

    def tags_display(self, obj):
        tags = getattr(obj, 'tags', None) or []
        if not tags:
            return format_html('<span style="color:#94a3b8;">—</span>')
        badges = []
        for tag in tags[:5]:
            badges.append(
                '<span style="display:inline-block;padding:1px 6px;margin:1px;border-radius:4px;'
                'font-size:0.7rem;background:rgba(99,102,241,0.1);color:#6366f1;font-weight:600;">'
                f'{tag}</span>'
            )
        return format_html(''.join(badges))
    tags_display.short_description = 'Tags'


@admin.register(MaterialAccess)
class MaterialAccessAdmin(EnhancedModelAdmin):
    list_display = ('material', 'user_id', 'action', 'accessed_at')
    list_filter = ('action',)
    actions = [export_as_csv]

    readonly_fields = ('id', 'accessed_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'tenant',
                    'material',
                    'user_id',
                    'user_type',
                    'action',
                    'accessed_at',
                    'duration_seconds',
                    'progress_percent',
                )
            },
        ),
    )


@admin.register(PhotoGallery)
class PhotoGalleryAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('title', 'category', 'active_badge', 'sort_order', 'preview')
    list_filter = ('is_active', 'category')
    list_editable = ('sort_order',)
    actions = [export_as_csv, activate_selected, deactivate_selected]

    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'tenant',
                    'title',
                    'description',
                    'category',
                    'image_url',
                    'thumbnail_url',
                    'sort_order',
                    'is_active',
                    'uploaded_by_id',
                    'created_at',
                )
            },
        ),
    )

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'

    def preview(self, obj):
        url = getattr(obj, 'image_url', None) or getattr(obj, 'image', None)
        if url:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:6px;object-fit:cover;border:1px solid rgba(99,102,241,0.15);">',
                url
            )
        return '-'
    preview.short_description = 'Preview'


@admin.register(Scholarship)
class ScholarshipAdmin(EnhancedModelAdmin):
    list_display = ('title', 'amount_display', 'discount_display', 'active_badge')
    actions = [export_as_csv, activate_selected, deactivate_selected]

    readonly_fields = ('id',)
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'tenant',
                    'title',
                    'description',
                    'eligibility',
                    'amount',
                    'discount_percent',
                    'documents_required',
                    'apply_url',
                    'valid_from',
                    'valid_until',
                    'is_active',
                )
            },
        ),
    )

    def amount_display(self, obj):
        amt = getattr(obj, 'amount', None)
        if amt:
            return format_html('<span style="font-weight:700;color:#10b981;">Rs.{}</span>', amt)
        return '-'
    amount_display.short_description = 'Amount'

    def discount_display(self, obj):
        pct = getattr(obj, 'discount_percent', None)
        if pct:
            return format_html('<span style="font-weight:700;color:#f59e0b;">{}%</span>', pct)
        return '-'
    discount_display.short_description = 'Discount'

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'


@admin.register(TopperStudent)
class TopperStudentAdmin(ImportExportMixin, EnhancedModelAdmin):
    list_display = ('student_name', 'exam_name', 'year', 'rank_display', 'featured_badge')
    list_filter = ('year', 'is_featured')
    search_fields = ('student_name', 'exam_name')
    actions = [export_as_csv, export_as_json]

    readonly_fields = ('id',)
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'tenant',
                    'student',
                    'student_name',
                    'exam_name',
                    'year',
                    'rank',
                    'score',
                    'photo_url',
                    'testimonial',
                    'is_featured',
                    'is_active',
                    'sort_order',
                )
            },
        ),
    )

    def rank_display(self, obj):
        rank = getattr(obj, 'rank', None)
        if rank:
            colors = {1: '#f59e0b', 2: '#94a3b8', 3: '#cd7f32'}
            c = colors.get(rank, '#64748b')
            return format_html('<span style="font-weight:800;color:{};font-size:1rem;">#{}</span>', c, rank)
        return '-'
    rank_display.short_description = 'Rank'

    def featured_badge(self, obj):
        if getattr(obj, 'is_featured', False):
            return format_html('<span style="color:#f59e0b;font-weight:700;">&#9733; Featured</span>')
        return '-'
    featured_badge.short_description = 'Featured'
