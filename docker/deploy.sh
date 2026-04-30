#!/bin/bash
# =============================================================================
# Enable-LMS Enterprise — Deployment Script for New Servers
#
# Usage:
#   1. Copy the Enable-LMS/ directory to the new server
#   2. cp docker/.env.example docker/.env  &&  edit docker/.env
#   3. bash docker/deploy.sh [build|pull|migrate|up|down|logs|status|push]
#
# Prerequisites:
#   - Docker Engine 24+ (or Podman 4+) with docker compose plugin
#   - Network access to external PostgreSQL
#   - Cloudflare tunnel token (from Zero Trust dashboard)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Load env
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Run: cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
    exit 1
fi
set -a; source "$ENV_FILE"; set +a

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-lms}"
COMPOSE="docker compose -f $COMPOSE_FILE -p $PROJECT_NAME"

# ── Helpers ──────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;36m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
err()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

wait_healthy() {
    local url="$1" max="${2:-60}" i=0
    info "Waiting for $url to become healthy..."
    while [[ $i -lt $max ]]; do
        if curl -sf --max-time 3 "$url" >/dev/null 2>&1; then
            ok "Healthy after ${i}s"
            return 0
        fi
        i=$((i+1)); sleep 1
    done
    err "Not healthy after ${max}s"; return 1
}

# ── Commands ─────────────────────────────────────────────────────────────────
cmd_build() {
    info "Building images locally..."
    $COMPOSE build --build-arg APP_VERSION="$(date +%s)" api
    $COMPOSE build nginx
    ok "Images built"
}

cmd_pull() {
    info "Pulling images from registry (IMAGE_REGISTRY=${IMAGE_REGISTRY:-<local>})..."
    $COMPOSE pull
    ok "Images pulled"
}

cmd_push() {
    local registry="${IMAGE_REGISTRY:?Set IMAGE_REGISTRY in .env first}"
    local tag="${IMAGE_TAG:-latest}"
    info "Tagging and pushing to ${registry}..."
    docker tag enable-lms:"$tag" "${registry}enable-lms:$tag"
    docker tag enable-lms-nginx:"$tag" "${registry}enable-lms-nginx:$tag"
    docker push "${registry}enable-lms:$tag"
    docker push "${registry}enable-lms-nginx:$tag"
    ok "Pushed to $registry"
}

cmd_migrate() {
    info "Running database migrations..."
    $COMPOSE --profile tools run --rm migrate
    ok "Migrations complete"
}

cmd_up() {
    info "Starting stack..."
    $COMPOSE up -d
    sleep 5
    wait_healthy "http://localhost:${HTTP_PORT:-8080}/health/"
    cmd_status
}

cmd_down() {
    info "Stopping stack..."
    $COMPOSE down
    ok "Stack stopped"
}

cmd_logs() {
    $COMPOSE logs -f --tail=50 "${2:-}"
}

cmd_status() {
    echo ""
    info "Container status:"
    $COMPOSE ps
    echo ""
    info "Health check:"
    curl -s "http://localhost:${HTTP_PORT:-8080}/health/" | python3 -m json.tool 2>/dev/null || err "Health endpoint unreachable"
    echo ""
    info "Tunnel status:"
    $COMPOSE logs tunnel 2>&1 | grep -E "Registered|ERR" | tail -4
}

cmd_rollback() {
    local prev="${1:?Usage: deploy.sh rollback <previous-tag>}"
    info "Rolling back to tag: $prev"
    IMAGE_TAG="$prev" $COMPOSE up -d api websocket celery-worker celery-beat
    wait_healthy "http://localhost:${HTTP_PORT:-8080}/health/"
}

# ── Full deploy (new server) ────────────────────────────────────────────────
cmd_deploy() {
    info "=== Full Deployment ==="
    echo ""

    # Step 1: Build or pull
    if [[ -n "${IMAGE_REGISTRY:-}" ]]; then
        cmd_pull
    else
        cmd_build
    fi

    # Step 2: Migrate
    cmd_migrate

    # Step 3: Start
    cmd_up

    echo ""
    ok "=== Deployment Complete ==="
    echo ""
    echo "  Local:  http://localhost:${HTTP_PORT:-8080}/health/"
    echo "  Public: Update Cloudflare tunnel origin to http://nginx:80"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────
case "${1:-deploy}" in
    build)    cmd_build ;;
    pull)     cmd_pull ;;
    push)     cmd_push ;;
    migrate)  cmd_migrate ;;
    up)       cmd_up ;;
    down)     cmd_down ;;
    logs)     cmd_logs "$@" ;;
    status)   cmd_status ;;
    rollback) cmd_rollback "${2:-}" ;;
    deploy)   cmd_deploy ;;
    *)        echo "Usage: $0 {build|pull|push|migrate|up|down|logs|status|rollback|deploy}" ;;
esac
