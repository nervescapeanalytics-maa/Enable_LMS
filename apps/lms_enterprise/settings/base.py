"""
LMS Enterprise - Base Settings
Common settings shared across all environments.
"""
import os
from pathlib import Path
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # /u01/app/django/apps
PROJECT_DIR = BASE_DIR / 'lms_enterprise'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-this-in-production-lms-enterprise-2026'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1'
).split(',')

# Cloudflare tunnel / reverse proxy settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'drf_spectacular',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
]

LOCAL_APPS = [
    'tenants.apps.TenantsConfig',
    'accounts.apps.AccountsConfig',
    'academics.apps.AcademicsConfig',
    'classes.apps.ClassesConfig',
    'assessments.apps.AssessmentsConfig',
    'attendance.apps.AttendanceConfig',
    'materials.apps.MaterialsConfig',
    'communication.apps.CommunicationConfig',
    'sessions_tracking.apps.SessionsTrackingConfig',
    'audit.apps.AuditConfig',
    'system_config.apps.SystemConfigConfig',
    'realtime.apps.RealtimeConfig',
    'scheduling.apps.SchedulingConfig',
    'promotions.apps.PromotionsConfig',
    'alerts.apps.AlertsConfig',
    'ai_core.apps.AiCoreConfig',
    'core',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + ['django.forms']

# ---------------------------------------------------------------------------
# Authentication Backends (allow admin login with username OR email)
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'accounts.backends.UsernameOrEmailBackend',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'tenants.middleware.TenantMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
    'sessions_tracking.middleware.SessionTrackingMiddleware',
]

ROOT_URLCONF = 'lms_enterprise.urls'

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tenants.context_processors.tenant_context',
                'accounts.context_processors.nav_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'lms_enterprise.wsgi.application'
ASGI_APPLICATION = 'lms_enterprise.asgi.application'

# ---------------------------------------------------------------------------
# Database - PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'LMS_PROD_DB'),
        'USER': os.environ.get('DB_USER', 'lms_app_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=public',
        },
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 600)),
        'CONN_HEALTH_CHECKS': True,
    }
}

# ---------------------------------------------------------------------------
# Cache - Redis
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'{REDIS_URL}/0',
        'KEY_PREFIX': 'lms',
        'TIMEOUT': int(os.environ.get('CACHE_TIMEOUT', 300)),
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'KEY_PREFIX': 'lms_sess',
        'TIMEOUT': int(os.environ.get('SESSION_CACHE_TIMEOUT', 86400)),
    },
}

# ---------------------------------------------------------------------------
# Channel Layers (WebSocket) - Disabled, channels not installed
# ---------------------------------------------------------------------------
# CHANNEL_LAYERS = {}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = os.environ.get('STATIC_ROOT', BASE_DIR / 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.MultiModelJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '10/minute',
        'otp': '5/minute',
    },
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'lms_enterprise.utils.exceptions.custom_exception_handler',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
}

# ---------------------------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# CSRF trusted origins (Cloudflare public domain + local)
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')

# ---------------------------------------------------------------------------
# Logging — 12-factor: all output to stdout/stderr
# In Docker/K8s, logs are collected by the container runtime.
# Set LOG_TO_FILE=true to enable file-based logging (legacy/VM mode).
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_TO_FILE = os.environ.get('LOG_TO_FILE', 'false').lower() in ('true', '1', 'yes')
LOG_DIR = os.environ.get('DJANGO_LOG_DIR', '/app/logs')

_log_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}

if LOG_TO_FILE:
    os.makedirs(LOG_DIR, exist_ok=True)
    _log_handlers.update({
        'file_app': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'application.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'file_audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'audit.log'),
            'maxBytes': 100 * 1024 * 1024,
            'backupCount': 20,
            'formatter': 'json',
        },
        'file_security': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'security.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 20,
            'formatter': 'json',
        },
    })

_django_handlers = ['console', 'file_app'] if LOG_TO_FILE else ['console']
_error_handlers = ['file_error'] if LOG_TO_FILE else ['console']
_audit_handlers = ['file_audit'] if LOG_TO_FILE else ['console']
_security_handlers = ['file_security'] if LOG_TO_FILE else ['console']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': _log_handlers,
    'loggers': {
        'django': {
            'handlers': _django_handlers,
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'django.request': {
            'handlers': _error_handlers,
            'level': 'ERROR',
            'propagate': False,
        },
        'lms': {
            'handlers': _django_handlers,
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'lms.audit': {
            'handlers': _audit_handlers,
            'level': 'INFO',
            'propagate': False,
        },
        'lms.security': {
            'handlers': _security_handlers,
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ---------------------------------------------------------------------------
# LMS Enterprise Custom Settings
# ---------------------------------------------------------------------------
LMS_SETTINGS = {
    # Session limits
    'STUDENT_SESSION_TIMEOUT_HOURS': 24,
    'TEACHER_SESSION_TIMEOUT_HOURS': 24,
    'ADMIN_SESSION_TIMEOUT_HOURS': 4,
    'MAX_CONCURRENT_SESSIONS': 3,

    # OTP
    'OTP_VALIDITY_SECONDS': 300,
    'OTP_MAX_ATTEMPTS': 3,
    'OTP_MAX_REQUESTS_PER_HOUR': 3,
    'OTP_LENGTH': 6,

    # Password
    'PASSWORD_HISTORY_COUNT': 5,
    'ADMIN_PASSWORD_EXPIRY_DAYS': 90,
    'MAX_FAILED_LOGIN_ATTEMPTS': 5,
    'ACCOUNT_LOCKOUT_MINUTES': 30,

    # Class
    'CLASS_MIN_ADVANCE_HOURS': 2,
    'CLASS_ACCESS_TOKEN_BEFORE_MINUTES': 15,
    'CLASS_ACCESS_TOKEN_AFTER_MINUTES': 30,
    'AUTO_ATTENDANCE_THRESHOLD_MINUTES': 15,
    'MIN_WATCH_PERCENT_FOR_PRESENT': 70,

    # Attendance
    'LOW_ATTENDANCE_THRESHOLD': 75,

    # Watch time tracking
    'HEARTBEAT_INTERVAL_SECONDS': 30,

    # YouTube
    'YOUTUBE_DEFAULT_PRIVACY': 'unlisted',
    'YOUTUBE_DAILY_QUOTA_LIMIT': 10000,
}

# ---------------------------------------------------------------------------
# YouTube API Configuration
# ---------------------------------------------------------------------------
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

# ---------------------------------------------------------------------------
# Email Configuration
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes', 'on')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes', 'on')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 15))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@lmsplatform.com')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Distribution lists (comma-separated env vars → python lists)
def _split_dl(name):
    raw = os.environ.get(name, '') or ''
    return [x.strip() for x in raw.split(',') if x.strip()]

DL_ALERTS = _split_dl('DL_ALERTS')
DL_REPORTS = _split_dl('DL_REPORTS')
DL_ADMINS = _split_dl('DL_ADMINS')

# ---------------------------------------------------------------------------
# Celery Configuration
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f'{REDIS_URL}/3')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f'{REDIS_URL}/4')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULE = {}


# ── drf-spectacular API documentation settings (added by remediation) ──
SPECTACULAR_SETTINGS = {
    'TITLE': 'LMS API',
    'DESCRIPTION': 'Learning Management System API Documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
}
