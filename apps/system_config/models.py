"""
LMS Enterprise - System Configuration Models
System settings, feature flags, MFA policies, maintenance windows.
Replaces legacy: info, founder, management_team, live_link, jee_2024
"""
import uuid
from django.db import models
from django.utils import timezone


class SystemSetting(models.Model):
    """Global or per-tenant configuration. Replaces legacy [info]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='system_settings',
        help_text='NULL = global setting'
    )

    setting_key = models.CharField(max_length=200, db_index=True)
    setting_value = models.TextField(null=True, blank=True)
    setting_json = models.JSONField(null=True, blank=True)

    class ValueType(models.TextChoices):
        STRING = 'STRING', 'String'
        INTEGER = 'INTEGER', 'Integer'
        BOOLEAN = 'BOOLEAN', 'Boolean'
        JSON = 'JSON', 'JSON'
        DECIMAL = 'DECIMAL', 'Decimal'

    value_type = models.CharField(max_length=10, choices=ValueType.choices, default=ValueType.STRING)

    category = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_secret = models.BooleanField(default=False)
    is_editable = models.BooleanField(default=True)

    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'setting_key'],
                name='uq_system_setting_key'
            ),
        ]


class FeatureFlag(models.Model):
    """Feature flags for gradual feature rollout."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='feature_flags'
    )

    flag_key = models.CharField(max_length=200)
    flag_name = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(default=0)
    allowed_user_types = models.JSONField(default=list, blank=True)
    allowed_user_ids = models.JSONField(default=list, blank=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feature_flags'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'flag_key'],
                name='uq_feature_flag_key'
            ),
        ]


class MFAPolicy(models.Model):
    """MFA policy configuration."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='mfa_policies')

    class MFAType(models.TextChoices):
        TOTP = 'TOTP', 'Time-based OTP'
        SMS = 'SMS', 'SMS OTP'
        EMAIL = 'EMAIL', 'Email OTP'

    mfa_type = models.CharField(max_length=10, choices=MFAType.choices, default=MFAType.EMAIL)
    is_mandatory = models.BooleanField(default=False)
    applies_to_user_types = models.JSONField(default=list, blank=True)

    otp_length = models.IntegerField(default=6)
    otp_expiry_seconds = models.IntegerField(default=300)
    max_attempts = models.IntegerField(default=5)
    lockout_duration_minutes = models.IntegerField(default=30)
    resend_cooldown_seconds = models.IntegerField(default=60)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'mfa_policies'
        verbose_name_plural = 'MFA policies'


class MaintenanceWindow(models.Model):
    """Scheduled maintenance windows."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    class Scope(models.TextChoices):
        FULL = 'FULL', 'Full Maintenance'
        PARTIAL = 'PARTIAL', 'Partial (Read-Only)'
        FEATURE = 'FEATURE', 'Feature Specific'

    scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.FULL)
    affected_features = models.JSONField(default=list, blank=True)
    notification_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'maintenance_windows'


class FounderInfo(models.Model):
    """Founder / management team. Replaces legacy [founder], [management_team]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='founders')

    class MemberType(models.TextChoices):
        FOUNDER = 'FOUNDER', 'Founder'
        MANAGEMENT = 'MANAGEMENT', 'Management Team'
        ADVISOR = 'ADVISOR', 'Advisor'

    member_type = models.CharField(max_length=15, choices=MemberType.choices, default=MemberType.FOUNDER)
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, null=True, blank=True)
    photo_url = models.URLField(max_length=1000, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    qualifications = models.CharField(max_length=500, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'founder_info'
        ordering = ['sort_order']


class EnquiryForm(models.Model):
    """Contact / enquiry forms. Replaces legacy [enquiry]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='enquiries')

    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    subject = models.CharField(max_length=500, null=True, blank=True)
    message = models.TextField()

    class Source(models.TextChoices):
        WEBSITE = 'WEBSITE', 'Website'
        APP = 'APP', 'Mobile App'
        REFERRAL = 'REFERRAL', 'Referral'
        WALK_IN = 'WALK_IN', 'Walk-in'

    source = models.CharField(max_length=10, choices=Source.choices, default=Source.WEBSITE)

    class EnquiryStatus(models.TextChoices):
        NEW = 'NEW', 'New'
        CONTACTED = 'CONTACTED', 'Contacted'
        CONVERTED = 'CONVERTED', 'Converted'
        CLOSED = 'CLOSED', 'Closed'

    status = models.CharField(max_length=10, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW)

    assigned_to = models.UUIDField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enquiry_forms'
        ordering = ['-created_at']


# ---------------------------------------------------------------------------
# AI Feature Configuration
# ---------------------------------------------------------------------------
class AIFeatureConfig(models.Model):
    """Centralized AI feature configuration for the LMS platform."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='ai_features',
        help_text='NULL = global setting'
    )

    feature_key = models.CharField(
        max_length=100, db_index=True,
        help_text="Unique identifier, e.g. 'ai_summarization'"
    )
    feature_name = models.CharField(max_length=200, help_text="Display name")
    description = models.TextField(null=True, blank=True)

    class FeatureCategory(models.TextChoices):
        CONTENT = 'CONTENT', 'Content Generation'
        ANALYTICS = 'ANALYTICS', 'Analytics & Prediction'
        ASSESSMENT = 'ASSESSMENT', 'Assessment Engine'
        COMMUNICATION = 'COMMUNICATION', 'Communication & Support'
        AUTOMATION = 'AUTOMATION', 'Workflow Automation'

    category = models.CharField(
        max_length=20, choices=FeatureCategory.choices,
        default=FeatureCategory.CONTENT
    )

    is_enabled = models.BooleanField(default=False)

    class IntegrationScope(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        ALL = 'ALL', 'All'

    integration_scope = models.CharField(
        max_length=10, choices=IntegrationScope.choices,
        default=IntegrationScope.ALL,
        help_text='Which dashboard this feature appears on'
    )

    # Provider Configuration
    provider = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="e.g. 'openai', 'google', 'internal'"
    )
    api_endpoint = models.URLField(max_length=500, null=True, blank=True)
    api_key_reference = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='Reference to SystemSetting key holding the API key'
    )

    # Rate Limits
    max_requests_per_hour = models.IntegerField(default=100)
    max_requests_per_user = models.IntegerField(default=20)

    # Metadata
    icon_class = models.CharField(
        max_length=100, default='fas fa-brain',
        help_text='Font Awesome icon class'
    )
    sort_order = models.IntegerField(default=0)
    config_json = models.JSONField(
        default=dict, blank=True,
        help_text='Additional configuration parameters'
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'ai_feature_configs'
        ordering = ['sort_order', 'feature_name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'feature_key'],
                name='uq_ai_feature_key_per_tenant'
            ),
        ]
        verbose_name = 'AI Feature'
        verbose_name_plural = 'AI Features'

    def __str__(self):
        status = 'ON' if self.is_enabled else 'OFF'
        return f"{self.feature_name} [{status}]"


# ---------------------------------------------------------------------------
# Class Scheduling / Link Automation Config
# ---------------------------------------------------------------------------
class ClassLinkConfig(models.Model):
    """Configuration for auto-generating class meeting links (Zoom, Meet, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='class_link_configs'
    )

    class Platform(models.TextChoices):
        YOUTUBE = 'YOUTUBE', 'YouTube Live'
        ZOOM = 'ZOOM', 'Zoom'
        GOOGLE_MEET = 'GOOGLE_MEET', 'Google Meet'
        MICROSOFT_TEAMS = 'MS_TEAMS', 'Microsoft Teams'
        CUSTOM = 'CUSTOM', 'Custom URL'

    platform = models.CharField(
        max_length=15, choices=Platform.choices,
        help_text='Choose the video platform for live classes. '
                  'YouTube Live is recommended for large audiences. '
                  'Zoom/Meet is better for interactive small sessions.'
    )
    is_active = models.BooleanField(
        default=False,
        help_text='Turn ON to enable this platform for live classes. '
                  'Only active platforms can be used to create new class links.'
    )
    is_default = models.BooleanField(
        default=False,
        help_text='Set as the default platform. When a teacher creates a new class, '
                  'this platform will be pre-selected. Only one platform can be default.'
    )

    # API Configuration
    api_endpoint = models.URLField(
        max_length=500, null=True, blank=True,
        help_text='The API URL for this platform. '
                  'YouTube: https://www.googleapis.com/youtube/v3 | '
                  'Zoom: https://api.zoom.us/v2 | '
                  'Leave blank to use the default for each platform.'
    )
    api_key_reference = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='The name of the System Setting that stores your API key. '
                  'Example: "YOUTUBE_API_KEY" or "ZOOM_API_KEY". '
                  'The actual key is stored securely in System Settings.'
    )
    client_id = models.CharField(
        max_length=300, null=True, blank=True,
        help_text='OAuth Client ID for this platform. '
                  'For YouTube/Meet: from Google Cloud Console. '
                  'For Zoom: from Zoom App Marketplace.'
    )
    client_secret_reference = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='The name of the System Setting that stores the client secret. '
                  'Example: "YOUTUBE_CLIENT_SECRET". The secret itself is stored securely.'
    )
    oauth_token_reference = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='The name of the System Setting that stores the OAuth token. '
                  'Example: "YOUTUBE_OAUTH_TOKEN". Usually auto-generated during authorization.'
    )
    webhook_url = models.URLField(
        max_length=500, null=True, blank=True,
        help_text='URL to receive real-time notifications (e.g. when a live stream starts/ends). '
                  'Leave blank if not needed.'
    )

    # Auto-generation settings
    auto_generate_link = models.BooleanField(
        default=False,
        help_text='When ON, the system automatically creates a meeting/stream link '
                  'before each class. When OFF, teachers must paste links manually.'
    )
    generate_minutes_before = models.IntegerField(
        default=15,
        help_text='How many minutes before the class starts should the link be created? '
                  'Recommended: 15 minutes. This gives time for the link to be shared with students.'
    )
    default_duration_minutes = models.IntegerField(
        default=60,
        help_text='Default class length in minutes. Used when creating meetings. '
                  'Teachers can override this for individual classes. Common values: 45, 60, 90.'
    )
    auto_record = models.BooleanField(
        default=False,
        help_text='When ON, live classes are automatically recorded. '
                  'Recordings are saved to the YouTube channel or cloud storage. '
                  'Students can watch them later.'
    )
    auto_admit_participants = models.BooleanField(
        default=True,
        help_text='When ON, students join the class directly without waiting in a lobby. '
                  'When OFF, the teacher must approve each student. '
                  'Recommended ON for large classes, OFF for small private sessions.'
    )

    # Extra config
    config_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_link_configs'
        verbose_name = 'Streaming Platform'
        verbose_name_plural = 'Streaming Platforms'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'platform'],
                name='uq_class_link_platform_per_tenant'
            ),
        ]

    def __str__(self):
        return f"{self.get_platform_display()} - {'Active' if self.is_active else 'Inactive'}"


# ---------------------------------------------------------------------------
# Attendance Rule Configuration
# ---------------------------------------------------------------------------
class AttendanceRule(models.Model):
    """Configurable attendance rules that inherit down to teacher profiles."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='attendance_rules'
    )

    rule_name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    class AppliesTo(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'
        ALL = 'ALL', 'All'

    applies_to = models.CharField(
        max_length=10, choices=AppliesTo.choices, default=AppliesTo.ALL
    )

    # Timing rules
    class_start_grace_minutes = models.IntegerField(
        default=10,
        help_text='Minutes after class start to still mark Present'
    )
    late_threshold_minutes = models.IntegerField(
        default=15,
        help_text='Minutes after which student is marked Late'
    )
    absent_threshold_minutes = models.IntegerField(
        default=30,
        help_text='Minutes after which student is marked Absent'
    )
    min_watch_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=75.00,
        help_text='Minimum % of class to watch for Present status'
    )

    # Auto-attendance from live class
    auto_mark_from_live_class = models.BooleanField(default=True)
    auto_mark_from_biometric = models.BooleanField(default=False)
    auto_mark_from_geofence = models.BooleanField(default=False)

    # Notifications
    notify_absent_student = models.BooleanField(default=True)
    notify_parent_on_absent = models.BooleanField(default=True)
    notify_admin_below_threshold = models.BooleanField(default=True)
    threshold_alert_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=75.00,
        help_text='Alert when attendance drops below this %'
    )

    # Teacher self-attendance
    teacher_self_attendance_required = models.BooleanField(
        default=True,
        help_text='Teachers must mark their own attendance'
    )
    teacher_attendance_auto_from_class = models.BooleanField(
        default=True,
        help_text='Auto-mark teacher present when they start a class'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_rules'
        ordering = ['rule_name']
        verbose_name = 'Attendance Rule'
        verbose_name_plural = 'Attendance Rules'

    def __str__(self):
        return f"{self.rule_name} ({'Active' if self.is_active else 'Inactive'})"


# ---------------------------------------------------------------------------
# Integration Configuration — LLM, AI, YouTube, Third-party APIs
# ---------------------------------------------------------------------------
class IntegrationConfig(models.Model):
    """Manages external service integrations: LLM providers, YouTube channels, APIs."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='integrations',
    )

    class IntegrationType(models.TextChoices):
        LLM = 'LLM', 'LLM / AI Model'
        YOUTUBE = 'YOUTUBE', 'YouTube Channel'
        ZOOM = 'ZOOM', 'Zoom'
        GOOGLE_MEET = 'GOOGLE_MEET', 'Google Meet'
        WHATSAPP = 'WHATSAPP', 'WhatsApp API'
        SMS = 'SMS', 'SMS Gateway'
        EMAIL = 'EMAIL', 'Email Service'
        STORAGE = 'STORAGE', 'Cloud Storage'
        PAYMENT = 'PAYMENT', 'Payment Gateway'
        ANALYTICS = 'ANALYTICS', 'Analytics Platform'
        CUSTOM = 'CUSTOM', 'Custom Integration'

    integration_type = models.CharField(max_length=20, choices=IntegrationType.choices)
    name = models.CharField(
        max_length=200,
        help_text='A friendly name for this integration. For YouTube, use something like '
                  '"Main YouTube Channel" or "Physics Department YouTube".'
    )
    description = models.TextField(
        null=True, blank=True,
        help_text='Optional notes about this integration — e.g. "Used for Class 11 & 12 Physics live streams".'
    )

    # Provider specifics
    provider = models.CharField(
        max_length=100,
        help_text='The service provider name. For YouTube integrations, enter "youtube". '
                  'Other examples: "zoom", "google", "openai".'
    )
    api_endpoint = models.URLField(
        max_length=500, null=True, blank=True,
        help_text='The API URL for this service. For YouTube, use: '
                  'https://www.googleapis.com/youtube/v3  '
                  'Leave blank to use the default.'
    )
    api_key = models.TextField(
        null=True, blank=True,
        help_text='Your API key from the provider (stored encrypted). '
                  'For YouTube: get this from Google Cloud Console → APIs & Services → Credentials.'
    )
    api_secret = models.TextField(
        null=True, blank=True,
        help_text='Your API secret key (stored encrypted). '
                  'Required for some providers. For YouTube, this is usually not needed if you use OAuth.'
    )
    oauth_client_id = models.CharField(
        max_length=300, null=True, blank=True,
        help_text='OAuth Client ID from Google Cloud Console. '
                  'Found under APIs & Services → Credentials → OAuth 2.0 Client IDs. '
                  'Looks like: 123456789-abcdef.apps.googleusercontent.com'
    )
    oauth_client_secret = models.TextField(
        null=True, blank=True,
        help_text='OAuth Client Secret from Google Cloud Console (stored encrypted). '
                  'Found next to the Client ID in your Google Cloud credentials page.'
    )
    oauth_token = models.TextField(
        null=True, blank=True,
        help_text='OAuth access token (auto-generated during authorization). '
                  'This is filled automatically when you connect your YouTube account. '
                  'Do not edit manually unless instructed by support.'
    )
    oauth_refresh_token = models.TextField(
        null=True, blank=True,
        help_text='OAuth refresh token (auto-generated). Used to renew the access token '
                  'when it expires. Do not edit manually.'
    )
    oauth_token_expiry = models.DateTimeField(
        null=True, blank=True,
        help_text='When the current OAuth token expires. The system refreshes tokens automatically.'
    )
    webhook_url = models.URLField(
        max_length=500, null=True, blank=True,
        help_text='URL to receive automatic notifications from the provider. '
                  'For YouTube, this can receive live stream status updates. '
                  'Leave blank if not using webhooks.'
    )

    # LLM-specific
    model_name = models.CharField(max_length=100, null=True, blank=True, help_text='e.g. gpt-4, claude-3')
    max_tokens = models.IntegerField(null=True, blank=True, default=4096)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, default=0.7)
    system_prompt = models.TextField(null=True, blank=True, help_text='Default system prompt for AI')

    # YouTube-specific
    channel_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text='Your YouTube Channel ID. Find it at: YouTube Studio → Settings → Channel → '
                  'Advanced Settings. Looks like: UCxxxxxxxxxxxxxxxxxxxxxxxx'
    )
    channel_name = models.CharField(
        max_length=200, null=True, blank=True,
        help_text='Your YouTube channel\'s display name (e.g. "ABC Academy Live Classes"). '
                  'This is shown to students so they know which channel to watch.'
    )
    playlist_ids = models.JSONField(
        default=list, blank=True,
        help_text='YouTube playlist IDs for organizing recordings. '
                  'Each playlist groups related videos (e.g. one per subject). '
                  'Find IDs in YouTube Studio → Content → Playlists. '
                  'Looks like: PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    )
    auto_sync_videos = models.BooleanField(
        default=False,
        help_text='When enabled, the system will automatically import new videos '
                  'from your YouTube channel. Useful for keeping class recordings in sync.'
    )

    # Rate limiting
    max_requests_per_hour = models.IntegerField(
        default=100,
        help_text='Maximum API calls per hour. YouTube\'s free quota is ~10,000 units/day. '
                  'Keep this at 100 or lower to avoid hitting limits. '
                  'Increase only if you have a paid quota.'
    )
    max_requests_per_user = models.IntegerField(
        default=20,
        help_text='Maximum API calls per user per hour. Prevents a single user '
                  'from consuming too much of the shared quota. Default: 20.'
    )
    daily_budget_limit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Maximum daily spending limit (in your currency). '
                  'Leave blank for YouTube (free tier). Used mainly for paid APIs.'
    )
    monthly_budget_limit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Maximum monthly spending limit. Leave blank for YouTube. '
                  'Useful for paid services like AI/LLM integrations.'
    )

    # Status
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_health_check = models.DateTimeField(null=True, blank=True)

    class HealthStatus(models.TextChoices):
        HEALTHY = 'HEALTHY', 'Healthy'
        DEGRADED = 'DEGRADED', 'Degraded'
        DOWN = 'DOWN', 'Down'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    health_status = models.CharField(max_length=10, choices=HealthStatus.choices, default=HealthStatus.UNKNOWN)

    # Extra config
    config_json = models.JSONField(default=dict, blank=True, help_text='Additional params')
    usage_stats = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'integration_configs'
        ordering = ['integration_type', 'name']

    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        return f"{self.name} ({self.get_integration_type_display()}) [{status}]"


# ---------------------------------------------------------------------------
# Website / Frontend Settings
# ---------------------------------------------------------------------------
class WebsiteSetting(models.Model):
    """Frontend website configuration: homepage, themes, branding."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class SectionType(models.TextChoices):
        HERO = 'HERO', 'Hero Section'
        ABOUT = 'ABOUT', 'About Section'
        PROGRAMS = 'PROGRAMS', 'Programs Section'
        TESTIMONIALS = 'TESTIMONIALS', 'Testimonials'
        FOUNDER = 'FOUNDER', 'Founders & Team'
        FOOTER = 'FOOTER', 'Footer'
        SEO = 'SEO', 'SEO & Meta'
        SOCIAL = 'SOCIAL', 'Social Media Links'
        BRANDING = 'BRANDING', 'Branding & Logo'
        CONTACT = 'CONTACT', 'Contact Info'
        NEWS = 'NEWS', 'News & Updates'
        CUSTOM = 'CUSTOM', 'Custom Section'

    section = models.CharField(max_length=20, choices=SectionType.choices)
    setting_key = models.CharField(max_length=200)
    setting_value = models.TextField(null=True, blank=True)
    setting_json = models.JSONField(default=dict, blank=True)
    media_url = models.URLField(max_length=1000, null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'website_settings'
        ordering = ['section', 'sort_order']
        verbose_name = 'Website Configuration'
        verbose_name_plural = 'Website Configurations'
        constraints = [
            models.UniqueConstraint(fields=['section', 'setting_key'], name='uq_website_section_key'),
        ]

    def __str__(self):
        return f"{self.get_section_display()} — {self.setting_key}"


# ---------------------------------------------------------------------------
# Report Template — for management reporting
# ---------------------------------------------------------------------------
class ReportTemplate(models.Model):
    """Pre-configured report templates for management export."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='report_templates',
    )

    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    class ReportType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student Report'
        TEACHER = 'TEACHER', 'Teacher Report'
        ATTENDANCE = 'ATTENDANCE', 'Attendance Report'
        EXAM = 'EXAM', 'Exam/Test Report'
        CENTER = 'CENTER', 'Center-wise Report'
        FINANCIAL = 'FINANCIAL', 'Financial Report'
        COMBINED = 'COMBINED', 'Combined/Custom Report'

    report_type = models.CharField(max_length=15, choices=ReportType.choices)

    # Filter configuration (saved as JSON)
    filters_json = models.JSONField(
        default=dict, blank=True,
        verbose_name='Report Filters',
        help_text='Filter conditions for the report — like Excel column filters',
    )
    columns_json = models.JSONField(default=list, blank=True, help_text='Selected columns for export')
    group_by = models.JSONField(default=list, blank=True, help_text='Group by fields')
    sort_by = models.JSONField(default=list, blank=True, help_text='Sort fields')

    class ExportFormat(models.TextChoices):
        CSV = 'CSV', 'CSV'
        EXCEL = 'EXCEL', 'Excel'
        PDF = 'PDF', 'PDF'
        JSON = 'JSON', 'JSON'

    default_format = models.CharField(max_length=5, choices=ExportFormat.choices, default=ExportFormat.EXCEL)
    is_scheduled = models.BooleanField(default=False)
    schedule_cron = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='Recurring Schedule',
        help_text='How often this report should be auto-generated',
    )
    recipients_email = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'report_templates'
        ordering = ['report_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


# ---------------------------------------------------------------------------
# News / Priority Announcements for Website
# ---------------------------------------------------------------------------
class WebsiteNews(models.Model):
    """News items and priority announcements for the public website."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='website_news',
    )

    class NewsType(models.TextChoices):
        ANNOUNCEMENT = 'ANNOUNCEMENT', 'Announcement'
        NEWS = 'NEWS', 'News'
        EVENT = 'EVENT', 'Event'
        ALERT = 'ALERT', 'Priority Alert'
        UPDATE = 'UPDATE', 'Update'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, blank=True)
    summary = models.TextField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    news_type = models.CharField(max_length=15, choices=NewsType.choices, default=NewsType.NEWS)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    featured_image = models.URLField(max_length=1000, blank=True, null=True)
    
    # Display options
    show_on_homepage = models.BooleanField(default=True)
    show_as_banner = models.BooleanField(default=False)
    banner_color = models.CharField(max_length=20, default='#2563eb', blank=True)
    
    publish_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'website_news'
        ordering = ['-priority', '-publish_date']
        verbose_name = 'Website News'
        verbose_name_plural = 'Website News'

    def __str__(self):
        return f"{self.title} ({self.get_news_type_display()})"


# ---------------------------------------------------------------------------
# Testimonials for Website
# ---------------------------------------------------------------------------
class Testimonial(models.Model):
    """Testimonials from students/parents for the public website."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='testimonials',
    )

    class AuthorType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        PARENT = 'PARENT', 'Parent'
        TEACHER = 'TEACHER', 'Teacher'
        ALUMNI = 'ALUMNI', 'Alumni'
        OTHER = 'OTHER', 'Other'

    author_name = models.CharField(max_length=200)
    author_type = models.CharField(max_length=10, choices=AuthorType.choices, default=AuthorType.STUDENT)
    author_designation = models.CharField(max_length=200, blank=True, help_text="e.g., 'Class 12 Student', 'JEE Advanced 2025'")
    author_photo = models.URLField(max_length=1000, blank=True, null=True)
    
    content = models.TextField(help_text='Testimonial text')
    rating = models.IntegerField(default=5, help_text='Rating out of 5')
    
    achievement = models.CharField(max_length=300, blank=True, help_text="e.g., 'AIR 45 in JEE Advanced'")
    batch_year = models.CharField(max_length=20, blank=True)
    
    is_featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'testimonials'
        ordering = ['-is_featured', 'sort_order', '-created_at']

    def __str__(self):
        return f"{self.author_name} - {self.get_author_type_display()}"

    @property
    def initials(self):
        parts = self.author_name.split()
        return ''.join(p[0].upper() for p in parts[:2]) if parts else '?'


# ---------------------------------------------------------------------------
# Footer Configuration
# ---------------------------------------------------------------------------
class FooterConfig(models.Model):
    """Footer sections and links for the public website."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='footer_configs',
    )

    class SectionType(models.TextChoices):
        QUICK_LINKS = 'QUICK_LINKS', 'Quick Links'
        RESOURCES = 'RESOURCES', 'Resources'
        CONTACT = 'CONTACT', 'Contact Info'
        SOCIAL = 'SOCIAL', 'Social Media'
        LEGAL = 'LEGAL', 'Legal Links'
        NEWSLETTER = 'NEWSLETTER', 'Newsletter'
        CUSTOM = 'CUSTOM', 'Custom Section'

    section = models.CharField(max_length=20, choices=SectionType.choices)
    section_title = models.CharField(max_length=100)
    
    # For link-based sections
    links_json = models.JSONField(default=list, blank=True, help_text='Array of {label, url, icon?}')
    
    # For contact section
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    contact_address = models.TextField(blank=True)
    
    # For social media
    social_links_json = models.JSONField(default=dict, blank=True, help_text='{facebook, twitter, instagram, youtube, linkedin}')
    
    # For newsletter
    newsletter_text = models.CharField(max_length=200, blank=True)
    
    # Copyright
    copyright_text = models.CharField(max_length=300, blank=True)
    
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'footer_configs'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.section_title} ({self.get_section_display()})"


class TickerItem(models.Model):
    """Individual items for the scrolling stats ticker on the homepage."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='ticker_items',
        help_text='NULL = global ticker item'
    )
    label = models.CharField(max_length=100, help_text='e.g. "Students Enrolled"')
    value = models.CharField(max_length=50, help_text='e.g. "15,000+"')
    icon_class = models.CharField(
        max_length=80, default='fas fa-star',
        help_text='FontAwesome class e.g. "fas fa-user-graduate"'
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ticker_items'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.value} {self.label}"
