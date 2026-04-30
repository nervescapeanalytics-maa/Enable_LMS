"""
LMS Enterprise - Tenant Model
Multi-tenant architecture with data isolation.
"""
import uuid
from django.db import models
from django.utils import timezone as django_tz


class Tenant(models.Model):
    """
    Represents an organization/institute on the platform.
    Each tenant has isolated data, own branding, and own YouTube channels.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    code = models.CharField(max_length=50, unique=True, help_text="Unique tenant code e.g. 'INST001'")
    name = models.CharField(max_length=255, help_text="e.g. 'ABC Coaching Institute'")
    legal_name = models.CharField(max_length=500, null=True, blank=True)

    # Domain Configuration
    subdomain = models.CharField(
        max_length=100, unique=True,
        help_text="Subdomain prefix e.g. 'abc' for abc.platform.com"
    )
    custom_domain = models.CharField(
        max_length=255, null=True, blank=True, unique=True,
        help_text="Custom domain e.g. 'www.abccoaching.com'"
    )

    # Branding
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    favicon_url = models.URLField(max_length=500, null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#1E3A5F', help_text="Hex color code")
    secondary_color = models.CharField(max_length=7, default='#FFFFFF', null=True, blank=True)
    theme_config = models.JSONField(default=dict, blank=True)

    # Contact
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default='India')

    # YouTube Configuration
    youtube_channel_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_channel_name = models.CharField(max_length=255, null=True, blank=True)
    youtube_client_id = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_client_secret = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_refresh_token = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_quota_limit = models.IntegerField(default=10000)
    youtube_quota_used = models.IntegerField(default=0)
    youtube_quota_reset_at = models.DateTimeField(null=True, blank=True)

    # Subscription
    class PlanType(models.TextChoices):
        STARTER = 'STARTER', 'Starter'
        PROFESSIONAL = 'PROFESSIONAL', 'Professional'
        ENTERPRISE = 'ENTERPRISE', 'Enterprise'
        CUSTOM = 'CUSTOM', 'Custom'

    plan_type = models.CharField(max_length=20, choices=PlanType.choices, default=PlanType.STARTER)
    max_students = models.IntegerField(default=100)
    max_teachers = models.IntegerField(default=10)
    max_storage_gb = models.IntegerField(default=50)
    features_enabled = models.JSONField(default=dict, blank=True, help_text="Feature flags per tenant")

    # Status
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        TRIAL = 'TRIAL', 'Trial'
        EXPIRED = 'EXPIRED', 'Expired'

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_ends_at = models.DateTimeField(null=True, blank=True)

    # Settings
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY', null=True, blank=True)
    academic_year_start = models.IntegerField(default=4, help_text="Month 1-12")

    # Compliance
    data_retention_days = models.IntegerField(default=365)
    gdpr_enabled = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(default=django_tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Future Extension Columns
    meta_data = models.JSONField(default=dict, blank=True)
    config_1 = models.CharField(max_length=500, null=True, blank=True)
    config_2 = models.CharField(max_length=500, null=True, blank=True)
    config_3 = models.TextField(null=True, blank=True)
    config_4 = models.JSONField(null=True, blank=True)
    config_5 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['name']
        indexes = [
            models.Index(fields=['subdomain'], name='idx_tenant_subdomain'),
            models.Index(fields=['custom_domain'], name='idx_tenant_custom_domain'),
            models.Index(fields=['status'], name='idx_tenant_status'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
