"""Test settings — uses an in-memory SQLite DB so tests don't need CREATEDB on PG."""
from .base import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Tests don't need real cache / channels infra.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
}

# Django password hashers — fast variant for tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

DEBUG = False
ALLOWED_HOSTS = ['*']
