"""
LMS Enterprise - Production Settings
"""
import os
from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security settings for production
# When behind Cloudflare (HTTPS at edge) + LAN HTTP access, these must be
# configurable.  Cloudflare enforces HTTPS redirect; Django does not need to.
SECURE_SSL_REDIRECT = os.environ.get(
    'SECURE_SSL_REDIRECT', 'false').lower() in ('true', '1', 'yes')
SESSION_COOKIE_SECURE = os.environ.get(
    'SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
CSRF_COOKIE_SECURE = os.environ.get(
    'CSRF_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Production database connection pool
DATABASES['default']['OPTIONS']['connect_timeout'] = 10  # noqa: F405
DATABASES['default']['CONN_MAX_AGE'] = None  # Persistent connections  # noqa: F405

# Session engine - use cache-backed sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# File storage - configure for S3/GCS in production
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
