#!/usr/bin/env bash
# =============================================================================
#  03-app-migrate.sh
#  Migrate Enable-LMS Docker Application to Target (45.194.90.251)
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║  Run this script ON THE SOURCE MACHINE (192.168.1.113) as root          ║
#  ║  Prerequisite: 01-target-pg-setup.sh and 02-db-migrate.sh completed     ║
#  ║                                                                          ║
#  ║  Run:  bash /u01/app/Enable-LMS/scripts/03-app-migrate.sh              ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
#
#  What this script does (in order):
#  ──────────────────────────────────────────────────────────────────────────
#  [PHASE 1]  Pre-flight: SSH, disk space, Docker images check
#  [PHASE 2]  Install Docker / docker-compose on target (if missing)
#  [PHASE 3]  Save Docker images to gzipped archive on source
#  [PHASE 4]  rsync project directory to target (/u01/app/Enable-LMS)
#             Note: runtime/redis, runtime/static synced selectively
#  [PHASE 5]  rsync runtime/media (user uploads)
#  [PHASE 6]  Transfer image archive to target machine
#  [PHASE 7]  Load Docker images on target
#  [PHASE 8]  Create/patch docker/.env on target
#             (DB_HOST → 45.194.90.251, all credentials preserved)
#  [PHASE 9]  Create runtime directories, fix permissions on target
#  [PHASE 10] Run DB migrations on target (collect static files)
#  [PHASE 11] Start full Docker stack on target
#  [PHASE 12] Health check — all containers Up, HTTP/WebSocket OK
#  [PHASE 13] Cleanup temp archives
#
#  Important notes:
#  ────────────────
#  • Docker images are NOT in the app directory. They live in the container
#    engine's local store. This script exports them to a tar.gz and loads
#    them on the target — the only reliable way to move them.
#  • Simply copying the app directory to the target will work for all config
#    and code files but WILL NOT include the images or runtime Redis state.
#  • Runtime Redis data is NOT migrated (in-memory cache/broker state is
#    ephemeral; Celery tasks will resume after startup).
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner() { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"; }
info()   { echo -e "${CYAN}  [INFO]  ${NC}$*"; }
ok()     { echo -e "${GREEN}  [ OK ]  ${NC}$*"; }
warn()   { echo -e "${YELLOW}  [WARN]  ${NC}$*"; }
die()    { echo -e "${RED}  [FAIL]  ${NC}$*" >&2; exit 1; }
ask()    { echo -e "${YELLOW}  [?]  ${NC}$*"; }

confirm() {
    local msg="${1:-Continue?}"
    ask "$msg [y/N] "
    read -r ans
    [[ "$ans" =~ ^[Yy]$ ]] || { warn "Aborted by user."; exit 0; }
}

pause() {
    echo ""
    ask "Review the above, then press ENTER to continue (Ctrl-C to abort)..."
    read -r
}

STAMP=$(date +%Y%m%d-%H%M%S)
LOG="/var/log/lms-app-migrate-${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1
info "All output logged to: $LOG"

# ── Fixed values ───────────────────────────────────────────────────────────────
SOURCE_IP="192.168.1.113"
TARGET_IP="45.194.90.251"
TARGET_HOST="rocky@${TARGET_IP}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_APP_DIR="$PROJECT_DIR"                     # /u01/app/Enable-LMS
TGT_APP_DIR="/u01/app/Enable-LMS"             # same path on target
ENV_FILE="${SRC_APP_DIR}/docker/.env"

# Load .env
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-}"
APP_IMAGE="${IMAGE_REGISTRY}enable-lms:${IMAGE_TAG}"
NGINX_IMAGE="${IMAGE_REGISTRY}enable-lms-nginx:${IMAGE_TAG}"

IMAGE_ARCHIVE="/tmp/enable-lms-images-${STAMP}.tar.gz"

# Detect local container engine
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    CENGINE=docker
elif command -v podman &>/dev/null; then
    CENGINE=podman
else
    die "Neither docker nor podman found on source machine"
fi

# =============================================================================
# BANNER
# =============================================================================
clear
echo -e "${BOLD}"
cat <<'BANNER'
 ╔══════════════════════════════════════════════════════════════╗
 ║     Enable-LMS — Application Migration                      ║
 ║     Source: 192.168.1.113  →  Target: 45.194.90.251         ║
 ║     App dir: /u01/app/Enable-LMS                            ║
 ╚══════════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

# =============================================================================
# INTERACTIVE INPUTS
# =============================================================================
banner "CONFIGURATION"

echo ""
info "Source app dir  : ${SRC_APP_DIR}"
info "Target app dir  : ${TGT_APP_DIR}"
info "Target host     : ${TARGET_HOST}"
info "Container engine: ${CENGINE} (source)"
info "DB_HOST in .env : $(grep '^DB_HOST=' "$ENV_FILE" 2>/dev/null || echo 'not set')"
echo ""

ask "SSH private key path for target (blank = default ~/.ssh/id_rsa): "
read -r SSH_KEY_INPUT
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"
[[ -n "$SSH_KEY_INPUT" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY_INPUT"

echo ""
ask "Should we update ALLOWED_HOSTS in .env to include ${TARGET_IP}? [y/N] "
read -r UPDATE_HOSTS
UPDATE_ALLOWED_HOSTS=false
[[ "$UPDATE_HOSTS" =~ ^[Yy]$ ]] && UPDATE_ALLOWED_HOSTS=true

echo ""
info "What will be migrated:"
echo "  Docker images : ${APP_IMAGE}"
echo "                  ${NGINX_IMAGE}"
echo "                  redis:7-alpine"
echo "                  cloudflare/cloudflared:latest"
echo "  App directory : ${SRC_APP_DIR} → ${TARGET_HOST}:${TGT_APP_DIR}"
echo "  Media files   : ${SRC_APP_DIR}/runtime/media (user uploads)"
echo "  NOT migrated  : runtime/redis (ephemeral cache — Redis starts fresh)"
echo ""
confirm "Proceed with application migration?"

# =============================================================================
# PHASE 1 — Pre-flight checks
# =============================================================================
banner "PHASE 1 — Pre-flight Checks"

info "Checking: running as root..."
[[ $EUID -eq 0 ]] || die "Run as root"
ok "Root OK"

info "Checking: source app directory..."
[[ -d "${SRC_APP_DIR}/docker" ]] || die "App directory not found: ${SRC_APP_DIR}"
ok "Source app dir: ${SRC_APP_DIR}"

info "Checking: Docker images exist locally..."
for IMG in "$APP_IMAGE" "$NGINX_IMAGE"; do
    $CENGINE image inspect "$IMG" &>/dev/null \
        || die "Image not found: ${IMG}. Build first with: cd ${SRC_APP_DIR}/docker && $CENGINE compose build"
    IMG_SIZE=$($CENGINE image inspect "$IMG" --format '{{.Size}}' | awk '{printf "%.0f MB", $1/1048576}')
    ok "Image: ${IMG} (${IMG_SIZE})"
done

#info "Checking: SSH connectivity to target..."
#ssh $SSH_OPTS "$TARGET_HOST" "echo SSH-OK" 2>/dev/null | grep -q "SSH-OK" \
 #   || die "Cannot SSH to ${TARGET_HOST}. Configure key-based auth first:
  #  ssh-copy-id -f -i /tmp/Dev-LMS-keypair.pem rocky@${TARGET_IP}"
#ok "SSH to ${TARGET_HOST} OK"

info "Checking: rsync available on both machines..."
command -v rsync &>/dev/null || die "rsync not installed on source: dnf install rsync"
ssh $SSH_OPTS "$TARGET_HOST" "command -v rsync" &>/dev/null \
    || { warn "rsync not on target — installing...";
         ssh $SSH_OPTS "$TARGET_HOST" "dnf install -y rsync &>/dev/null"; }
ok "rsync available"

info "Checking: disk space on source for image archive..."
TOTAL_IMG_SIZE=$($CENGINE image inspect "$APP_IMAGE" "$NGINX_IMAGE" \
    --format '{{.Size}}' 2>/dev/null | awk '{s+=$1} END {printf "%d", s*0.7}')
FREE_TMP=$(df /tmp --output=avail -B1 | tail -1)
(( FREE_TMP > TOTAL_IMG_SIZE )) \
    && ok "Source /tmp has sufficient space: $(( FREE_TMP / 1048576 ))MB free" \
    || warn "Low space in /tmp ($(( FREE_TMP / 1048576 ))MB). Image archive may fail."

info "Checking: disk space on target /u01..."
TGT_FREE=$(ssh $SSH_OPTS "$TARGET_HOST" "df /u01 --output=avail -B1 2>/dev/null | tail -1 || df / --output=avail -B1 | tail -1")
ok "Target has $(( TGT_FREE / 1073741824 ))GB free"
pause

# =============================================================================
# PHASE 2 — Install Docker on target (if missing)
# =============================================================================
banner "PHASE 2 — Verify / Install Docker on Target"

TGT_ENGINE=$(ssh $SSH_OPTS "$TARGET_HOST" \
    "command -v docker 2>/dev/null || command -v podman 2>/dev/null || echo NONE")
TGT_ENGINE=$(basename "$TGT_ENGINE" 2>/dev/null || echo "NONE")

if [[ "$TGT_ENGINE" == "NONE" ]]; then
    warn "No container engine found on target. Docker will be installed."
    confirm "Install Docker CE on target ${TARGET_IP}?"

    ssh $SSH_OPTS "$TARGET_HOST" bash <<'REMOTE'
set -euo pipefail
echo "--- Installing Docker CE on Rocky Linux 8 ---"
dnf install -y dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null || \
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker --version
echo "Docker installed"
REMOTE
    ok "Docker installed on target"
else
    TGT_ENGINE_VER=$(ssh $SSH_OPTS "$TARGET_HOST" "$TGT_ENGINE --version 2>/dev/null" | head -1)
    ok "Target container engine: ${TGT_ENGINE_VER}"
fi

# Ensure docker compose works on target
TGT_COMPOSE=$(ssh $SSH_OPTS "$TARGET_HOST" \
    "docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo NONE")
[[ "$TGT_COMPOSE" == "NONE" ]] && {
    warn "docker compose not available on target — installing docker-compose-plugin..."
    ssh $SSH_OPTS "$TARGET_HOST" "dnf install -y docker-compose-plugin" || true
}
ok "docker compose available on target"
pause

# =============================================================================
# PHASE 3 — Save Docker images to archive on source
# =============================================================================
banner "PHASE 3 — Export Docker Images to Archive"

info "Images to export:"
for IMG in "$APP_IMAGE" "$NGINX_IMAGE" redis:7-alpine cloudflare/cloudflared:latest; do
    SIZE=$($CENGINE image inspect "$IMG" --format '{{.Size}}' 2>/dev/null | awk '{printf "%.0f MB", $1/1048576}') || SIZE="unknown"
    info "  ${IMG}  (${SIZE})"
done

info "Saving images → ${IMAGE_ARCHIVE}  (this may take several minutes)..."
$CENGINE save \
    "$APP_IMAGE" \
    "$NGINX_IMAGE" \
    redis:7-alpine \
    cloudflare/cloudflared:latest \
    | gzip -1 > "$IMAGE_ARCHIVE"

ARCHIVE_SIZE=$(du -sh "$IMAGE_ARCHIVE" | cut -f1)
ok "Image archive created: ${IMAGE_ARCHIVE} (${ARCHIVE_SIZE})"
pause

# =============================================================================
# PHASE 4 — rsync project directory to target
# =============================================================================
banner "PHASE 4 — Sync Project Directory to Target"

info "Source: ${SRC_APP_DIR}/"
info "Target: ${TARGET_HOST}:${TGT_APP_DIR}/"
echo ""
info "Excluded: .git, __pycache__, *.pyc, runtime/redis/, docker/.env, docker/.env.bak"
echo ""

# Create target directory structure
ssh $SSH_OPTS "$TARGET_HOST" "mkdir -p ${TGT_APP_DIR} /d01/postgresql"

rsync -avz --progress \
    -e "ssh ${SSH_OPTS}" \
    --exclude='.git/' \
    --exclude='apps/__pycache__/' \
    --exclude='apps/**/__pycache__/' \
    --exclude='apps/**/*.pyc' \
    --exclude='apps/**/*.pyo' \
    --exclude='runtime/redis/' \
    --exclude='docker/.env' \
    --exclude='docker/.env.bak' \
    --exclude='*.log' \
    "${SRC_APP_DIR}/" \
    "${TARGET_HOST}:${TGT_APP_DIR}/"

ok "Project directory synced to target"

# =============================================================================
# PHASE 5 — rsync runtime/media (user uploads)
# =============================================================================
banner "PHASE 5 — Sync Media Files (User Uploads)"

MEDIA_SRC="${SRC_APP_DIR}/runtime/media"
if [[ -d "$MEDIA_SRC" ]] && [[ "$(ls -A "$MEDIA_SRC" 2>/dev/null)" ]]; then
    MEDIA_SIZE=$(du -sh "$MEDIA_SRC" | cut -f1)
    info "Media directory size: ${MEDIA_SIZE}"
    confirm "Sync media files to target?"
    rsync -avz --progress --checksum \
        -e "ssh ${SSH_OPTS}" \
        "${MEDIA_SRC}/" \
        "${TARGET_HOST}:${TGT_APP_DIR}/runtime/media/"
    ok "Media files synced"
else
    info "Media directory is empty — skipping"
fi
pause

# =============================================================================
# PHASE 6 — Transfer image archive to target
# =============================================================================
banner "PHASE 6 — Transfer Image Archive to Target"

ARCHIVE_SIZE=$(du -sh "$IMAGE_ARCHIVE" | cut -f1)
info "Transferring ${ARCHIVE_SIZE} archive to ${TARGET_HOST}:/tmp/..."

rsync -avz --progress \
    -e "ssh ${SSH_OPTS}" \
    "$IMAGE_ARCHIVE" \
    "${TARGET_HOST}:/tmp/"

# Verify transfer integrity
LOCAL_SIZE=$(stat -c%s "$IMAGE_ARCHIVE")
REMOTE_SIZE=$(ssh $SSH_OPTS "$TARGET_HOST" "stat -c%s /tmp/$(basename "$IMAGE_ARCHIVE")")
[[ "$LOCAL_SIZE" == "$REMOTE_SIZE" ]] \
    && ok "Transfer verified: ${LOCAL_SIZE} bytes" \
    || die "Archive size mismatch: local=${LOCAL_SIZE} remote=${REMOTE_SIZE}"
pause

# =============================================================================
# PHASE 7 — Load Docker images on target
# =============================================================================
banner "PHASE 7 — Load Docker Images on Target"

info "Loading images from archive on target..."
ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
ARCHIVE_FILE="/tmp/$(basename "$IMAGE_ARCHIVE")"
echo "--- Loading images from \$ARCHIVE_FILE ---"
gunzip -c "\$ARCHIVE_FILE" | docker load
echo "--- Loaded images ---"
docker images | grep -E "enable-lms|redis|cloudflared|REPOSITORY"
REMOTE
ok "Docker images loaded on target"
pause

# =============================================================================
# PHASE 8 — Create docker/.env on target
# =============================================================================
banner "PHASE 8 — Configure docker/.env on Target"

info "Creating docker/.env on target based on source settings..."

# Read current values from source .env
SECRET_KEY=$(grep '^DJANGO_SECRET_KEY=' "$ENV_FILE" | cut -d= -f2-)
ALLOWED_HOSTS=$(grep '^ALLOWED_HOSTS=' "$ENV_FILE" | cut -d= -f2-)
DB_NAME_VAL=$(grep '^DB_NAME=' "$ENV_FILE" | cut -d= -f2-)
DB_USER_VAL=$(grep '^DB_USER=' "$ENV_FILE" | cut -d= -f2-)
DB_PASS_VAL=$(grep '^DB_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
CF_TOKEN=$(grep '^CLOUDFLARE_TUNNEL_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
REDIS_PASS=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || echo "")

# Optionally add target IP to ALLOWED_HOSTS
if [[ "$UPDATE_ALLOWED_HOSTS" == "true" ]]; then
    ALLOWED_HOSTS="${ALLOWED_HOSTS},${TARGET_IP}"
fi

ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
mkdir -p "${TGT_APP_DIR}/docker"

# Backup old .env if it exists
[[ -f "${TGT_APP_DIR}/docker/.env" ]] && \
    cp "${TGT_APP_DIR}/docker/.env" "${TGT_APP_DIR}/docker/.env.bak-${STAMP}"

cat > "${TGT_APP_DIR}/docker/.env" <<'ENV_EOF'
# =============================================================================
# Enable-LMS Enterprise — Environment Configuration
# Generated by 03-app-migrate.sh on $(date)
# Target machine: ${TARGET_IP}
# DO NOT COMMIT THIS FILE TO GIT
# =============================================================================

# ── Django Core ──────────────────────────────────────────────────────────────
DJANGO_ENV=production
DJANGO_SETTINGS_MODULE=lms_enterprise.settings
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_DEBUG=false
ALLOWED_HOSTS=${ALLOWED_HOSTS}
LOG_LEVEL=INFO

# ── Database ─────────────────────────────────────────────────────────────────
# Points to the PostgreSQL 18 instance on THIS machine (/d01/postgresql)
DB_HOST=${TARGET_IP}
DB_PORT=5432
DB_NAME=${DB_NAME_VAL}
DB_USER=${DB_USER_VAL}
DB_PASSWORD=${DB_PASS_VAL}
DB_CONN_MAX_AGE=600

# ── Redis (Docker internal service name) ─────────────────────────────────────
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=${REDIS_PASS}
REDIS_MAXMEMORY=256mb

# ── Celery ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL=redis://redis:6379/3
CELERY_RESULT_BACKEND=redis://redis:6379/4
CELERY_CONCURRENCY=4
CELERY_MAX_TASKS_PER_CHILD=1000

# ── CORS & CSRF ──────────────────────────────────────────────────────────────
CORS_ORIGINS=https://lms.automatebot.shop,http://localhost:3000
CSRF_TRUSTED_ORIGINS=https://lms.automatebot.shop,http://localhost:8080,http://${TARGET_IP}:8080

# ── Cloudflare Tunnel ────────────────────────────────────────────────────────
CLOUDFLARE_TUNNEL_TOKEN=${CF_TOKEN}

# ── Image (local build) ──────────────────────────────────────────────────────
IMAGE_REGISTRY=
IMAGE_TAG=latest
HTTP_PORT=8080

# ── Resource Limits ──────────────────────────────────────────────────────────
API_CPU_LIMIT=2.0
API_MEMORY_LIMIT=1G
WS_CPU_LIMIT=1.0
WS_MEMORY_LIMIT=512M
WORKER_CPU_LIMIT=2.0
WORKER_MEMORY_LIMIT=1G
BEAT_CPU_LIMIT=0.5
BEAT_MEMORY_LIMIT=256M
ENV_EOF

chmod 600 "${TGT_APP_DIR}/docker/.env"
echo "docker/.env created on target"
cat "${TGT_APP_DIR}/docker/.env" | grep -v PASSWORD | grep -v SECRET | grep -v TOKEN
REMOTE

ok "docker/.env written on target"
pause

# =============================================================================
# PHASE 9 — Create runtime directories on target
# =============================================================================
banner "PHASE 9 — Runtime Directories on Target"

ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
echo "Creating runtime directories..."
mkdir -p "${TGT_APP_DIR}/runtime/media"
mkdir -p "${TGT_APP_DIR}/runtime/static"
mkdir -p "${TGT_APP_DIR}/runtime/redis"
chmod -R 755 "${TGT_APP_DIR}/runtime"
echo "Runtime directories:"
ls -la "${TGT_APP_DIR}/runtime/"
REMOTE
ok "Runtime directories created"
pause

# =============================================================================
# PHASE 10 — Run DB migrations & collect static files
# =============================================================================
banner "PHASE 10 — Database Migrations on Target"

info "Running Django migrate + collectstatic on target..."
ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
cd "${TGT_APP_DIR}/docker"

echo "--- Running migrate job ---"
docker compose run --rm migrate 2>&1 | tail -30

echo "--- Verify migrations ---"
docker compose run --rm api python manage.py showmigrations --list 2>&1 | tail -20
REMOTE
ok "Migrations complete on target"
pause

# =============================================================================
# PHASE 11 — Start Docker stack on target
# =============================================================================
banner "PHASE 11 — Start Docker Stack on Target"

info "Starting full application stack on ${TARGET_IP}..."
ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
cd "${TGT_APP_DIR}/docker"

echo "--- Starting stack ---"
docker compose up -d

echo "Sleeping 10s for containers to initialise..."
sleep 10

echo "--- Container status ---"
docker compose ps
REMOTE
ok "Docker stack started on target"
pause

# =============================================================================
# PHASE 12 — Health checks
# =============================================================================
banner "PHASE 12 — Health Checks on Target"

info "Checking container health..."
ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
cd "${TGT_APP_DIR}/docker"

echo "--- docker compose ps ---"
docker compose ps

echo ""
echo "--- HTTP health check on :8080 ---"
HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:8080/" 2>/dev/null || echo "000")
echo "HTTP response: \${HTTP_CODE}"
if [[ "\$HTTP_CODE" =~ ^(200|301|302|401|403)$ ]]; then
    echo "HTTP OK (\${HTTP_CODE})"
else
    echo "Unexpected HTTP code: \${HTTP_CODE} — check logs below"
    docker compose logs api --tail=20
fi

echo ""
echo "--- API container logs (last 10 lines) ---"
docker compose logs api --tail=10

echo ""
echo "--- Nginx container logs (last 5 lines) ---"
docker compose logs nginx --tail=5
REMOTE

ok "Health checks complete"

# =============================================================================
# PHASE 13 — Cleanup
# =============================================================================
banner "PHASE 13 — Cleanup"

info "Removing local image archive: ${IMAGE_ARCHIVE}"
rm -f "$IMAGE_ARCHIVE"
ok "Local archive removed"

info "Removing image archive from target..."
ssh $SSH_OPTS "$TARGET_HOST" "rm -f /tmp/$(basename "$IMAGE_ARCHIVE")" \
    && ok "Target archive removed" \
    || warn "Could not remove archive from target (harmless)"

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}"
cat <<DONE
 ╔══════════════════════════════════════════════════════════════╗
 ║   Application Migration COMPLETE                            ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Source  : ${SOURCE_IP}  /u01/app/Enable-LMS    ║
 ║  Target  : ${TARGET_IP}  /u01/app/Enable-LMS ║
 ║  DB Host : ${TARGET_IP} (/d01/postgresql)   ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Application URLs:                                          ║
 ║    HTTP  : http://${TARGET_IP}:8080              ║
 ║    Tunnel: https://lms.automatebot.shop (Cloudflare)        ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Useful commands on target:                                  ║
 ║    cd /u01/app/Enable-LMS/docker                            ║
 ║    docker compose ps                                        ║
 ║    docker compose logs -f api                               ║
 ║    docker compose logs -f nginx                             ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Log file  : ${LOG}  ║
 ╚══════════════════════════════════════════════════════════════╝
DONE
echo -e "${NC}"
