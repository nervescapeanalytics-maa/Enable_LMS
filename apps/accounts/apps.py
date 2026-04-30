from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'accounts'
    verbose_name = 'Identity & User Management'
