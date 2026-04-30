"""
LMS Enterprise - Development Settings
"""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Add browsable API renderer
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# Disable throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []  # noqa: F405

# CORS - allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# CSRF trusted origins for frontend
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.1.113:8000',
]

# Session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Channel layers disabled - channels not installed
# CHANNEL_LAYERS = {}

# Simpler cache for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# SQLite database for development when PostgreSQL is not available
import os
if os.environ.get('USE_SQLITE', 'false').lower() == 'true':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
        }
    }
