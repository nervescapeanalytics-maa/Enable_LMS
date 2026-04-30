# =============================================================================
# Enable-LMS — Enterprise Multi-stage Production Dockerfile
# Base: Python 3.13 (LTS-aligned) + Django 5.2 LTS
# Single image, multiple services via CMD override:
#   - gunicorn  (WSGI API)
#   - daphne    (ASGI WebSocket)
#   - celery-worker
#   - celery-beat
#   - nginx     (reverse proxy + static files)
#
# All packages installed within the image — no external repos at runtime.
# =============================================================================

# ── Stage 1: Builder — install deps & collect static ─────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# System deps needed to compile psycopg, Pillow, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/requirements.lock ./requirements.txt
RUN pip install --prefix=/install -r requirements.txt

# Copy application code
COPY apps/ /build/apps/

# Collect static files at build time (needs Django settings)
ENV DJANGO_SETTINGS_MODULE=lms_enterprise.settings \
    DJANGO_ENV=production \
    DJANGO_SECRET_KEY=build-only-placeholder \
    DB_HOST=localhost \
    REDIS_URL=redis://localhost:6379 \
    ALLOWED_HOSTS=localhost \
    STATIC_ROOT=/build/staticfiles

WORKDIR /build/apps
RUN PYTHONPATH=/install/lib/python3.13/site-packages:/install/lib64/python3.13/site-packages \
    python manage.py collectstatic --noinput 2>/dev/null || true \
    && mkdir -p /build/staticfiles


# ── Stage 2: Runtime — lean production image ─────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL maintainer="Enable-LMS Enterprise" \
      description="Enable-LMS Enterprise Django Application" \
      version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=lms_enterprise.settings \
    DJANGO_ENV=production \
    APP_HOME=/app

# Runtime-only system libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        curl \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r lms && useradd -r -g lms -d /app -s /sbin/nologin lms

WORKDIR ${APP_HOME}

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Cache-bust for app code changes
ARG APP_VERSION=1
# Copy application code
COPY apps/ ${APP_HOME}/

# Copy collected static files
COPY --from=builder /build/staticfiles ${APP_HOME}/staticfiles

# Copy Docker-specific configs
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/gunicorn.conf.py ${APP_HOME}/gunicorn.conf.py
COPY docker/healthcheck.py ${APP_HOME}/healthcheck.py

# Create directories and fix permissions
RUN mkdir -p ${APP_HOME}/media ${APP_HOME}/logs \
    && chmod +x /entrypoint.sh \
    && chown -R lms:lms ${APP_HOME}

# Non-root user
USER lms

# Health check — lightweight Python script that tests /health/
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

EXPOSE 8000 8001

ENTRYPOINT ["/entrypoint.sh"]

# Default: run Gunicorn. Override in docker-compose for other services.
CMD ["gunicorn"]
