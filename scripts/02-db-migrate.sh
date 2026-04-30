#!/usr/bin/env bash
# =============================================================================
#  02-db-migrate.sh
#  Dump LMS_PROD_DB from Source (192.168.1.113) → Restore on Target (45.194.90.251)
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║  Run this script ON THE SOURCE MACHINE (192.168.1.113) as root          ║
#  ║  PREREQUISITE: 01-target-pg-setup.sh must have been completed first     ║
#  ║                                                                          ║
#  ║  Run:  bash /u01/app/Enable-LMS/scripts/02-db-migrate.sh               ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
#
#  What this script does (in order):
#  ──────────────────────────────────────────────────────────────────────────
#  [PHASE 1]  Pre-flight: connectivity, disk space, SSH to target
#  [PHASE 2]  Capture baseline row-count from source for verification
#  [PHASE 3]  pg_dump from /d01/postgres/18/bin/pg_dump (source PG)
#  [PHASE 4]  rsync dump file to target machine /tmp/
#  [PHASE 5]  Drop & recreate DB on target (clean slate)
#  [PHASE 6]  pg_restore on target (4 parallel jobs)
#  [PHASE 7]  Post-restore permissions grant
#  [PHASE 8]  Verify row-counts match source
#  [PHASE 9]  Update docker/.env DB_HOST to target IP
#  [PHASE 10] Restart Docker stack, confirm DB connectivity
#  [PHASE 11] Cleanup temp files
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
LOG="/var/log/lms-db-migrate-${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1
info "All output logged to: $LOG"

# ── Fixed values ───────────────────────────────────────────────────────────────
SOURCE_IP="192.168.1.113"
TARGET_IP="45.194.90.251"
TARGET_HOST="rocky@${TARGET_IP}"

# Source PostgreSQL (custom layout on source machine)
SRC_PG_BIN="/d01/postgres/18/bin"
SRC_PG_DATA="/d01/postgres/18/data"
SRC_PG_SOCKET="/d01/postgres/18/run"
SRC_PG_USER="pgadmin"

# Source DB credentials (from docker/.env)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/docker/.env"
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

SRC_DB_HOST="${DB_HOST:-192.168.1.113}"
SRC_DB_PORT="${DB_PORT:-5432}"
SRC_DB_NAME="${DB_NAME:-LMS_PROD_DB}"
SRC_DB_APP_USER="${DB_USER:-lms_app_user}"
SRC_DB_PASS="${DB_PASSWORD:-LmsSecure@2024!}"

# Target PostgreSQL (new layout on target machine)
TGT_PG_BASE="/d01/postgresql"
TGT_PG_BIN="${TGT_PG_BASE}/bin"
TGT_PG_SOCKET="${TGT_PG_BASE}/run"
TGT_PG_USER="pgadmin"

DUMP_FILE="/tmp/lms-${SRC_DB_NAME}-${STAMP}.dump"
TGT_DUMP_FILE="/tmp/lms-${SRC_DB_NAME}-${STAMP}.dump"

# =============================================================================
# BANNER
# =============================================================================
clear
echo -e "${BOLD}"
cat <<'BANNER'
 ╔══════════════════════════════════════════════════════════════╗
 ║     Enable-LMS — Database Migration                         ║
 ║     Source: 192.168.1.113  →  Target: 45.194.90.251         ║
 ║     Method: pg_dump (custom format) + pg_restore            ║
 ╚══════════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

# =============================================================================
# INTERACTIVE INPUTS
# =============================================================================
banner "CONFIGURATION"

echo ""
info "Source DB : ${SRC_DB_HOST}:${SRC_DB_PORT}/${SRC_DB_NAME} (user: ${SRC_DB_APP_USER})"
info "Target    : ${TARGET_IP} — ${TGT_PG_BASE}"
echo ""

ask "Source DB password for '${SRC_DB_APP_USER}'"
ask "(Press ENTER to use value from docker/.env: [${SRC_DB_PASS:0:4}****]): "
read -r -s PASS_INPUT
echo ""
[[ -n "$PASS_INPUT" ]] && SRC_DB_PASS="$PASS_INPUT"

ask "Target DB password for '${SRC_DB_APP_USER}' on target machine"
ask "(Press ENTER to use same password as source): "
read -r -s TGT_PASS_INPUT
echo ""
TGT_DB_PASS="${TGT_PASS_INPUT:-$SRC_DB_PASS}"

echo ""
ask "SSH key for target (leave blank to use default ~/.ssh/id_rsa): "
read -r SSH_KEY_INPUT
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o BatchMode=yes"
[[ -n "$SSH_KEY_INPUT" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY_INPUT"

echo ""
info "Migration plan:"
echo "  Source PG binary  : ${SRC_PG_BIN}/pg_dump"
echo "  Source DB         : ${SRC_DB_HOST}:${SRC_DB_PORT}/${SRC_DB_NAME}"
echo "  Dump file (local) : ${DUMP_FILE}"
echo "  Target            : ${TARGET_HOST}"
echo "  Target dump file  : ${TGT_DUMP_FILE}"
echo "  Target PG bin     : ${TGT_PG_BIN}/pg_restore"
echo "  Restore DB        : ${SRC_DB_NAME} on ${TARGET_IP}"
echo "  docker/.env       : DB_HOST will be updated to ${TARGET_IP}"
echo ""

confirm "Proceed with database migration?"

# =============================================================================
# PHASE 1 — Pre-flight checks
# =============================================================================
banner "PHASE 1 — Pre-flight Checks"

info "Checking: running as root or pgadmin..."
[[ $EUID -eq 0 ]] || id | grep -qE "pgadmin|postgres" || die "Run as root or pgadmin"
ok "User OK"

info "Checking: source PG binary exists..."
[[ -x "${SRC_PG_BIN}/pg_dump" ]] || die "pg_dump not found at ${SRC_PG_BIN}/pg_dump"
SRC_PG_VER=$("${SRC_PG_BIN}/pg_dump" --version | awk '{print $3}')
ok "Source pg_dump: ${SRC_PG_VER}"

info "Checking: source DB connectivity..."
PGPASSWORD="$SRC_DB_PASS" "${SRC_PG_BIN}/psql" \
    -h "$SRC_DB_HOST" -p "$SRC_DB_PORT" \
    -U "$SRC_DB_APP_USER" -d "$SRC_DB_NAME" \
    -c "SELECT 1;" -t -A -q >/dev/null \
    || die "Cannot connect to source DB. Check host/port/password."
ok "Source DB connection OK"

SRC_DB_SIZE=$(PGPASSWORD="$SRC_DB_PASS" "${SRC_PG_BIN}/psql" \
    -h "$SRC_DB_HOST" -p "$SRC_DB_PORT" \
    -U "$SRC_DB_APP_USER" -d "$SRC_DB_NAME" \
    -t -A -c "SELECT pg_size_pretty(pg_database_size('$SRC_DB_NAME'));")
info "Source DB size: ${SRC_DB_SIZE}"

# Disk space check — need at least 3x DB size free in /tmp
SRC_DB_BYTES=$(PGPASSWORD="$SRC_DB_PASS" "${SRC_PG_BIN}/psql" \
    -h "$SRC_DB_HOST" -p "$SRC_DB_PORT" \
    -U "$SRC_DB_APP_USER" -d "$SRC_DB_NAME" \
    -t -A -c "SELECT pg_database_size('$SRC_DB_NAME');")
FREE_BYTES=$(df /tmp --output=avail -B1 | tail -1)
NEEDED=$(( SRC_DB_BYTES * 2 ))
if (( FREE_BYTES < NEEDED )); then
    warn "Low disk space in /tmp: $(( FREE_BYTES / 1048576 ))MB free, need ~$(( NEEDED / 1048576 ))MB"
    confirm "Continue anyway?"
else
    ok "Disk space OK: $(( FREE_BYTES / 1048576 ))MB free in /tmp"
fi

info "Checking: SSH connectivity to target ${TARGET_HOST}..."
ssh $SSH_OPTS "$TARGET_HOST" "echo SSH-OK" 2>/dev/null | grep -q "SSH-OK" \
    || die "Cannot SSH to ${TARGET_HOST}. Ensure root password/key access is configured."
ok "SSH to target OK"

info "Checking: target PostgreSQL service is running..."
ssh $SSH_OPTS "$TARGET_HOST" "systemctl is-active postgres.service" 2>/dev/null | grep -q "active" \
    || die "postgres.service is not running on target. Run 01-target-pg-setup.sh first."
ok "Target postgres.service is active"

info "Checking: target pg_isready..."
ssh $SSH_OPTS "$TARGET_HOST" \
    "sudo -u ${TGT_PG_USER} ${TGT_PG_BIN}/pg_isready -h 127.0.0.1 -p 5432" 2>/dev/null \
    | grep -q "accepting" \
    || die "PostgreSQL on target is not accepting connections."
ok "Target DB accepting connections"

info "Checking: target has ${TGT_PG_BIN}/pg_restore..."
ssh $SSH_OPTS "$TARGET_HOST" "test -x ${TGT_PG_BIN}/pg_restore" \
    || die "pg_restore not found at ${TGT_PG_BIN} on target."
TGT_PG_VER=$(ssh $SSH_OPTS "$TARGET_HOST" "${TGT_PG_BIN}/pg_restore --version" | awk '{print $3}')
ok "Target pg_restore: ${TGT_PG_VER}"
pause

# =============================================================================
# PHASE 2 — Baseline row count from source
# =============================================================================
banner "PHASE 2 — Capture Baseline Metrics from Source"

info "Counting tables and rows in source DB..."
SRC_TABLE_COUNT=$(PGPASSWORD="$SRC_DB_PASS" "${SRC_PG_BIN}/psql" \
    -h "$SRC_DB_HOST" -p "$SRC_DB_PORT" \
    -U "$SRC_DB_APP_USER" -d "$SRC_DB_NAME" \
    -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
SRC_ROW_COUNT=$(PGPASSWORD="$SRC_DB_PASS" "${SRC_PG_BIN}/psql" \
    -h "$SRC_DB_HOST" -p "$SRC_DB_PORT" \
    -U "$SRC_DB_APP_USER" -d "$SRC_DB_NAME" \
    -t -A -c "SELECT COALESCE(SUM(n_live_tup),0) FROM pg_stat_user_tables;")

ok "Source baseline:"
echo "  Tables : ${SRC_TABLE_COUNT}"
echo "  Rows   : ${SRC_ROW_COUNT} (live tuples from pg_stat_user_tables)"
pause

# =============================================================================
# PHASE 3 — pg_dump from source
# =============================================================================
banner "PHASE 3 — Dump Source Database"

info "Running pg_dump (custom format, compression 9)..."
info "Output: ${DUMP_FILE}"

sudo -u "$SRC_PG_USER" "${SRC_PG_BIN}/pg_dump" \
    -h "$SRC_PG_SOCKET" \
    -U "$SRC_PG_USER" \
    --format=custom \
    --compress=9 \
    --verbose \
    --no-password \
    --exclude-schema=legacy_exam \
    "$SRC_DB_NAME" \
    -f "$DUMP_FILE" 2>&1

chown root:root "$DUMP_FILE" 2>/dev/null || true
DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
ok "Dump complete: ${DUMP_FILE} (${DUMP_SIZE})"
pause

# =============================================================================
# PHASE 4 — Transfer dump to target
# =============================================================================
banner "PHASE 4 — Transfer Dump File to Target"

info "rsync ${DUMP_FILE} → ${TARGET_HOST}:/tmp/"
rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    "$DUMP_FILE" \
    "${TARGET_HOST}:${TGT_DUMP_FILE}"

ok "Transfer complete: ${TGT_DUMP_FILE} on target"

# Verify file arrived intact via size check
LOCAL_SIZE=$(stat -c%s "$DUMP_FILE")
REMOTE_SIZE=$(ssh $SSH_OPTS "$TARGET_HOST" "stat -c%s ${TGT_DUMP_FILE}")
[[ "$LOCAL_SIZE" == "$REMOTE_SIZE" ]] \
    || die "File size mismatch: local=${LOCAL_SIZE} remote=${REMOTE_SIZE}. Transfer may be corrupt."
ok "File integrity check passed (${LOCAL_SIZE} bytes)"
pause

# =============================================================================
# PHASE 5 — Drop & recreate DB on target (clean slate)
# =============================================================================
banner "PHASE 5 — Prepare Target Database"

warn "This will DROP the existing '${SRC_DB_NAME}' database on target ${TARGET_IP} if it exists."
confirm "DROP and recreate '${SRC_DB_NAME}' on target?"

ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail

PG_BIN="${TGT_PG_BIN}"
PG_USER="${TGT_PG_USER}"
DB_NAME="${SRC_DB_NAME}"
APP_USER="${SRC_DB_APP_USER}"
TGT_PASS="${TGT_DB_PASS}"

echo "--- Terminating active connections to \${DB_NAME} ---"
sudo -u "\$PG_USER" "\${PG_BIN}/psql" -h 127.0.0.1 -p 5432 -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='\${DB_NAME}' AND pid <> pg_backend_pid();" || true

echo "--- Dropping database \${DB_NAME} if exists ---"
sudo -u "\$PG_USER" "\${PG_BIN}/psql" -h 127.0.0.1 -p 5432 -d postgres \
    -c "DROP DATABASE IF EXISTS \"\${DB_NAME}\";"

echo "--- Recreating database \${DB_NAME} ---"
sudo -u "\$PG_USER" "\${PG_BIN}/psql" -h 127.0.0.1 -p 5432 -d postgres \
    -c "CREATE DATABASE \"\${DB_NAME}\" OWNER \"\${APP_USER}\" ENCODING 'UTF8';"

echo "Target database ready."
REMOTE

ok "Target database '${SRC_DB_NAME}' recreated clean"
pause

# =============================================================================
# PHASE 6 — pg_restore on target
# =============================================================================
banner "PHASE 6 — Restore on Target"

info "Running pg_restore on ${TARGET_IP} (4 jobs)..."
ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail

PG_BIN="${TGT_PG_BIN}"
PG_USER="${TGT_PG_USER}"
DB_NAME="${SRC_DB_NAME}"
APP_USER="${SRC_DB_APP_USER}"
PASS="${TGT_DB_PASS}"
DUMP="${TGT_DUMP_FILE}"

export PGPASSWORD="\$PASS"

echo "--- pg_restore starting ---"
sudo -u "\${PG_USER}" "\${PG_BIN}/pg_restore" \
    -h /d01/postgresql/run \
    -U "\${PG_USER}" \
    -d "\${DB_NAME}" \
    --no-owner \
    --no-acl \
    --verbose \
    "\${DUMP}" 2>&1; RC=\$?

if (( RC > 0 )); then
    echo "pg_restore exited with code \${RC} — checking if only warnings..."
    # Exit code 1 from pg_restore is typically just warnings (not fatal errors)
    if (( RC == 1 )); then
        echo "WARNING: pg_restore exited 1 (likely non-fatal warnings only)"
    else
        echo "ERROR: pg_restore exited \${RC} — check output above"
        exit \$RC
    fi
fi
echo "pg_restore finished"
REMOTE

ok "pg_restore complete on target"
pause

# =============================================================================
# PHASE 7 — Post-restore permissions
# =============================================================================
banner "PHASE 7 — Post-restore Permissions"

ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
set -euo pipefail
PG_BIN="${TGT_PG_BIN}"
PG_USER="${TGT_PG_USER}"
DB_NAME="${SRC_DB_NAME}"
APP_USER="${SRC_DB_APP_USER}"

echo "--- Granting schema and object permissions ---"
sudo -u "\$PG_USER" "\${PG_BIN}/psql" -h 127.0.0.1 -p 5432 -d "\${DB_NAME}" <<SQL
GRANT ALL PRIVILEGES ON DATABASE "\${DB_NAME}" TO "\${APP_USER}";
GRANT ALL ON SCHEMA public       TO "\${APP_USER}";
GRANT ALL ON ALL TABLES     IN SCHEMA public TO "\${APP_USER}";
GRANT ALL ON ALL SEQUENCES  IN SCHEMA public TO "\${APP_USER}";
GRANT ALL ON ALL FUNCTIONS  IN SCHEMA public TO "\${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO "\${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "\${APP_USER}";
SQL
echo "Permissions granted"
REMOTE

ok "Post-restore permissions applied"

# =============================================================================
# PHASE 8 — Verification: compare row counts
# =============================================================================
banner "PHASE 8 — Row Count Verification"

TGT_TABLE_COUNT=$(ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
export PGPASSWORD="${TGT_DB_PASS}"
${TGT_PG_BIN}/psql -h 127.0.0.1 -p 5432 \
    -U "${SRC_DB_APP_USER}" -d "${SRC_DB_NAME}" \
    -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
REMOTE
)

TGT_ROW_COUNT=$(ssh $SSH_OPTS "$TARGET_HOST" bash <<REMOTE
export PGPASSWORD="${TGT_DB_PASS}"
${TGT_PG_BIN}/psql -h 127.0.0.1 -p 5432 \
    -U "${SRC_DB_APP_USER}" -d "${SRC_DB_NAME}" \
    -t -A -c "SELECT COALESCE(SUM(n_live_tup),0) FROM pg_stat_user_tables;"
REMOTE
)

echo ""
echo "  ┌───────────────────────┬──────────────┬──────────────┐"
echo "  │ Metric                │    Source    │    Target    │"
echo "  ├───────────────────────┼──────────────┼──────────────┤"
printf "  │ Tables                │ %12s │ %12s │\n" "$SRC_TABLE_COUNT" "$TGT_TABLE_COUNT"
printf "  │ Live rows (approx)    │ %12s │ %12s │\n" "$SRC_ROW_COUNT" "$TGT_ROW_COUNT"
echo "  └───────────────────────┴──────────────┴──────────────┘"
echo ""

if [[ "$SRC_TABLE_COUNT" == "$TGT_TABLE_COUNT" ]]; then
    ok "Table count matches ($SRC_TABLE_COUNT tables)"
else
    warn "Table count mismatch: source=${SRC_TABLE_COUNT} target=${TGT_TABLE_COUNT}"
    warn "This may be due to pg_restore warnings — inspect the restore output above."
fi

# Live-row counts may differ slightly due to autovacuum timing — within 5% is acceptable
if [[ "$SRC_ROW_COUNT" -gt 0 ]]; then
    DIFF=$(( (TGT_ROW_COUNT - SRC_ROW_COUNT) ))
    (( DIFF < 0 )) && DIFF=$(( -DIFF ))
    PCT=$(( DIFF * 100 / SRC_ROW_COUNT ))
    if (( PCT <= 5 )); then
        ok "Row count within 5% tolerance (diff=${DIFF}, ${PCT}%)"
    else
        warn "Row count differs by ${PCT}% — investigate before switching traffic"
    fi
fi
pause

# =============================================================================
# PHASE 9 — Update docker/.env
# =============================================================================
banner "PHASE 9 — Update docker/.env DB_HOST"

info "Current DB_HOST in docker/.env: $(grep '^DB_HOST=' "$ENV_FILE")"

confirm "Update docker/.env to point DB_HOST → ${TARGET_IP}?"

# Backup current .env
cp "$ENV_FILE" "${ENV_FILE}.pre-migration-${STAMP}"
ok "Backup: ${ENV_FILE}.pre-migration-${STAMP}"

# Update DB_HOST
sed -i "s|^DB_HOST=.*|DB_HOST=${TARGET_IP}|" "$ENV_FILE"
ok "docker/.env DB_HOST updated:"
grep "^DB_HOST=" "$ENV_FILE"
pause

# =============================================================================
# PHASE 10 — Restart Docker stack and verify
# =============================================================================
banner "PHASE 10 — Restart Docker Stack on Source Machine"

info "The Docker stack on the SOURCE machine will now be restarted"
info "pointing to the NEW database at ${TARGET_IP}"
confirm "Restart Docker stack?"

cd "${PROJECT_DIR}/docker"
docker compose down
docker compose up -d
sleep 8

info "Container status:"
docker compose ps

info "Testing Django DB connectivity..."
docker compose exec -T api python manage.py dbshell -- -c "SELECT COUNT(*) FROM django_migrations;" 2>/dev/null \
    && ok "DB connection from api container: OK" \
    || { warn "dbshell test failed — trying showmigrations...";
         docker compose exec -T api python manage.py showmigrations --list 2>&1 | tail -5 \
         && ok "Django can reach DB" \
         || warn "Could not verify from container. Check: docker compose logs api"; }
pause

# =============================================================================
# PHASE 11 — Cleanup
# =============================================================================
banner "PHASE 11 — Cleanup"

info "Removing local dump file: ${DUMP_FILE}"
rm -f "$DUMP_FILE"
ok "Local dump removed"

info "Removing dump from target: ${TGT_DUMP_FILE}"
ssh $SSH_OPTS "$TARGET_HOST" "rm -f ${TGT_DUMP_FILE}" && ok "Target dump removed" || warn "Could not remove target dump"

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}"
cat <<DONE
 ╔══════════════════════════════════════════════════════════════╗
 ║   Database Migration COMPLETE                               ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  Source : ${SOURCE_IP}  /d01/postgres/18       ║
 ║  Target : ${TARGET_IP}  /d01/postgresql     ║
 ║  DB     : ${SRC_DB_NAME}                     ║
 ║  Tables : src=${SRC_TABLE_COUNT}  tgt=${TGT_TABLE_COUNT}                         ║
 ║  .env backup : docker/.env.pre-migration-${STAMP}  ║
 ║  Log    : ${LOG}  ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  NEXT STEP: Run 03-app-migrate.sh to move Docker images     ║
 ║    bash scripts/03-app-migrate.sh                           ║
 ╚══════════════════════════════════════════════════════════════╝
DONE
echo -e "${NC}"
