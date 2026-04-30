from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'tenants'
    verbose_name = 'Multi-Tenancy'
