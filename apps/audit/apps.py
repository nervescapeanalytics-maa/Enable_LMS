from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'audit'
    verbose_name = 'Audit & Compliance'
