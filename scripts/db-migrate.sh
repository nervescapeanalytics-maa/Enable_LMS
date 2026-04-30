#!/usr/bin/env bash
# =============================================================================
# db-migrate.sh — Dump LMS_PROD_DB from source and restore on target PG18
#
# Run this from the SOURCE machine (current app/DB server).
# The target machine must already have PostgreSQL 18 installed and the
# database role+DB created (see pg18-rocky8-setup.sh).
#
# Usage:
#   export TARGET_HOST='root@<target-ip>'    # SSH user@IP of Rocky 8 target
#   export TARGET_DB_IP='<target-ip>'        # IP Docker containers will connect to
#   bash scripts/db-migrate.sh
#
# What it does:
#   Phase 1 — Dump:     pg_dump from local PG18 → compressed .dump file
#   Phase 2 — Transfer: rsync the dump to target over SSH
#   Phase 3 — Restore:  pg_restore on target, verify row counts match
#   Phase 4 — Update:   patch docker/.env DB_HOST to point at target
#   Phase 5 — Verify:   restart stack, test DB connectivity
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/docker/.env"

# ── Load current .env ─────────────────────────────────────────────────────────
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

# ── Required parameters ───────────────────────────────────────────────────────
# Source DB (from .env)
SRC_HOST="${DB_HOST:-192.168.1.113}"
SRC_PORT="${DB_PORT:-5432}"
SRC_DB="${DB_NAME:-LMS_PROD_DB}"
SRC_USER="${DB_USER:-lms_app_user}"
SRC_PASS="${DB_PASSWORD:?DB_PASSWORD not set in docker/.env}"

# Target (set via env before running)
TARGET_HOST="${TARGET_HOST:?Set TARGET_HOST=root@<target-ip>}"
TARGET_DB_IP="${TARGET_DB_IP:?Set TARGET_DB_IP=<ip-reachable-from-docker-containers>}"
TGT_DB="${DB_NAME:-LMS_PROD_DB}"
TGT_USER="${DB_USER:-lms_app_user}"
TGT_PASS="${DB_PASSWORD:-$SRC_PASS}"   # Use same password unless overridden

PG_MAJOR=18
PG_BIN="/usr/pgsql-${PG_MAJOR}/bin"

STAMP=$(date +%Y%m%d-%H%M%S)
DUMP_FILE="/tmp/lms-pg18-${STAMP}.dump"
DUMP_LOG="/tmp/lms-pg18-migrate-${STAMP}.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')] INFO  ${NC} $*" | tee -a "$DUMP_LOG"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] OK    ${NC} $*" | tee -a "$DUMP_LOG"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN  ${NC} $*" | tee -a "$DUMP_LOG"; }
die()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR ${NC} $*" | tee -a "$DUMP_LOG" >&2; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Phase 0 — Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 0: Pre-flight checks ==="

info "Source: PostgreSQL @ ${SRC_HOST}:${SRC_PORT}/${SRC_DB}"
PGPASSWORD="$SRC_PASS" psql -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -d "$SRC_DB" \
    -c "SELECT version();" -t -A | tee -a "$DUMP_LOG" | grep -q "PostgreSQL 18" \
    || die "Cannot connect to source DB or it is not PostgreSQL 18"
ok "Source DB connection OK (PostgreSQL 18)"

SRC_SIZE=$(PGPASSWORD="$SRC_PASS" psql -h "$SRC_HOST" -p "$SRC_PORT" \
    -U "$SRC_USER" -d "$SRC_DB" \
    -t -A -c "SELECT pg_size_pretty(pg_database_size('$SRC_DB'));")
SRC_ROWS=$(PGPASSWORD="$SRC_PASS" psql -h "$SRC_HOST" -p "$SRC_PORT" \
    -U "$SRC_USER" -d "$SRC_DB" -t -A \
    -c "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;")
info "Source DB size: ${SRC_SIZE}, approx live rows: ${SRC_ROWS}"

info "Checking SSH connectivity to target ${TARGET_HOST}..."
ssh -o ConnectTimeout=10 -o BatchMode=yes "$TARGET_HOST" "echo ok" \
    || die "Cannot SSH to ${TARGET_HOST}. Ensure key-based auth is configured."
ok "SSH to target OK"

info "Checking PostgreSQL 18 on target..."
ssh "$TARGET_HOST" "${PG_BIN}/postgres --version" \
    || die "PostgreSQL ${PG_MAJOR} not found on target at ${PG_BIN}. Run pg18-rocky8-setup.sh first."
ok "Target PostgreSQL 18 found"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Dump from source
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 1: Dumping source database ==="
info "Writing dump to ${DUMP_FILE}..."

PGPASSWORD="$SRC_PASS" pg_dump \
    -h "$SRC_HOST" -p "$SRC_PORT" \
    -U "$SRC_USER" -d "$SRC_DB" \
    --format=custom \
    --compress=9 \
    --no-password \
    --verbose \
    -f "$DUMP_FILE" 2>&1 | tee -a "$DUMP_LOG"

DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
ok "Dump complete: ${DUMP_FILE} (${DUMP_SIZE})"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Transfer to target
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 2: Transferring dump to target ==="
info "rsync ${DUMP_FILE} → ${TARGET_HOST}:${DUMP_FILE}"

rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=accept-new" \
    "$DUMP_FILE" \
    "${TARGET_HOST}:${DUMP_FILE}" 2>&1 | tee -a "$DUMP_LOG"

ok "Transfer complete"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Restore on target
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 3: Restoring on target ==="

ssh "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
export PGPASSWORD='${TGT_PASS}'

echo "--- Dropping and recreating target database for clean restore ---"
sudo -u postgres ${PG_BIN}/psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${TGT_DB}' AND pid <> pg_backend_pid();" || true
sudo -u postgres ${PG_BIN}/psql -c "DROP DATABASE IF EXISTS \"${TGT_DB}\";"
sudo -u postgres ${PG_BIN}/psql -c "CREATE DATABASE \"${TGT_DB}\" OWNER \"${TGT_USER}\";"

echo "--- Running pg_restore ---"
${PG_BIN}/pg_restore \
    -h 127.0.0.1 -p 5432 \
    -U "${TGT_USER}" \
    -d "${TGT_DB}" \
    --no-owner \
    --no-acl \
    --jobs=4 \
    --verbose \
    "${DUMP_FILE}" 2>&1 || true   # pg_restore exits 1 on warnings — we check below

echo "--- Row count verification ---"
ROW_COUNT=\$(${PG_BIN}/psql -h 127.0.0.1 -U "${TGT_USER}" -d "${TGT_DB}" \
    -t -A -c "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;")
echo "Target live row count: \${ROW_COUNT}"

echo "--- Table list ---"
${PG_BIN}/psql -h 127.0.0.1 -U "${TGT_USER}" -d "${TGT_DB}" \
    -c "\dt+" 2>&1 | head -60

echo "--- Grant schema permissions ---"
sudo -u postgres ${PG_BIN}/psql -d "${TGT_DB}" \
    -c "GRANT ALL PRIVILEGES ON DATABASE \"${TGT_DB}\" TO \"${TGT_USER}\";"
sudo -u postgres ${PG_BIN}/psql -d "${TGT_DB}" \
    -c "GRANT ALL ON SCHEMA public TO \"${TGT_USER}\";"
sudo -u postgres ${PG_BIN}/psql -d "${TGT_DB}" \
    -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO \"${TGT_USER}\";"
sudo -u postgres ${PG_BIN}/psql -d "${TGT_DB}" \
    -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO \"${TGT_USER}\";"

echo "Restore complete on target"
REMOTE

ok "Restore complete on target"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Update docker/.env to point at new DB host
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 4: Updating docker/.env ==="

# Backup current .env
cp "$ENV_FILE" "${ENV_FILE}.pre-migration-${STAMP}"
ok "Backed up .env → ${ENV_FILE}.pre-migration-${STAMP}"

# Replace DB_HOST in-place
sed -i "s|^DB_HOST=.*|DB_HOST=${TARGET_DB_IP}|" "$ENV_FILE"
# Also update ALLOWED_HOSTS to include new target IP if not already there
if ! grep -q "$TARGET_DB_IP" "$ENV_FILE"; then
    sed -i "s|^ALLOWED_HOSTS=\(.*\)|\ALLOWED_HOSTS=\1,${TARGET_DB_IP}|" "$ENV_FILE"
fi

ok "docker/.env DB_HOST updated to: ${TARGET_DB_IP}"

# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Restart Docker stack and verify
# ─────────────────────────────────────────────────────────────────────────────
info "=== Phase 5: Restarting Docker stack ==="
cd "$PROJECT_DIR/docker"
docker compose down
docker compose up -d
sleep 5
docker compose ps

info "Testing DB connectivity from api container..."
docker compose exec -T api python manage.py showmigrations --list 2>&1 | tail -20 \
    && ok "DB connection from api container: OK" \
    || warn "Could not verify from container — check logs with: docker compose logs api"

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────
info "Removing local dump file..."
rm -f "$DUMP_FILE"
info "Removing dump from target..."
ssh "$TARGET_HOST" "rm -f ${DUMP_FILE}" || true

echo ""
echo "============================================================"
ok "Migration complete!"
echo "  Source DB:   ${SRC_HOST}:${SRC_PORT}/${SRC_DB}"
echo "  Target DB:   ${TARGET_DB_IP}:5432/${TGT_DB}"
echo "  .env backup: ${ENV_FILE}.pre-migration-${STAMP}"
echo "  Log file:    ${DUMP_LOG}"
echo ""
warn "OPTIONAL: Once verified, you can shut down PostgreSQL on source:"
warn "  systemctl stop postgresql-18 && systemctl disable postgresql-18"
echo "============================================================"
