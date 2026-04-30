from django.contrib import admin
from django import forms as django_forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.contrib.admin.widgets import FilteredSelectMultiple
from classes.models import (
    YouTubeChannel, ScheduledClass, ClassAccessToken, ClassWatchTime,
    ClassLinkConfigProxy, IntegrationConfigProxy, RecurringClassTemplate,
)
from system_config.forms import ClassLinkConfigForm, IntegrationConfigForm
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status


# ═══════════════════════════════════════════════════════════════════
# COMMON DROPDOWN CHOICES FOR NON-TECHNICAL USERS
# ═══════════════════════════════════════════════════════════════════

RATE_LIMIT_CHOICES = [
    (50, '🐢 Low (50/hr) — Small institution, < 100 students'),
    (100, '✅ Standard (100/hr) — Recommended for most institutions'),
    (200, '⚡ Medium (200/hr) — 500+ students'),
    (500, '🚀 High (500/hr) — 1000+ students, paid quota'),
]

RATE_LIMIT_PER_USER_CHOICES = [
    (10, '10/hr — Strict (saves quota)'),
    (20, '20/hr — Standard (recommended)'),
    (50, '50/hr — Generous'),
]

DURATION_CHOICES = [
    (30, '30 minutes'),
    (45, '45 minutes'),
    (60, '60 minutes (recommended)'),
    (90, '90 minutes'),
    (120, '2 hours'),
    (180, '3 hours'),
]

LINK_GEN_TIMING_CHOICES = [
    (5, '5 minutes before'),
    (10, '10 minutes before'),
    (15, '15 minutes before (recommended)'),
    (30, '30 minutes before'),
    (60, '1 hour before'),
]

WATCH_PERCENT_CHOICES = [
    (50, '50% — Lenient'),
    (60, '60% — Moderate'),
    (70, '70% — Standard (recommended)'),
    (80, '80% — Strict'),
    (90, '90% — Very Strict'),
]

THRESHOLD_MINUTE_CHOICES = [
    (5, '5 minutes'),
    (10, '10 minutes'),
    (15, '15 minutes (recommended)'),
    (20, '20 minutes'),
    (30, '30 minutes'),
]

WEEKDAY_CHOICES = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]


# ═══════════════════════════════════════════════════════════════════
# CUSTOM FORMS — SIMPLIFIED WITH DROPDOWNS
# ═══════════════════════════════════════════════════════════════════

class YouTubeIntegrationAdminForm(IntegrationConfigForm):
    """Radically simplified form for non-technical YouTube setup."""

    max_requests_per_hour = django_forms.TypedChoiceField(
        choices=RATE_LIMIT_CHOICES,
        coerce=int,
        initial=100,
        label='API Rate Limit',
        help_text='How many API calls per hour. "Standard" works for most institutions.',
    )
    max_requests_per_user = django_forms.TypedChoiceField(
        choices=RATE_LIMIT_PER_USER_CHOICES,
        coerce=int,
        initial=20,
        label='Per-User Rate Limit',
        help_text='Limits how much any single user can consume. "Standard" is recommended.',
    )

    class Meta(IntegrationConfigForm.Meta):
        help_texts = {
            'name': 'Give this a friendly name, e.g. "Main YouTube Channel" or "Physics Dept YouTube".',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Auto-fill provider and endpoint — no need for user to touch these
        if 'provider' in self.fields:
            self.fields['provider'].widget = django_forms.HiddenInput()
            self.fields['provider'].initial = 'youtube'
        if 'api_endpoint' in self.fields:
            self.fields['api_endpoint'].widget = django_forms.HiddenInput()
            self.fields['api_endpoint'].initial = 'https://www.googleapis.com/youtube/v3'
        # Friendly placeholders
        if 'name' in self.fields:
            self.fields['name'].widget.attrs['placeholder'] = 'e.g. Main YouTube Channel'
        if 'channel_id' in self.fields:
            self.fields['channel_id'].widget.attrs['placeholder'] = 'e.g. UCxxxxxxxxxxxxxxxxxxxxxxxx'
            self.fields['channel_id'].label = 'YouTube Channel ID'
        if 'channel_name' in self.fields:
            self.fields['channel_name'].widget.attrs['placeholder'] = 'e.g. ABC Academy Live Classes'
            self.fields['channel_name'].label = 'Channel Display Name'
        if 'description' in self.fields:
            self.fields['description'].widget.attrs.update({
                'placeholder': 'Optional: what is this channel used for?',
                'rows': 2,
            })
        if 'api_key' in self.fields:
            self.fields['api_key'].widget.attrs['placeholder'] = 'Paste your API key from Google Cloud Console'
            self.fields['api_key'].label = 'YouTube API Key'
        if 'oauth_client_id' in self.fields:
            self.fields['oauth_client_id'].widget.attrs['placeholder'] = '123456789-abc.apps.googleusercontent.com'
        if 'oauth_client_secret' in self.fields:
            self.fields['oauth_client_secret'].widget.attrs['placeholder'] = 'Paste OAuth secret from Google Cloud Console'
        # Hide auto-managed OAuth token fields completely
        for hidden_field in ('oauth_token', 'oauth_refresh_token', 'oauth_token_expiry',
                             'api_secret', 'webhook_url'):
            if hidden_field in self.fields:
                self.fields[hidden_field].widget = django_forms.HiddenInput()
        # Budget fields — hide for YouTube (free API)
        for budget_field in ('daily_budget_limit', 'monthly_budget_limit'):
            if budget_field in self.fields:
                self.fields[budget_field].widget = django_forms.HiddenInput()
        # Pre-select current values for dropdown fields
        if self.instance and self.instance.pk:
            if 'max_requests_per_hour' in self.fields:
                current = getattr(self.instance, 'max_requests_per_hour', 100)
                valid_values = [c[0] for c in RATE_LIMIT_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['max_requests_per_hour'] = closest
            if 'max_requests_per_user' in self.fields:
                current = getattr(self.instance, 'max_requests_per_user', 20)
                valid_values = [c[0] for c in RATE_LIMIT_PER_USER_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['max_requests_per_user'] = closest

    def clean_provider(self):
        return 'youtube'

    def clean_api_endpoint(self):
        return 'https://www.googleapis.com/youtube/v3'

    def clean_channel_id(self):
        channel_id = self.cleaned_data.get('channel_id', '')
        if channel_id and not channel_id.startswith('UC'):
            raise ValidationError(
                'YouTube Channel IDs start with "UC". '
                'Find yours at YouTube Studio → Settings → Channel → Advanced Settings.'
            )
        return channel_id

    def clean(self):
        cleaned_data = super().clean()
        api_key = cleaned_data.get('api_key')
        oauth_client_id = cleaned_data.get('oauth_client_id')
        if not api_key and not oauth_client_id:
            self.add_error(None, ValidationError(
                'Please provide at least an API Key or OAuth Client ID. '
                'Get these from Google Cloud Console → APIs & Services → Credentials.'
            ))
        return cleaned_data


class ClassLinkConfigAdminForm(ClassLinkConfigForm):
    """Simplified form with dropdowns for non-technical class link setup."""

    generate_minutes_before = django_forms.TypedChoiceField(
        choices=LINK_GEN_TIMING_CHOICES,
        coerce=int,
        initial=15,
        label='Create Link',
        help_text='How early should the class link be generated before the class starts?',
    )
    default_duration_minutes = django_forms.TypedChoiceField(
        choices=DURATION_CHOICES,
        coerce=int,
        initial=60,
        label='Default Class Duration',
        help_text='Standard class length. Teachers can change this per class.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide technical fields that only devs need
        for hidden_field in ('webhook_url', 'config_json'):
            if hidden_field in self.fields:
                self.fields[hidden_field].widget = django_forms.HiddenInput()
        # Friendlier labels
        if 'api_key_reference' in self.fields:
            self.fields['api_key_reference'].label = 'API Key Setting Name'
            self.fields['api_key_reference'].widget.attrs['placeholder'] = 'e.g. YOUTUBE_API_KEY'
        if 'client_secret_reference' in self.fields:
            self.fields['client_secret_reference'].label = 'Client Secret Setting Name'
            self.fields['client_secret_reference'].widget.attrs['placeholder'] = 'e.g. YOUTUBE_CLIENT_SECRET'
        if 'oauth_token_reference' in self.fields:
            self.fields['oauth_token_reference'].label = 'OAuth Token Setting Name'
            self.fields['oauth_token_reference'].widget.attrs['placeholder'] = 'e.g. YOUTUBE_OAUTH_TOKEN'
        if 'api_endpoint' in self.fields:
            self.fields['api_endpoint'].widget.attrs['placeholder'] = 'e.g. https://www.googleapis.com/youtube/v3'
        # Pre-select current values for dropdown fields
        if self.instance and self.instance.pk:
            if 'generate_minutes_before' in self.fields:
                current = getattr(self.instance, 'generate_minutes_before', 15)
                valid_values = [c[0] for c in LINK_GEN_TIMING_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['generate_minutes_before'] = closest
            if 'default_duration_minutes' in self.fields:
                current = getattr(self.instance, 'default_duration_minutes', 60)
                valid_values = [c[0] for c in DURATION_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['default_duration_minutes'] = closest

    def clean(self):
        cleaned_data = super().clean()
        auto_gen = cleaned_data.get('auto_generate_link')
        platform = cleaned_data.get('platform')
        api_key_ref = cleaned_data.get('api_key_reference')
        client_id = cleaned_data.get('client_id')

        if auto_gen and platform != 'CUSTOM' and not api_key_ref and not client_id:
            self.add_error(None, ValidationError(
                'Auto-generate is ON but no API credentials are set. '
                'Please add credentials below, or change platform to "Custom URL" for manual links.'
            ))
        return cleaned_data


class ScheduledClassAdminForm(django_forms.ModelForm):
    """Simplified scheduled class form with dropdown presets and searchable multi-select batches."""

    min_watch_percent_for_present = django_forms.TypedChoiceField(
        choices=WATCH_PERCENT_CHOICES,
        coerce=int,
        initial=70,
        label='Minimum Watch % for Present',
        help_text='Student must watch this much of the class to be marked "Present".',
    )
    auto_attendance_threshold_minutes = django_forms.TypedChoiceField(
        choices=THRESHOLD_MINUTE_CHOICES,
        coerce=int,
        initial=15,
        label='Grace Period (minutes)',
        help_text='How long after class start to still count as "on time".',
    )

    custom_chapter_name = django_forms.CharField(
        required=False,
        max_length=500,
        label='Custom Chapter Name',
        widget=django_forms.TextInput(attrs={
            'placeholder': 'Type new chapter name, e.g. Thermodynamics',
        }),
        help_text='Fill this only when you select "── Add Custom Chapter ──" above.',
    )
    custom_topic_name = django_forms.CharField(
        required=False,
        max_length=500,
        label='Custom Topic Name',
        widget=django_forms.TextInput(attrs={
            'placeholder': 'Type new topic name, e.g. Carnot Cycle',
        }),
        help_text='Fill this only when you select "── Add Custom Topic ──" above.',
    )

    class Meta:
        model = ScheduledClass
        fields = '__all__'
        exclude = ('created_by_id', 'created_by_type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'description' in self.fields:
            self.fields['description'].widget.attrs.update({
                'placeholder': 'Brief description of what will be covered',
                'rows': 2,
            })
        if 'class_code' in self.fields:
            self.fields['class_code'].widget.attrs['placeholder'] = 'e.g. PHY-2026-001'
        if 'title' in self.fields:
            self.fields['title'].widget.attrs['placeholder'] = 'e.g. Kinematics — Chapter 3 (Live Session)'

        # ── Published At: date-only picker (applied in form) ──
        if 'published_at' in self.fields:
            self.fields['published_at'] = django_forms.DateField(
                required=False,
                widget=django_forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                input_formats=['%Y-%m-%d'],
                label='Published At',
                help_text='Date when the class becomes visible to students.',
            )

        # ── Thumbnail: helpful placeholder ──
        if 'thumbnail_url' in self.fields:
            self.fields['thumbnail_url'].widget.attrs.update({
                'placeholder': 'https://example.com/image.jpg',
            })
            self.fields['thumbnail_url'].help_text = 'Paste a direct image URL. Students see this as the class preview.'

        # ── Allowed Batches: simple multi-select dropdown ──
        from academics.models import Batch
        batch_qs = Batch.objects.filter(status__iexact='ACTIVE').order_by('name')
        batch_choices = [(str(b.id), f'{b.name} ({b.code})') for b in batch_qs]
        self.fields['allowed_batches'] = django_forms.MultipleChoiceField(
            choices=batch_choices,
            required=False,
            widget=django_forms.SelectMultiple(attrs={
                'style': 'width:100%;min-height:120px;',
            }),
            label='Allowed Batches',
            help_text='Hold Ctrl (or Cmd on Mac) to select multiple batches.',
        )
        if self.instance and self.instance.pk:
            current_batches = self.instance.allowed_batches or []
            self.initial['allowed_batches'] = [str(b) for b in current_batches]

        # ── Chapter: prepend "Add Custom" option ──
        if 'chapter' in self.fields:
            from academics.models import Chapter
            chapter_choices = [('', '---------'), ('__custom__', '── Add Custom Chapter ──')]
            for ch in Chapter.objects.filter(status=True).order_by('name'):
                chapter_choices.append((str(ch.id), str(ch)))
            self.fields['chapter'] = django_forms.ChoiceField(
                choices=chapter_choices,
                required=False,
                label='Chapter',
                help_text='Pick an existing chapter or select "Add Custom" to create a new one.',
            )
            if self.instance and self.instance.pk and self.instance.chapter_id:
                self.initial['chapter'] = str(self.instance.chapter_id)

        # ── Topic: prepend "Add Custom" option ──
        if 'topic' in self.fields:
            from academics.models import Topic
            topic_choices = [('', '---------'), ('__custom__', '── Add Custom Topic ──')]
            for tp in Topic.objects.filter(status=True).order_by('name'):
                topic_choices.append((str(tp.id), str(tp)))
            self.fields['topic'] = django_forms.ChoiceField(
                choices=topic_choices,
                required=False,
                label='Topic',
                help_text='Pick an existing topic or select "Add Custom" to create a new one.',
            )
            if self.instance and self.instance.pk and self.instance.topic_id:
                self.initial['topic'] = str(self.instance.topic_id)

        # Pre-select dropdown values for existing instances
        if self.instance and self.instance.pk:
            if 'min_watch_percent_for_present' in self.fields:
                current = getattr(self.instance, 'min_watch_percent_for_present', 70)
                valid_values = [c[0] for c in WATCH_PERCENT_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['min_watch_percent_for_present'] = closest
            if 'auto_attendance_threshold_minutes' in self.fields:
                current = getattr(self.instance, 'auto_attendance_threshold_minutes', 15)
                valid_values = [c[0] for c in THRESHOLD_MINUTE_CHOICES]
                if current not in valid_values:
                    closest = min(valid_values, key=lambda x: abs(x - current))
                    self.initial['auto_attendance_threshold_minutes'] = closest

    def clean_chapter(self):
        """Return None for custom or empty, Chapter instance for valid UUID."""
        val = self.cleaned_data.get('chapter', '')
        if not val or val == '__custom__':
            return None
        from academics.models import Chapter
        try:
            return Chapter.objects.get(pk=val)
        except (Chapter.DoesNotExist, ValueError):
            return None

    def clean_topic(self):
        """Return None for custom or empty, Topic instance for valid UUID."""
        val = self.cleaned_data.get('topic', '')
        if not val or val == '__custom__':
            return None
        from academics.models import Topic
        try:
            return Topic.objects.get(pk=val)
        except (Topic.DoesNotExist, ValueError):
            return None

    def clean_allowed_batches(self):
        return list(self.cleaned_data.get('allowed_batches', []))

    def clean(self):
        cleaned_data = super().clean()
        raw_chapter = self.data.get('chapter', '')
        raw_topic = self.data.get('topic', '')
        custom_chapter = cleaned_data.get('custom_chapter_name', '').strip()
        custom_topic = cleaned_data.get('custom_topic_name', '').strip()

        if raw_chapter == '__custom__' and not custom_chapter:
            self.add_error('custom_chapter_name', 'Please enter the custom chapter name.')
        if raw_topic == '__custom__' and not custom_topic:
            self.add_error('custom_topic_name', 'Please enter the custom topic name.')
        if raw_chapter == '__custom__' and custom_chapter:
            subject_val = cleaned_data.get('subject')
            if not subject_val:
                self.add_error('subject', 'Subject is required when creating a custom chapter.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.allowed_batches = self.cleaned_data.get('allowed_batches', [])

        raw_chapter = self.data.get('chapter', '')
        raw_topic = self.data.get('topic', '')

        if raw_chapter == '__custom__':
            custom_name = self.cleaned_data.get('custom_chapter_name', '').strip()
            if custom_name and instance.tenant_id:
                from academics.models import Subject as AcademicSubject, Chapter
                subject_val = self.cleaned_data.get('subject')
                subject_obj = AcademicSubject.objects.filter(
                    tenant=instance.tenant, subject_type=subject_val
                ).first()
                if not subject_obj:
                    subject_obj = AcademicSubject.objects.create(
                        tenant=instance.tenant,
                        name=subject_val.title() if subject_val else 'General',
                        subject_type=subject_val or 'OTHER',
                    )
                chapter_obj, _ = Chapter.objects.get_or_create(
                    tenant=instance.tenant, subject=subject_obj, name=custom_name,
                    defaults={'status': True},
                )
                instance.chapter = chapter_obj

        if raw_topic == '__custom__':
            custom_name = self.cleaned_data.get('custom_topic_name', '').strip()
            if custom_name and instance.chapter and instance.tenant_id:
                from academics.models import Topic
                topic_obj, _ = Topic.objects.get_or_create(
                    tenant=instance.tenant, chapter=instance.chapter, name=custom_name,
                    defaults={'status': True},
                )
                instance.topic = topic_obj

        if commit:
            instance.save()
            self.save_m2m()
        return instance


# ═══════════════════════════════════════════════════════════════════
# YOUTUBE CHANNEL — Simplified for non-technical admins
# ═══════════════════════════════════════════════════════════════════

@admin.register(YouTubeChannel)
class YouTubeChannelAdmin(EnhancedModelAdmin):
    list_display = ('channel_name', 'channel_id_short', 'status_badge', 'verification_badge', 'primary_badge', 'quota_display')
    list_filter = ('status', 'verification_status', 'primary_channel')
    search_fields = ('channel_name', 'channel_id')
    actions = [export_as_csv, activate_selected, deactivate_selected]
    readonly_fields = ('quota_used_today', 'quota_reset_at', 'last_verified_at', 'created_at', 'updated_at')
    inlines = []

    fieldsets = (
        ('YouTube Channel', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '💡 <b>What is this?</b> Link your YouTube channel here for live class streaming. '
                'You need the <b>Channel ID</b> from YouTube Studio → Settings → Channel → Advanced Settings.'
                '</div>'
            ),
            'fields': ('tenant', 'channel_id', 'channel_name', 'channel_url', 'owned_by_tenant'),
        }),
        ('Status & Settings', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '✅ <b>Active</b> = ready to use &nbsp;|&nbsp; '
                '<b>Inactive</b> = paused &nbsp;|&nbsp; '
                '<b>Revoked</b> = access removed, re-authorize needed'
                '</div>'
            ),
            'fields': ('status', 'verification_status', 'last_verified_at', 'primary_channel', 'assigned_teacher'),
        }),
        ('API Quota (auto-managed)', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '⚠️ YouTube allows ~10,000 API calls/day. These counters are updated automatically. '
                'If quota is exceeded, live streaming pauses until the next day.'
                '</div>'
            ),
            'fields': ('daily_quota_limit', 'quota_used_today', 'quota_reset_at'),
            'classes': ('collapse',),
        }),
        ('OAuth Credentials — Do Not Edit Unless Instructed', {
            'description': (
                '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔒 <b>Sensitive!</b> These are auto-managed. Only edit if instructed by your IT team.'
                '</div>'
            ),
            'fields': ('client_id', 'client_secret', 'scopes', 'access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def channel_id_short(self, obj):
        cid = str(getattr(obj, 'channel_id', ''))
        return format_html(
            '<span style="font-family:monospace;font-size:0.78rem;color:#94a3b8;" title="{}">{}</span>',
            cid, cid[:16] + '…' if len(cid) > 16 else cid
        )
    channel_id_short.short_description = 'Channel ID'

    def verification_badge(self, obj):
        v = getattr(obj, 'verification_status', '')
        if v == 'VERIFIED':
            return format_html('<span style="color:#10b981;font-weight:700;">✓ Verified</span>')
        if v == 'FAILED':
            return format_html('<span style="color:#ef4444;font-weight:700;">✗ Failed</span>')
        return format_html('<span style="color:#f59e0b;">⏳ Pending</span>')
    verification_badge.short_description = 'Verified'

    def primary_badge(self, obj):
        if getattr(obj, 'primary_channel', False):
            return format_html('<span style="color:#f59e0b;font-weight:700;">★ Primary</span>')
        return format_html('<span style="color:#64748b;">—</span>')
    primary_badge.short_description = 'Primary'

    def quota_display(self, obj):
        used = getattr(obj, 'quota_used_today', 0) or 0
        limit = getattr(obj, 'daily_quota_limit', 10000) or 10000
        pct = (used / limit * 100) if limit > 0 else 0
        color = '#10b981' if pct < 50 else '#f59e0b' if pct < 80 else '#ef4444'
        return format_html(
            '<span style="color:{};font-size:0.82rem;font-weight:600;">{}/{} ({}%)</span>',
            color, used, limit, int(pct)
        )
    quota_display.short_description = 'Quota Used'


# ── Inline: recent classes streamed on this channel ──
class ScheduledClassInline(admin.TabularInline):
    model = ScheduledClass
    fk_name = 'youtube_channel'
    fields = ('class_code', 'title', 'scheduled_date', 'start_time', 'status')
    readonly_fields = ('class_code', 'title', 'scheduled_date', 'start_time', 'status')
    extra = 0
    max_num = 0  # read-only, no add
    can_delete = False
    verbose_name = 'Recent Class'
    verbose_name_plural = 'Class History (recent classes on this channel)'
    ordering = ('-scheduled_date',)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-scheduled_date')

    def has_add_permission(self, request, obj=None):
        return False

# YouTubeChannelAdmin.inlines = [ScheduledClassInline]  # disabled — inline causes issues


# ═══════════════════════════════════════════════════════════════════
# SCHEDULED CLASS — Only essential fields visible, rest collapsed
# ═══════════════════════════════════════════════════════════════════

@admin.register(ScheduledClass)
class ScheduledClassAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = ScheduledClassAdminForm
    list_display = (
        'class_code', 'title', 'subject', 'scheduled_date',
        'time_display', 'teacher', 'status_badge', 'live_link',
    )
    list_filter = ('status', 'subject', 'scheduled_date')
    search_fields = ('class_code', 'title', 'teacher__first_name', 'teacher__last_name')
    date_hierarchy = 'scheduled_date'
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]
    readonly_fields = (
        'youtube_broadcast_id', 'youtube_stream_id', 'youtube_stream_key',
        'youtube_stream_url', 'youtube_watch_url', 'youtube_embed_url',
        'youtube_recording_id', 'youtube_recording_url',
        'actual_start_time', 'actual_end_time',
        'peak_live_viewers', 'total_unique_viewers', 'average_watch_duration_seconds', 'total_chat_messages',
        'created_at', 'updated_at',
    )

    fieldsets = (
        ('Class Details', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📚 Fill in the basic class details. Students will see the <b>Title</b>, so keep it descriptive.'
                '</div>'
            ),
            'fields': ('tenant', 'class_code', 'title', 'description', 'teacher', 'batch'),
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'start_time', 'end_time', 'duration_minutes', 'class_timezone'),
        }),
        ('YouTube Streaming', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '▶️ Just pick the <b>channel</b> and <b>privacy</b>. '
                'All other streaming fields are filled automatically.'
                '</div>'
            ),
            'fields': ('youtube_channel', 'privacy_status'),
        }),
        ('Publishing', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📷 <b>Thumbnail</b>: paste a direct image URL (e.g. from Google Drive or Imgur). '
                'Students see this as the class preview image.'
                '</div>'
            ),
            'fields': ('thumbnail_url', 'published_at'),
        }),
        ('Who Can Watch?', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔐 <b>Batch Only</b> = assigned batch only &nbsp;|&nbsp; '
                '<b>Multi-Batch</b> = multiple batches &nbsp;|&nbsp; '
                '<b>All Students</b> = open to everyone &nbsp;|&nbsp; '
                '<b>Custom</b> = hand-pick students'
                '</div>'
            ),
            'fields': ('access_type', 'allowed_batches'),
        }),
        ('Attendance', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📋 <b>Automatic</b> = marks attendance from watch time &nbsp;|&nbsp; '
                '<b>Manual</b> = teacher marks &nbsp;|&nbsp; '
                '<b>Hybrid</b> = system suggests, teacher confirms'
                '</div>'
            ),
            'fields': ('attendance_mode', 'auto_attendance_threshold_minutes', 'min_watch_percent_for_present'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Subject & Curriculum (optional)', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📖 Select an existing chapter/topic <b>or</b> choose '
                '"<b>── Add Custom ──</b>" from the dropdown to create a new one on the fly.'
                '</div>'
            ),
            'fields': (
                'subject', 'chapter', 'custom_chapter_name', 'topic', 'custom_topic_name',
            ),
            'classes': ('collapse',),
        }),

        ('Recurring Template', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔁 Link this class to a <b>Recurring Template</b> to indicate it was auto-generated '
                'from a recurring schedule. If you created this class manually, leave these blank.'
                '</div>'
            ),
            'fields': ('recurring_template', 'is_recurring_instance'),
            'classes': ('collapse',),
        }),

        ('Stream Details (auto-generated — read only)', {
            'description': 'These are filled automatically when the live stream is created. Do not edit.',
            'fields': (
                'youtube_broadcast_id', 'youtube_stream_id', 'youtube_stream_key',
                'youtube_stream_url', 'youtube_watch_url', 'youtube_embed_url',
                'youtube_recording_id', 'youtube_recording_url',
            ),
            'classes': ('collapse',),
        }),
        ('Analytics (auto-generated)', {
            'fields': ('actual_start_time', 'actual_end_time',
                        'peak_live_viewers', 'total_unique_viewers', 'average_watch_duration_seconds', 'total_chat_messages'),
            'classes': ('collapse',),
        }),
        ('Cancellation / Rescheduling', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📝 <b>Reschedule Count</b> tracks how many times this class was moved to a new date/time. '
                'It increments automatically each time you reschedule. A high count may indicate scheduling issues.'
                '</div>'
            ),
            'fields': ('cancellation_reason', 'cancelled_at', 'cancelled_by', 'rescheduled_from', 'reschedule_count'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


    class Media:
        js = ('js/scheduled_class_admin.js',)

    def save_model(self, request, obj, form, change):
        """Auto-capture created_by_id and created_by_type from the logged-in admin user."""
        if not change:  # New object
            obj.created_by_id = str(request.user.pk)
            obj.created_by_type = 'ADMIN'
        super().save_model(request, obj, form, change)

    def time_display(self, obj):
        st = getattr(obj, 'start_time', None)
        et = getattr(obj, 'end_time', None)
        if st:
            parts = str(st)
            if et:
                parts += f' — {et}'
            return format_html('<span style="color:#94a3b8;font-size:0.82rem;">{}</span>', parts)
        return '-'
    time_display.short_description = 'Time'

    def live_link(self, obj):
        url = getattr(obj, 'youtube_watch_url', None) or getattr(obj, 'youtube_embed_url', None)
        if url:
            return format_html(
                '<a href="{}" target="_blank" style="color:#ef4444;text-decoration:none;font-weight:600;">'
                '▶ Live</a>', url
            )
        return format_html('<span style="color:#64748b;">—</span>')
    live_link.short_description = 'Live'


# ═══════════════════════════════════════════════════════════════════
# RECURRING CLASS TEMPLATE — Auto-generate YouTube live sessions
# ═══════════════════════════════════════════════════════════════════


class RecurringClassTemplateAdminForm(django_forms.ModelForm):
    """Custom form for RecurringClassTemplate with multi-select days and searchable batches."""

    class Meta:
        model = RecurringClassTemplate
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ── Recurrence Days: checkbox multi-select ──
        self.fields['recurrence_days'] = django_forms.TypedMultipleChoiceField(
            choices=WEEKDAY_CHOICES,
            coerce=int,
            required=False,
            widget=django_forms.CheckboxSelectMultiple,
            label='Recurrence Days',
            help_text='Select which days of the week this class should repeat on.',
        )
        if self.instance and self.instance.pk:
            self.initial['recurrence_days'] = self.instance.recurrence_days or []

        # ── Allowed Batches: simple multi-select dropdown ──
        from academics.models import Batch
        batch_qs = Batch.objects.filter(status__iexact='ACTIVE').order_by('name')
        batch_choices = [(str(b.id), f'{b.name} ({b.code})') for b in batch_qs]
        self.fields['allowed_batches'] = django_forms.MultipleChoiceField(
            choices=batch_choices,
            required=False,
            widget=django_forms.SelectMultiple(attrs={
                'style': 'width:100%;min-height:120px;',
            }),
            label='Allowed Batches',
            help_text='Hold Ctrl (or Cmd on Mac) to select multiple batches.',
        )
        if self.instance and self.instance.pk:
            current_batches = self.instance.allowed_batches or []
            self.initial['allowed_batches'] = [str(b) for b in current_batches]

        # ── Allowed Students: optional ──
        if 'allowed_students' in self.fields:
            self.fields['allowed_students'].required = False
            self.fields['allowed_students'].help_text = (
                'Optional — only needed for "Custom" access type. Leave empty if not needed.'
            )
            self.fields['allowed_students'].widget.attrs.update({
                'placeholder': '["student-uuid-1", "student-uuid-2"]',
                'rows': 2,
            })

    def clean_recurrence_days(self):
        return [int(d) for d in self.cleaned_data.get('recurrence_days', [])]

    def clean_allowed_batches(self):
        return list(self.cleaned_data.get('allowed_batches', []))

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.recurrence_days = self.cleaned_data.get('recurrence_days', [])
        instance.allowed_batches = self.cleaned_data.get('allowed_batches', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(RecurringClassTemplate)
class RecurringClassTemplateAdmin(EnhancedModelAdmin):
    form = RecurringClassTemplateAdminForm
    list_display = (
        'title', 'class_code_prefix', 'recurrence_badge', 'time_range',
        'teacher', 'batch', 'youtube_channel', 'auto_create_broadcast',
        'is_active', 'last_generated_date', 'total_classes_generated',
    )
    list_filter  = ('is_active', 'recurrence_type', 'subject', 'auto_create_broadcast')
    search_fields = ('title', 'class_code_prefix', 'teacher__first_name', 'teacher__last_name')
    actions = [activate_selected, deactivate_selected, 'trigger_generate_now']

    fieldsets = (
        ('Template Identity', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
                'padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔁 A <b>Recurring Template</b> tells the system to auto-create a new '
                'Scheduled Class (and optionally a YouTube Live broadcast) every day this '
                'pattern is active. Classes are generated each morning at <b>6:00 AM</b> '
                'for the following day.'
                '</div>'
            ),
            'fields': ('tenant', 'title', 'class_code_prefix', 'description'),
        }),
        ('Recurrence Pattern', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;'
                'padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📅 <b>Every Day</b> = Mon–Sun &nbsp;|&nbsp; '
                '<b>Weekdays Only</b> = Mon–Fri &nbsp;|&nbsp; '
                '<b>Specific Days</b> = tick the days below.'
                '</div>'
            ),
            'fields': (
                'recurrence_type', 'recurrence_days',
                'effective_from', 'effective_until', 'is_active',
            ),
        }),
        ('Class Timing', {
            'fields': ('start_time', 'end_time', 'duration_minutes', 'class_timezone'),
        }),
        ('Teacher & Subject', {
            'fields': ('teacher', 'batch', 'subject'),
        }),
        ('YouTube Live Settings', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                'padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '▶️ When <b>Auto-Create Broadcast</b> is on, the system will create a YouTube '
                'Live broadcast automatically <b>N hours before</b> each class starts. '
                'The stream key and watch URL are saved to the generated class.'
                '</div>'
            ),
            'fields': (
                'youtube_channel', 'privacy_status',
                'auto_create_broadcast', 'advance_create_hours',
            ),
        }),
        ('Access Control', {
            'fields': ('access_type', 'allowed_batches', 'allowed_students'),
        }),
        ('Attendance Settings', {
            'fields': (
                'attendance_mode',
                'auto_attendance_threshold_minutes',
                'min_watch_percent_for_present',
            ),
            'classes': ('collapse',),
        }),
        ('Stats (read-only)', {
            'fields': ('last_generated_date', 'total_classes_generated', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('last_generated_date', 'total_classes_generated', 'created_at', 'updated_at')

    # ── Custom display methods ────────────────────────────────────────────────

    def recurrence_badge(self, obj):
        icons = {
            'DAILY':    ('🔁', '#6366f1', 'Every Day'),
            'WEEKDAYS': ('📅', '#0ea5e9', 'Mon–Fri'),
            'WEEKLY':   ('📆', '#f59e0b', 'Specific Days'),
        }
        icon, color, label = icons.get(obj.recurrence_type, ('?', '#94a3b8', obj.recurrence_type))
        extra = ''
        if obj.recurrence_type == 'WEEKLY' and obj.recurrence_days:
            day_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
            days = ', '.join(day_names[d] for d in sorted(obj.recurrence_days) if 0 <= d <= 6)
            extra = f' <span style="color:#64748b;font-size:.75rem;">({days})</span>'
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>{}',
            color, icon, label, extra,
        )
    recurrence_badge.short_description = 'Recurrence'

    def time_range(self, obj):
        return format_html(
            '<span style="font-size:.82rem;color:#64748b;">{} – {}</span>',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M'),
        )
    time_range.short_description = 'Time'

    # ── Admin action: trigger generation immediately ──────────────────────────

    def trigger_generate_now(self, request, queryset):
        """Manually trigger recurring class generation for selected templates right now."""
        from classes.tasks import generate_recurring_classes
        generate_recurring_classes.delay()
        self.message_user(
            request,
            "✅ Recurring class generation task queued. Check back in a moment.",
        )
    trigger_generate_now.short_description = "▶ Trigger class generation now (queues Celery task)"


# ═══════════════════════════════════════════════════════════════════
# CLASS ACCESS TOKEN — Read-heavy, minimal edit
# ═══════════════════════════════════════════════════════════════════

@admin.register(ClassAccessToken)
class ClassAccessTokenAdmin(EnhancedModelAdmin):
    list_display = ('scheduled_class', 'student', 'used_badge', 'revoked_badge', 'expires_at')
    list_filter = ('used', 'revoked')
    search_fields = ('scheduled_class__title', 'student__first_name', 'student__last_name')
    actions = [export_as_csv]
    readonly_fields = ('token', 'used_at', 'used_device', 'used_ip', 'revoked_at', 'created_at')

    fieldsets = (
        ('Access Token', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🎟️ Tokens are auto-generated. To <b>block a student</b>, check "Revoked" and save.'
                '</div>'
            ),
            'fields': ('tenant', 'scheduled_class', 'student', 'expires_at'),
        }),
        ('Revoke Access', {
            'description': 'Check the box below to prevent this student from joining the class.',
            'fields': ('revoked', 'revoked_at', 'revoked_reason'),
        }),
        ('Usage Log (read-only)', {
            'fields': ('token', 'token_meta', 'used', 'used_at', 'used_device', 'used_ip', 'created_at'),
            'classes': ('collapse',),
        }),
        ('Extension', {
            'fields': ('ext_token_1',),
            'classes': ('collapse',),
        }),
    )

    def used_badge(self, obj):
        return colored_status(obj.used)
    used_badge.short_description = 'Used'

    def revoked_badge(self, obj):
        if obj.revoked:
            return format_html('<span style="color:#ef4444;font-weight:600;">🚫 Revoked</span>')
        return format_html('<span style="color:#10b981;">✓ Active</span>')
    revoked_badge.short_description = 'Status'


# ═══════════════════════════════════════════════════════════════════
# CLASS WATCH TIME — Read-only analytics view
# ═══════════════════════════════════════════════════════════════════

@admin.register(ClassWatchTime)
class ClassWatchTimeAdmin(EnhancedModelAdmin):
    list_display = ('scheduled_class', 'student', 'watch_time_display', 'completion_badge', 'live_badge', 'engagement_display')
    list_filter = ('completion_status', 'is_live_watch')
    search_fields = ('scheduled_class__title', 'student__first_name', 'student__last_name')
    actions = [export_as_csv, export_as_json]

    fieldsets = (
        ('Viewing Summary', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📊 This shows how a student watched a class — duration, engagement, and completion. '
                'Used for automatic attendance and engagement reports.'
                '</div>'
            ),
            'fields': ('tenant', 'scheduled_class', 'student', 'session', 'watch_session_id', 'is_live_watch', 'completion_status'),
        }),
        ('Watch Duration', {
            'fields': ('joined_at', 'left_at', 'total_watch_seconds', 'video_progress_percent', 'max_timestamp_reached'),
        }),
        ('Engagement Score', {
            'description': 'Higher score = more attentive student. Tab switches and idle time reduce this.',
            'fields': ('engagement_score', 'tab_switches', 'idle_periods',
                        'chat_messages_sent', 'questions_asked', 'polls_participated'),
            'classes': ('collapse',),
        }),
        ('Detailed Playback (technical)', {
            'fields': ('rewind_count', 'forward_count', 'pause_count', 'playback_speed',
                        'average_quality', 'buffering_count', 'buffering_duration_seconds', 'device', 'device_type'),
            'classes': ('collapse',),
        }),
        ('Extension Fields', {
            'fields': ('watch_meta', 'ext_watch_1', 'ext_watch_2'),
            'classes': ('collapse',),
        }),
    )

    def watch_time_display(self, obj):
        secs = getattr(obj, 'total_watch_seconds', 0) or 0
        if secs >= 3600:
            hrs = secs // 3600
            mins = (secs % 3600) // 60
            return format_html('<span style="font-weight:600;color:#1e293b;">{}h {}m</span>', hrs, mins)
        mins = secs // 60
        remaining = secs % 60
        return format_html('<span style="font-weight:600;color:#1e293b;">{}m {}s</span>', mins, remaining)
    watch_time_display.short_description = 'Watch Time'

    def completion_badge(self, obj):
        s = getattr(obj, 'completion_status', '')
        if s:
            return colored_status(s)
        return '-'
    completion_badge.short_description = 'Completion'

    def live_badge(self, obj):
        if getattr(obj, 'is_live_watch', False):
            return format_html('<span style="color:#ef4444;font-weight:600;">● LIVE</span>')
        return format_html('<span style="color:#64748b;">📼 Recording</span>')
    live_badge.short_description = 'Type'

    def engagement_display(self, obj):
        score = getattr(obj, 'engagement_score', None)
        if score is not None:
            score_float = float(score)
            color = '#10b981' if score_float >= 70 else '#f59e0b' if score_float >= 40 else '#ef4444'
            label = 'High' if score_float >= 70 else 'Medium' if score_float >= 40 else 'Low'
            return format_html(
                '<span style="color:{};font-weight:600;">{}% ({})</span>',
                color, int(score_float), label
            )
        return format_html('<span style="color:#64748b;">—</span>')
    engagement_display.short_description = 'Engagement'


# ═══════════════════════════════════════════════════════════════════
# CLASS LINK CONFIG — Simplified: dropdowns, fewer visible fields
# ═══════════════════════════════════════════════════════════════════

@admin.register(ClassLinkConfigProxy)
class ClassLinkConfigProxyAdmin(EnhancedModelAdmin):
    form = ClassLinkConfigAdminForm
    list_display = (
        'platform_badge', 'tenant', 'active_badge', 'default_badge',
        'auto_gen_badge', 'gen_before', 'duration_display', 'updated_display',
    )
    list_filter = ('platform', 'is_active', 'is_default', 'auto_generate_link')
    search_fields = ('tenant__name',)
    actions = [export_as_csv, activate_selected, deactivate_selected]

    fieldsets = (
        ('Pick a Platform', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🎥 <b>YouTube Live</b> → large audiences, one-way broadcast<br>'
                '<b>Zoom</b> → interactive Q&A, screen sharing<br>'
                '<b>Google Meet</b> → Google Workspace schools<br>'
                '<b>Microsoft Teams</b> → Microsoft 365 schools<br>'
                '<b>Custom URL</b> → any other platform, paste links manually'
                '</div>'
            ),
            'fields': ('tenant', 'platform', 'is_active', 'is_default'),
        }),
        ('Class Defaults', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '⚙️ These defaults apply to all new classes on this platform. Teachers can override per class.'
                '</div>'
            ),
            'fields': ('auto_generate_link', 'generate_minutes_before', 'default_duration_minutes',
                        'auto_record', 'auto_admit_participants'),
        }),
        ('API Credentials (ask your IT team)', {
            'description': (
                '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔒 These connect the system to the platform\'s API. '
                'Skip this section if you chose "Custom URL".'
                '</div>'
            ),
            'fields': ('api_endpoint', 'api_key_reference', 'client_id',
                        'client_secret_reference', 'oauth_token_reference'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def platform_badge(self, obj):
        icons = {
            'YOUTUBE': ('▶', '#ef4444'),
            'ZOOM': ('📹', '#2d8cff'),
            'GOOGLE_MEET': ('📞', '#10b981'),
            'MS_TEAMS': ('👥', '#6264a7'),
            'CUSTOM': ('🔗', '#94a3b8'),
        }
        plat = getattr(obj, 'platform', '')
        icon, color = icons.get(plat, ('🔗', '#94a3b8'))
        label = obj.get_platform_display() if hasattr(obj, 'get_platform_display') else plat
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color, icon, label
        )
    platform_badge.short_description = 'Platform'

    def active_badge(self, obj):
        return colored_status(getattr(obj, 'is_active', False))
    active_badge.short_description = 'Active'

    def default_badge(self, obj):
        if getattr(obj, 'is_default', False):
            return format_html('<span style="color:#f59e0b;font-weight:700;">★ Default</span>')
        return format_html('<span style="color:#64748b;">—</span>')
    default_badge.short_description = 'Default'

    def auto_gen_badge(self, obj):
        if getattr(obj, 'auto_generate_link', False):
            return format_html('<span style="color:#10b981;font-weight:600;">⚡ Auto</span>')
        return format_html('<span style="color:#64748b;">Manual</span>')
    auto_gen_badge.short_description = 'Link Gen'

    def gen_before(self, obj):
        mins = getattr(obj, 'generate_minutes_before', 15)
        return format_html('<span style="color:#94a3b8;font-size:0.82rem;">{}m before</span>', mins)
    gen_before.short_description = 'Generate'

    def duration_display(self, obj):
        dur = getattr(obj, 'default_duration_minutes', 60)
        return format_html('<span style="color:#94a3b8;font-size:0.82rem;">{}min</span>', dur)
    duration_display.short_description = 'Duration'


# ═══════════════════════════════════════════════════════════════════
# YOUTUBE INTEGRATION CONFIG — Shows under Live Classes & YouTube sidebar
# ═══════════════════════════════════════════════════════════════════

@admin.register(IntegrationConfigProxy)
class IntegrationConfigProxyAdmin(EnhancedModelAdmin):
    form = YouTubeIntegrationAdminForm
    list_display = ('name', 'channel_name_display', 'health_badge', 'enabled_badge', 'rate_info', 'updated_at')
    list_filter = ('health_status', 'is_active')
    search_fields = ('name', 'channel_name')
    readonly_fields = ('health_status', 'last_health_check', 'created_at', 'updated_at')

    fieldsets = (
        ('Name & Status', {
            'description': (
                '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📺 <b>Give this integration a name</b> and turn it ON when ready.'
                '</div>'
            ),
            'fields': ('name', 'is_active', 'description'),
        }),
        ('YouTube Channel', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '📺 Enter your YouTube channel details. '
                '<b>How to find Channel ID:</b> YouTube Studio → Settings → Channel → Advanced Settings (starts with "UC").'
                '</div>'
            ),
            'fields': ('channel_id', 'channel_name', 'playlist_ids', 'auto_sync_videos'),
        }),
        ('API Key', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔑 Get your API Key from '
                '<a href="https://console.cloud.google.com/apis/credentials" target="_blank">'
                'Google Cloud Console → Credentials</a>. '
                'Make sure <b>YouTube Data API v3</b> is enabled.'
                '</div>'
            ),
            'fields': ('api_key',),
        }),
        ('OAuth (needed for live streaming)', {
            'description': (
                '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '🔒 Only needed if you want the system to <b>create live streams automatically</b>. '
                'Get Client ID and Secret from Google Cloud Console → OAuth 2.0 Client IDs. '
                'Token fields are auto-managed — do not edit them.'
                '</div>'
            ),
            'fields': ('oauth_client_id', 'oauth_client_secret'),
            'classes': ('collapse',),
        }),
        ('Rate Limits', {
            'description': (
                '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '⚠️ Protects your daily YouTube quota (~10,000 units/day). '
                'The defaults work well for almost everyone.'
                '</div>'
            ),
            'fields': ('max_requests_per_hour', 'max_requests_per_user'),
            'classes': ('collapse',),
        }),
        ('Connection Health (auto-checked)', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 18px;margin-bottom:10px;line-height:1.6;">'
                '💚 <b>Healthy</b> = working &nbsp;|&nbsp; '
                '🟡 <b>Degraded</b> = slow &nbsp;|&nbsp; '
                '🔴 <b>Down</b> = check credentials &nbsp;|&nbsp; '
                '⚪ <b>Unknown</b> = not checked yet'
                '</div>'
            ),
            'fields': ('health_status', 'last_health_check', 'is_verified', 'updated_at', 'created_at'),
            'classes': ('collapse',),
        }),
        ('Internal / Auto-managed (do not edit)', {
            'fields': ('tenant', 'integration_type', 'provider', 'api_endpoint', 'api_secret',
                        'oauth_token', 'oauth_refresh_token', 'oauth_token_expiry',
                        'daily_budget_limit', 'monthly_budget_limit', 'created_by'),
            'classes': ('collapse',),
        }),
        ('LLM Settings (if applicable)', {
            'fields': ('model_name', 'max_tokens', 'temperature', 'system_prompt'),
            'classes': ('collapse',),
        }),
        ('Advanced', {
            'fields': ('webhook_url', 'config_json', 'usage_stats'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        """Show only YouTube integration configs."""
        return super().get_queryset(request).filter(integration_type='YOUTUBE')

    def get_form(self, request, obj=None, **kwargs):
        """Lock integration_type to YOUTUBE and hide it from the form."""
        form = super().get_form(request, obj, **kwargs)
        if 'integration_type' in form.base_fields:
            field = form.base_fields['integration_type']
            field.initial = 'YOUTUBE'
            field.choices = [('YOUTUBE', 'YouTube Channel')]
            field.widget = django_forms.HiddenInput()
        return form

    def save_model(self, request, obj, form, change):
        """Auto-fill technical fields on save."""
        obj.integration_type = 'YOUTUBE'
        obj.provider = 'youtube'
        if not obj.api_endpoint:
            obj.api_endpoint = 'https://www.googleapis.com/youtube/v3'
        super().save_model(request, obj, form, change)

    def channel_name_display(self, obj):
        name = getattr(obj, 'channel_name', '')
        cid = getattr(obj, 'channel_id', '')
        if name:
            return format_html(
                '<span style="font-weight:600;">{}</span>'
                '<br><span style="font-family:monospace;font-size:0.72rem;color:#94a3b8;">{}</span>',
                name, cid or '—'
            )
        return format_html('<span style="color:#64748b;">Not set</span>')
    channel_name_display.short_description = 'Channel'

    def health_badge(self, obj):
        icons = {'HEALTHY': '💚', 'DEGRADED': '🟡', 'DOWN': '🔴', 'UNKNOWN': '⚪'}
        colors = {'HEALTHY': '#22c55e', 'DEGRADED': '#f59e0b', 'DOWN': '#ef4444', 'UNKNOWN': '#64748b'}
        icon = icons.get(obj.health_status, '⚪')
        c = colors.get(obj.health_status, '#64748b')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            c, icon, obj.get_health_status_display()
        )
    health_badge.short_description = 'Health'

    def enabled_badge(self, obj):
        return colored_status(obj.is_active)
    enabled_badge.short_description = 'Enabled'

    def rate_info(self, obj):
        rate = obj.max_requests_per_hour or 100
        return format_html('<span style="color:#64748b;font-size:11px;">{}/hr</span>', rate)
    rate_info.short_description = 'Rate Limit'
