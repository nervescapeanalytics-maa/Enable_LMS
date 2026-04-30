#!/bin/sh
set -e

# =============================================================================
# Enable-LMS Enterprise — Docker Entrypoint
# Routes to the correct service based on CMD argument.
# =============================================================================

echo "=== Enable-LMS Enterprise Container Starting ==="
echo "Service : $1"
echo "Env     : ${DJANGO_ENV:-production}"
echo "=========================================="

# ── Wait for dependent services ──────────────────────────────────────────────
wait_for_service() {
    local host="$1" port="$2" name="$3" max_wait="${4:-30}"
    local count=0
    echo "Waiting for ${name} (${host}:${port})..."
    while [ $count -lt $max_wait ]; do
        if python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${host}', ${port})); s.close()" 2>/dev/null; then
            echo "${name} is ready."
            return 0
        fi
        count=$((count + 1))
        sleep 1
    done
    echo "ERROR: ${name} not available after ${max_wait}s"
    return 1
}

# Always wait for database
if [ -n "${DB_HOST:-}" ]; then
    wait_for_service "${DB_HOST}" "${DB_PORT:-5432}" "PostgreSQL" 60
fi

# Always wait for Redis
if [ -n "${REDIS_URL:-}" ]; then
    REDIS_HOST=$(echo "${REDIS_URL}" | sed -E 's|redis://([^:@]+).*|\1|')
    REDIS_PORT=$(echo "${REDIS_URL}" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|; t; c6379')
    wait_for_service "${REDIS_HOST}" "${REDIS_PORT}" "Redis"
fi

# ── Run migrations if requested ──────────────────────────────────────────────
if [ "${RUN_MIGRATIONS:-false}" = "true" ] && [ "$1" = "gunicorn" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput
    echo "Copying static files to shared volume..."
    python manage.py collectstatic --noinput 2>/dev/null || true
fi

# ── Route to the requested service ───────────────────────────────────────────
case "$1" in
    gunicorn)
        echo "Starting Gunicorn (WSGI)..."
        exec gunicorn lms_enterprise.wsgi:application \
            --config /app/gunicorn.conf.py
        ;;

    daphne)
        echo "Starting Daphne (ASGI/WebSocket)..."
        exec daphne \
            --bind 0.0.0.0 \
            --port "${DAPHNE_PORT:-8001}" \
            --proxy-headers \
            --verbosity 1 \
            lms_enterprise.asgi:application
        ;;

    celery-worker)
        echo "Starting Celery Worker..."
        exec celery -A lms_enterprise worker \
            --loglevel="${LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-4}" \
            --max-tasks-per-child="${CELERY_MAX_TASKS_PER_CHILD:-1000}" \
            --without-heartbeat
        ;;

    celery-beat)
        echo "Starting Celery Beat..."
        exec celery -A lms_enterprise beat \
            --loglevel="${LOG_LEVEL:-info}" \
            --schedule=/tmp/celerybeat-schedule
        ;;

    migrate)
        echo "Running migrations..."
        exec python manage.py migrate --noinput
        ;;

    collectstatic)
        echo "Collecting static files..."
        exec python manage.py collectstatic --noinput
        ;;

    shell)
        echo "Starting Django shell..."
        exec python manage.py shell
        ;;

    test)
        echo "Running tests..."
        exec python -m pytest "$@"
        ;;

    *)
        exec "$@"
        ;;
esac
