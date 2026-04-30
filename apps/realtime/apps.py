from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'realtime'
    verbose_name = 'Real-Time Events'
