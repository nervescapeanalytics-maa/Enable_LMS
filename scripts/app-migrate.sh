#!/usr/bin/env bash
# =============================================================================
# app-migrate.sh — Export Docker images + application directory to target host
#
# Run this from the SOURCE machine (current app server).
#
# Usage:
#   export TARGET_HOST='root@<target-ip>'
#   bash scripts/app-migrate.sh
#
# What it does:
#   1. Saves Docker images to tar archives
#   2. rsyncs the entire project directory (minus runtime data) to target
#   3. Loads images on target
#   4. Updates target docker/.env with new DB_HOST if needed
#   5. Starts the stack on the target
#
# Prerequisites on TARGET machine:
#   - Docker or Podman + podman-compose / docker compose installed
#   - rsync, ssh key-based access from this machine
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/docker/.env"

[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

TARGET_HOST="${TARGET_HOST:?Set TARGET_HOST=root@<target-ip>}"
TARGET_DIR="${TARGET_DIR:-/u01/app/Enable-LMS}"
TARGET_DB_IP="${TARGET_DB_IP:-$DB_HOST}"    # override if DB is on a third machine

IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-}"

APP_IMAGE="${IMAGE_REGISTRY}enable-lms:${IMAGE_TAG}"
NGINX_IMAGE="${IMAGE_REGISTRY}enable-lms-nginx:${IMAGE_TAG}"

STAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_ARCHIVE="/tmp/enable-lms-images-${STAMP}.tar"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')] INFO  ${NC} $*"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] OK    ${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN  ${NC} $*"; }
die()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR ${NC} $*" >&2; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Detect container engine (docker or podman)
# ─────────────────────────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    CENGINE=docker
elif command -v podman &>/dev/null; then
    CENGINE=podman
else
    die "Neither docker nor podman found"
fi
info "Container engine: $CENGINE"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Save images to archive
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 1: Saving images to archive ==="
info "Images to export:"
info "  ${APP_IMAGE}"
info "  ${NGINX_IMAGE}"
info "  redis:7-alpine"
info "  cloudflare/cloudflared:latest"

$CENGINE save \
    "$APP_IMAGE" \
    "$NGINX_IMAGE" \
    redis:7-alpine \
    cloudflare/cloudflared:latest \
    | gzip > "${IMAGE_ARCHIVE}.gz"

ARCHIVE_SIZE=$(du -sh "${IMAGE_ARCHIVE}.gz" | cut -f1)
ok "Image archive saved: ${IMAGE_ARCHIVE}.gz (${ARCHIVE_SIZE})"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Rsync project directory (exclude runtime data & caches)
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 2: Syncing project directory to target ==="
info "Source: ${PROJECT_DIR}"
info "Target: ${TARGET_HOST}:${TARGET_DIR}"

ssh -o StrictHostKeyChecking=accept-new "$TARGET_HOST" "mkdir -p ${TARGET_DIR}"

rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    --exclude='.git/' \
    --exclude='runtime/redis/' \
    --exclude='runtime/static/' \
    --exclude='runtime/media/' \
    --exclude='apps/__pycache__/' \
    --exclude='apps/**/__pycache__/' \
    --exclude='apps/**/*.pyc' \
    --exclude='apps/.env' \
    --exclude='docker/.env' \
    --exclude='docker/.env.bak' \
    "${PROJECT_DIR}/" \
    "${TARGET_HOST}:${TARGET_DIR}/"

ok "Project directory synced"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Transfer image archive to target
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 3: Transferring image archive to target ==="
rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    "${IMAGE_ARCHIVE}.gz" \
    "${TARGET_HOST}:/tmp/"

ok "Image archive transferred"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Load images on target, configure .env, start stack
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 4: Loading images and starting stack on target ==="

ssh "$TARGET_HOST" bash <<REMOTE
set -euo pipefail

# Detect engine on target
if command -v docker &>/dev/null; then CE=docker; elif command -v podman &>/dev/null; then CE=podman; else echo "ERROR: no container engine on target"; exit 1; fi
echo "Target container engine: \$CE"

# Load images
echo "Loading images from archive..."
gunzip -c "/tmp/${IMAGE_ARCHIVE##*/}.gz" | \$CE load
echo "Images loaded:"
\$CE images | grep -E "enable-lms|redis|cloudflared"

# Create runtime dirs (bind mounts expected by compose)
mkdir -p ${TARGET_DIR}/runtime/media
mkdir -p ${TARGET_DIR}/runtime/static
mkdir -p ${TARGET_DIR}/runtime/redis

# Write .env from .env.example, then patch DB_HOST
if [[ ! -f "${TARGET_DIR}/docker/.env" ]]; then
    cp "${TARGET_DIR}/docker/.env.example" "${TARGET_DIR}/docker/.env"
    echo "Created docker/.env from template — REVIEW IT before starting!"
fi

# Patch DB_HOST to point at the new DB server
sed -i "s|^DB_HOST=.*|DB_HOST=${TARGET_DB_IP}|" "${TARGET_DIR}/docker/.env"
echo "DB_HOST in docker/.env set to: ${TARGET_DB_IP}"

echo ""
echo "=== Stack is ready. Start it manually after reviewing .env: ==="
echo "  cd ${TARGET_DIR}/docker"
echo "  \$CE compose up -d"
REMOTE

ok "Target setup complete"

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup local archive
# ─────────────────────────────────────────────────────────────────────────────
rm -f "${IMAGE_ARCHIVE}.gz"
info "Local image archive removed"

echo ""
echo "============================================================"
ok "Application migration complete!"
echo ""
echo "  Project dir on target : ${TARGET_DIR}"
echo "  DB_HOST on target     : ${TARGET_DB_IP}"
echo ""
warn "ACTION REQUIRED on target machine:"
warn "  1. Edit ${TARGET_DIR}/docker/.env — fill in secrets (SECRET_KEY, DB_PASSWORD, CLOUDFLARE_TUNNEL_TOKEN)"
warn "  2. cd ${TARGET_DIR}/docker && docker compose up -d"
warn "  3. Verify: docker compose ps && docker compose logs api"
echo "============================================================"
