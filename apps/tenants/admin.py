from django.contrib import admin
from django import forms
from django.utils.html import format_html
from tenants.models import Tenant
from core.admin_utils import EnhancedModelAdmin, ImportExportMixin, export_as_csv, export_as_json, activate_selected, deactivate_selected, colored_status

THEME_PRESETS = {
    'default': {
        'label': 'Default — Navy & White',
        'primary_color': '#1E3A5F',
        'secondary_color': '#FFFFFF',
        'config': {'font': 'Inter', 'border_radius': '8px', 'sidebar': 'dark'},
    },
    'ocean': {
        'label': 'Ocean — Blue & Light Gray',
        'primary_color': '#0369A1',
        'secondary_color': '#F0F9FF',
        'config': {'font': 'Inter', 'border_radius': '10px', 'sidebar': 'dark'},
    },
    'forest': {
        'label': 'Forest — Green & Cream',
        'primary_color': '#166534',
        'secondary_color': '#FEFCE8',
        'config': {'font': 'Poppins', 'border_radius': '8px', 'sidebar': 'dark'},
    },
    'sunset': {
        'label': 'Sunset — Orange & White',
        'primary_color': '#C2410C',
        'secondary_color': '#FFFBEB',
        'config': {'font': 'Inter', 'border_radius': '12px', 'sidebar': 'light'},
    },
    'royal': {
        'label': 'Royal — Purple & Lavender',
        'primary_color': '#6D28D9',
        'secondary_color': '#F5F3FF',
        'config': {'font': 'Poppins', 'border_radius': '10px', 'sidebar': 'dark'},
    },
    'crimson': {
        'label': 'Crimson — Red & White',
        'primary_color': '#B91C1C',
        'secondary_color': '#FFF1F2',
        'config': {'font': 'Inter', 'border_radius': '8px', 'sidebar': 'dark'},
    },
    'slate': {
        'label': 'Slate — Dark Gray & White (Minimal)',
        'primary_color': '#334155',
        'secondary_color': '#F8FAFC',
        'config': {'font': 'Inter', 'border_radius': '6px', 'sidebar': 'dark'},
    },
    'custom': {
        'label': 'Custom (set colors manually below)',
        'primary_color': None,
        'secondary_color': None,
        'config': {},
    },
}

THEME_CHOICES = [(key, preset['label']) for key, preset in THEME_PRESETS.items()]


def _detect_theme(obj):
    """Detect which preset matches the current tenant colors."""
    pc = getattr(obj, 'primary_color', '')
    for key, preset in THEME_PRESETS.items():
        if key == 'custom':
            continue
        if preset['primary_color'] and preset['primary_color'].upper() == (pc or '').upper():
            return key
    return 'custom'


class TenantAdminForm(forms.ModelForm):
    theme_preset = forms.ChoiceField(
        choices=THEME_CHOICES,
        required=False,
        label='Theme',
        help_text='Pick a pre-built colour theme. Choose "Custom" to set your own colours.',
    )

    class Meta:
        model = Tenant
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['theme_preset'].initial = _detect_theme(self.instance)
        else:
            self.fields['theme_preset'].initial = 'default'

    def save(self, commit=True):
        chosen = self.cleaned_data.get('theme_preset', 'custom')
        preset = THEME_PRESETS.get(chosen)
        if preset and chosen != 'custom':
            self.instance.primary_color = preset['primary_color']
            self.instance.secondary_color = preset['secondary_color']
            self.instance.theme_config = preset['config']
        return super().save(commit=commit)


@admin.register(Tenant)
class TenantAdmin(ImportExportMixin, EnhancedModelAdmin):
    form = TenantAdminForm
    list_display = ('code', 'name', 'subdomain_display', 'plan_badge', 'status_badge', 'created_display')
    list_filter = ('status', 'plan_type')
    search_fields = ('code', 'name', 'subdomain', 'custom_domain')
    readonly_fields = ('id', 'created_at', 'updated_at')
    actions = [export_as_csv, export_as_json, activate_selected, deactivate_selected]

    fieldsets = (
        ('Identity', {
            'fields': ('code', 'name', 'legal_name', 'subdomain', 'custom_domain'),
        }),
        ('Theme & Branding', {
            'description': (
                '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                'padding:12px 16px;margin-bottom:10px;line-height:1.6;">'
                '🎨 <b>Select a theme</b> from the dropdown — colours and config will be set '
                'automatically. Choose <b>Custom</b> if you want to enter your own hex codes.</div>'
            ),
            'fields': ('theme_preset', 'logo_url', 'favicon_url',
                        'primary_color', 'secondary_color', 'theme_config'),
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'address', 'city', 'state', 'country'),
        }),
        ('Subscription & Limits', {
            'fields': ('plan_type', 'status', 'max_students', 'max_teachers',
                        'max_storage_gb', 'trial_ends_at', 'subscription_ends_at'),
        }),
        ('Settings', {
            'classes': ('collapse',),
            'fields': ('timezone', 'date_format', 'academic_year_start',
                        'data_retention_days', 'gdpr_enabled', 'features_enabled'),
        }),
        ('YouTube (Advanced)', {
            'classes': ('collapse',),
            'fields': ('youtube_channel_id', 'youtube_channel_name',
                        'youtube_client_id', 'youtube_client_secret',
                        'youtube_refresh_token', 'youtube_quota_limit',
                        'youtube_quota_used', 'youtube_quota_reset_at'),
        }),
        ('System', {
            'classes': ('collapse',),
            'fields': ('id', 'created_at', 'updated_at', 'meta_data',
                        'config_1', 'config_2', 'config_3', 'config_4', 'config_5'),
        }),
    )

    def subdomain_display(self, obj):
        sd = getattr(obj, 'subdomain', '')
        return format_html(
            '<span style="font-family:monospace;font-size:0.82rem;color:#a5b4fc;'
            'padding:2px 8px;background:rgba(99,102,241,0.08);border-radius:6px;">{}</span>',
            sd or '-'
        )
    subdomain_display.short_description = 'Subdomain'

    def plan_badge(self, obj):
        p = getattr(obj, 'plan_type', '')
        colors = {
            'STARTER': '#94a3b8', 'PROFESSIONAL': '#3b82f6',
            'ENTERPRISE': '#f59e0b', 'CUSTOM': '#8b5cf6',
        }
        c = colors.get(p, '#94a3b8')
        return format_html(
            '<span style="padding:2px 8px;border-radius:5px;font-size:0.72rem;'
            'background:{}22;color:{};font-weight:700;">{}</span>',
            c, c, p or '-'
        )
    plan_badge.short_description = 'Plan'
