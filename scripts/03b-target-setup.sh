#!/usr/bin/env bash
# =============================================================================
#  03b-target-setup.sh  ← RUN THIS ON TARGET MACHINE (45.194.90.251)
#
#  Enable-LMS — Application Setup (Part 2 of 2)
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║  MACHINE : TARGET  45.194.90.251  (Rocky Linux 8)                       ║
#  ║  Run as  : root                                                          ║
#  ║  Command : bash /opt/lms-export/03b-target-setup.sh                     ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║  PREREQUISITE: The following files must already be in /opt/lms-export/  ║
#  ║    lms-images.tar.gz    (Docker images)                                 ║
#  ║    lms-app.tar.gz       (Application files)                             ║
#  ║    lms-dot-env          (docker/.env for this machine)                  ║
#  ║    lms-checksums.sha256 (for integrity verification)                    ║
#  ║                                                                          ║
#  ║  Also prerequisite: 01-target-pg-setup.sh and 02-db-migrate.sh done     ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
#
#  Phases:
#  ───────
#  [PHASE 1]  Pre-flight checks (root, OS, files present, checksums)
#  [PHASE 2]  Install Docker CE (if not installed)
#  [PHASE 3]  Verify checksums of transferred files
#  [PHASE 4]  Extract application files → /u01/app/Enable-LMS
#  [PHASE 5]  Load Docker images from archive
#  [PHASE 6]  Place docker/.env (from lms-dot-env)
#  [PHASE 7]  Create runtime directories + permissions
#  [PHASE 8]  Tag images (localhost/ prefix compatibility)
#  [PHASE 9]  Run DB migrations + collectstatic
#  [PHASE 10] Start full Docker stack
#  [PHASE 11] Health checks
#  [PHASE 12] Cleanup /opt/lms-export archives
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner() { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"; }
info()   { echo -e "${CYAN}  [INFO]  ${NC}$*"; }
ok()     { echo -e "${GREEN}  [ OK ]  ${NC}$*"; }
warn()   { echo -e "${YELLOW}  [WARN]  ${NC}$*"; }
die()    { echo -e "${RED}  [FAIL]  ${NC}$*" >&2; exit 1; }
ask()    { echo -e "${YELLOW}  [?]  ${NC}$*"; }

confirm() {
    ask "$1 [y/N] "
    read -r ans
    [[ "$ans" =~ ^[Yy]$ ]] || { warn "Aborted by user."; exit 0; }
}

pause() {
    echo ""
    ask "Press ENTER to continue (Ctrl-C to abort)..."
    read -r
}

# ── Logging ────────────────────────────────────────────────────────────────────
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p /var/log
LOG="/var/log/lms-target-setup-${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1
info "Logging to: $LOG"

# ── Fixed paths ────────────────────────────────────────────────────────────────
TARGET_IP="45.194.90.251"
EXPORT_DIR="/opt/lms-export"
IMAGE_ARCHIVE="${EXPORT_DIR}/lms-images.tar.gz"
APP_ARCHIVE="${EXPORT_DIR}/lms-app.tar.gz"
ENV_FILE="${EXPORT_DIR}/lms-dot-env"
CHECKSUM_FILE="${EXPORT_DIR}/lms-checksums.sha256"
APP_DIR="/u01/app/Enable-LMS"

# =============================================================================
clear
echo -e "${BOLD}"
cat <<'BANNER'
 ╔══════════════════════════════════════════════════════════════╗
 ║   Enable-LMS — Part 2/2: TARGET Setup                      ║
 ║   Machine: 45.194.90.251  (Rocky Linux 8)                   ║
 ║   Reads from: /opt/lms-export/                              ║
 ╚══════════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

echo ""
info "App install dir : $APP_DIR"
info "Import dir      : $EXPORT_DIR"
echo ""

# =============================================================================
# PHASE 1 — Pre-flight
# =============================================================================
banner "PHASE 1 — Pre-flight Checks"

info "Checking: running as root..."
[[ $EUID -eq 0 ]] || die "Must run as root: sudo bash $0"
ok "Running as root"

info "Checking: OS..."
OS_VER=$(grep -oP '(?<=^VERSION_ID=")[^"]+' /etc/os-release 2>/dev/null || echo "0")
MAJOR="${OS_VER%%.*}"
info "Detected OS major version: $MAJOR"
[[ "$MAJOR" == "8" ]] || warn "Expected Rocky/RHEL 8, found: $MAJOR — continuing anyway"
ok "OS check passed"

info "Checking: required export files..."
MISSING=()
for f in "$IMAGE_ARCHIVE" "$APP_ARCHIVE" "$ENV_FILE"; do
    if [[ ! -f "$f" ]]; then
        MISSING+=("$f")
    else
        SZ=$(du -sh "$f" | cut -f1)
        ok "Found: $f  ($SZ)"
    fi
done

if (( ${#MISSING[@]} > 0 )); then
    die "Missing required files:\n$(printf '  %s\n' "${MISSING[@]}")\n\nRun 03a-source-export.sh on source (192.168.1.113) first, then transfer files:\n  scp 192.168.1.113:/opt/lms-export/*.{tar.gz,sha256} /opt/lms-export/\n  scp 192.168.1.113:/opt/lms-export/lms-dot-env /opt/lms-export/"
fi

info "Checking: disk space..."
FREE_GB=$(df /u01 --output=avail -B1 2>/dev/null | tail -1 | awk '{printf "%d", $1/1073741824}' || \
          df /    --output=avail -B1             | tail -1 | awk '{printf "%d", $1/1073741824}')
ok "Free space: ${FREE_GB} GB"
(( FREE_GB < 3 )) && warn "Less than 3 GB free — may be tight for images + app"

echo ""
confirm "Proceed with target setup?"
pause

# =============================================================================
# PHASE 2 — Install Docker CE
# =============================================================================
banner "PHASE 2 — Install Docker CE"

if command -v docker &>/dev/null; then
    DVER=$(docker --version 2>/dev/null)
    ok "Docker already installed: $DVER"

    # Make sure dockerd is running
    if ! systemctl is-active docker &>/dev/null; then
        info "Starting Docker service..."
        systemctl enable --now docker
        ok "Docker started"
    fi
else
    warn "Docker not found. Installing Docker CE for Rocky Linux 8..."
    confirm "Install Docker CE now?"

    info "Adding Docker CE repo..."
    dnf install -y dnf-plugins-core 2>&1 | tail -3

    # Try RHEL repo first, fall back to CentOS
    dnf config-manager \
        --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null || \
    dnf config-manager \
        --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    info "Installing Docker packages..."
    dnf install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin \
        2>&1 | grep -E "install|already|error|ERROR|Running" | tail -15

    systemctl enable --now docker
    ok "Docker CE installed: $(docker --version)"
fi

# Check docker compose
if docker compose version &>/dev/null 2>&1; then
    ok "docker compose: $(docker compose version 2>/dev/null | head -1)"
elif command -v docker-compose &>/dev/null; then
    ok "docker-compose: $(docker-compose --version)"
else
    warn "docker compose plugin not found — installing..."
    dnf install -y docker-compose-plugin 2>&1 | tail -5 || \
        pip3 install docker-compose 2>/dev/null || \
        warn "Could not install docker compose — install manually before Phase 9"
fi
pause

# =============================================================================
# PHASE 3 — Verify checksums
# =============================================================================
banner "PHASE 3 — Verify File Integrity (Checksums)"

if [[ -f "$CHECKSUM_FILE" ]]; then
    info "Verifying SHA-256 checksums..."
    cd "$EXPORT_DIR"
    if sha256sum --check "$CHECKSUM_FILE" 2>&1; then
        ok "All checksums verified — files are intact"
    else
        warn "One or more checksum mismatches detected."
        warn "The file may be corrupted during transfer."
        confirm "Continue anyway? (Not recommended if sizes differ)"
    fi
else
    warn "Checksum file not found ($CHECKSUM_FILE) — skipping integrity check"
    warn "If transfer was interrupted, files may be corrupt."
    confirm "Continue without checksum verification?"
fi
pause

# =============================================================================
# PHASE 4 — Extract application files
# =============================================================================
banner "PHASE 4 — Extract Application Files → $APP_DIR"

info "Creating base directory structure..."
mkdir -p /u01/app
mkdir -p /u01/app/Enable-LMS

if [[ -d "$APP_DIR/docker" ]]; then
    warn "Application directory already exists at $APP_DIR"
    confirm "Overwrite? (Existing files will be replaced, .env is handled separately)"
fi

info "Extracting $APP_ARCHIVE → /u01/app/ ..."
tar -xzf "$APP_ARCHIVE" -C /u01/app/ 2>&1

ok "Application extracted to: $APP_DIR"
info "Contents:"
ls -la "$APP_DIR"
pause

# =============================================================================
# PHASE 5 — Load Docker images
# =============================================================================
banner "PHASE 5 — Load Docker Images"

IMG_SIZE=$(du -sh "$IMAGE_ARCHIVE" | cut -f1)
info "Loading images from $IMAGE_ARCHIVE  ($IMG_SIZE)"
info "This may take 3-8 minutes..."
echo ""

gunzip -c "$IMAGE_ARCHIVE" | docker load 2>&1

echo ""
ok "Images loaded. Current image list:"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}' | \
    grep -E "enable-lms|redis|cloudflared|REPOSITORY" || true
pause

# =============================================================================
# PHASE 6 — Place docker/.env
# =============================================================================
banner "PHASE 6 — Configure docker/.env"

TGT_ENV="${APP_DIR}/docker/.env"

if [[ -f "$TGT_ENV" ]]; then
    cp "$TGT_ENV" "${TGT_ENV}.bak-${STAMP}"
    warn "Backed up existing .env → ${TGT_ENV}.bak-${STAMP}"
fi

cp "$ENV_FILE" "$TGT_ENV"
chmod 600 "$TGT_ENV"

ok "docker/.env installed at: $TGT_ENV"
info "Current DB_HOST setting:"
grep "^DB_HOST=" "$TGT_ENV"
info "Current ALLOWED_HOSTS:"
grep "^ALLOWED_HOSTS=" "$TGT_ENV"
echo ""
info "(Full .env shown below with secrets redacted)"
grep -v -E "PASSWORD|SECRET_KEY|TOKEN" "$TGT_ENV" | grep -v "^#" | grep .
pause

# =============================================================================
# PHASE 7 — Runtime directories
# =============================================================================
banner "PHASE 7 — Create Runtime Directories"

info "Creating bind-mount directories expected by docker-compose.yml..."
mkdir -p "${APP_DIR}/runtime/media"
mkdir -p "${APP_DIR}/runtime/static"
mkdir -p "${APP_DIR}/runtime/redis"
chmod 755 "${APP_DIR}/runtime"
chmod 755 "${APP_DIR}/runtime/media"
chmod 755 "${APP_DIR}/runtime/static"
chmod 755 "${APP_DIR}/runtime/redis"

ok "Runtime directories created:"
ls -la "${APP_DIR}/runtime/"
pause

# =============================================================================
# PHASE 8 — Tag images for docker compose compatibility
# =============================================================================
banner "PHASE 8 — Tag Images for docker-compose.yml"

info "docker-compose.yml uses 'enable-lms:latest' and 'enable-lms-nginx:latest'"
info "Checking if tags already exist or need aliasing..."

# Check if images are available under expected names
for IMG in "enable-lms:latest" "localhost/enable-lms:latest"; do
    if docker image inspect "$IMG" &>/dev/null 2>&1; then
        ok "Found: $IMG"
        FOUND_APP_IMG="$IMG"
        break
    fi
done

for IMG in "enable-lms-nginx:latest" "localhost/enable-lms-nginx:latest"; do
    if docker image inspect "$IMG" &>/dev/null 2>&1; then
        ok "Found: $IMG"
        FOUND_NGINX_IMG="$IMG"
        break
    fi
done

# If loaded as localhost/enable-lms but compose uses enable-lms, add tag
if docker image inspect "localhost/enable-lms:latest" &>/dev/null 2>&1 && \
   ! docker image inspect "enable-lms:latest" &>/dev/null 2>&1; then
    docker tag "localhost/enable-lms:latest" "enable-lms:latest"
    ok "Tagged: localhost/enable-lms:latest → enable-lms:latest"
fi

if docker image inspect "localhost/enable-lms-nginx:latest" &>/dev/null 2>&1 && \
   ! docker image inspect "enable-lms-nginx:latest" &>/dev/null 2>&1; then
    docker tag "localhost/enable-lms-nginx:latest" "enable-lms-nginx:latest"
    ok "Tagged: localhost/enable-lms-nginx:latest → enable-lms-nginx:latest"
fi

# redis
if docker image inspect "docker.io/library/redis:7-alpine" &>/dev/null 2>&1 && \
   ! docker image inspect "redis:7-alpine" &>/dev/null 2>&1; then
    docker tag "docker.io/library/redis:7-alpine" "redis:7-alpine"
    ok "Tagged: docker.io/library/redis:7-alpine → redis:7-alpine"
fi

info "Final image list:"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | \
    grep -E "enable-lms|redis|cloudflared|REPOSITORY" || true
pause

# =============================================================================
# PHASE 9 — DB migrations + collectstatic
# =============================================================================
banner "PHASE 9 — Database Migrations"

info "Running Django migrate (connects to PostgreSQL at DB_HOST in .env)..."
cd "${APP_DIR}/docker"

# Show which DB_HOST will be used
DB_H=$(grep "^DB_HOST=" "$TGT_ENV" | cut -d= -f2)
info "DB_HOST = $DB_H"

# Run migrate job (defined in docker-compose.yml under 'profiles: [tools]')
docker compose run --rm migrate 2>&1 || {
    warn "migrate command failed — trying alternative..."
    docker compose run --rm api python manage.py migrate 2>&1
}

ok "Migrations complete"

info "Collecting static files..."
docker compose run --rm api python manage.py collectstatic --noinput 2>&1 | tail -5
ok "Static files collected"
pause

# =============================================================================
# PHASE 10 — Start Docker stack
# =============================================================================
banner "PHASE 10 — Start Docker Stack"

info "Starting all services..."
cd "${APP_DIR}/docker"
docker compose up -d 2>&1

info "Waiting 15 seconds for containers to initialise..."
sleep 15

info "Container status:"
docker compose ps
pause

# =============================================================================
# PHASE 11 — Health checks
# =============================================================================
banner "PHASE 11 — Health Checks"

info "1) Checking all containers are Up..."
NOT_UP=$(docker compose ps --format json 2>/dev/null | \
    python3 -c "
import sys,json
data=sys.stdin.read().strip()
rows = json.loads('[' + data.replace('}\n{','},{') + ']') if data else []
down=[r.get('Name','?') for r in rows if 'Up' not in str(r.get('State',''))]
print('\n'.join(down))
" 2>/dev/null || echo "")

if [[ -z "$NOT_UP" ]]; then
    ok "All containers are Up"
else
    warn "These containers are NOT running: $NOT_UP"
    warn "Check logs: docker compose logs <service-name>"
fi

info "2) HTTP check on port 8080..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 15 \
    "http://localhost:8080/" 2>/dev/null || echo "000")
info "HTTP response code: $HTTP_CODE"
if [[ "$HTTP_CODE" =~ ^(200|301|302|401|403)$ ]]; then
    ok "HTTP response OK ($HTTP_CODE)"
else
    warn "Unexpected HTTP code: $HTTP_CODE"
    warn "Check nginx logs: docker compose logs nginx --tail=30"
fi

info "3) API container DB connectivity..."
docker compose exec -T api python manage.py dbshell -- \
    -c "SELECT COUNT(*) FROM django_migrations;" 2>/dev/null \
    && ok "DB reachable from API container" \
    || warn "DB check failed — check: docker compose logs api --tail=30"

echo ""
info "Useful log commands:"
echo "  docker compose logs -f api"
echo "  docker compose logs -f nginx"
echo "  docker compose logs -f celery-worker"

# =============================================================================
# PHASE 12 — Cleanup
# =============================================================================
banner "PHASE 12 — Cleanup"

echo ""
ask "Remove export archives from /opt/lms-export/ to free disk space? [y/N] "
read -r CLEAN_ANS
if [[ "$CLEAN_ANS" =~ ^[Yy]$ ]]; then
    rm -f "$IMAGE_ARCHIVE" "$APP_ARCHIVE"
    ok "Archives removed (lms-dot-env and checksums kept for reference)"
else
    info "Archives kept in $EXPORT_DIR"
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}"
cat <<DONE
 ╔══════════════════════════════════════════════════════════════╗
 ║   TARGET SETUP COMPLETE                                     ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  App dir    : /u01/app/Enable-LMS                           ║
 ║  DB host    : ${TARGET_IP} (/d01/postgresql)   ║
 ║  HTTP       : http://${TARGET_IP}:8080           ║
 ║  Tunnel     : https://lms.automatebot.shop                  ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Day-to-day commands:                                       ║
 ║    cd /u01/app/Enable-LMS/docker                            ║
 ║    docker compose ps                                        ║
 ║    docker compose logs -f api                               ║
 ║    docker compose restart api                               ║
 ║    docker compose down / up -d                              ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Log : /var/log/lms-target-setup-${STAMP}.log  ║
 ╚══════════════════════════════════════════════════════════════╝
DONE
echo -e "${NC}"
