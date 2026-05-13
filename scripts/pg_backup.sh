#!/bin/bash
# =============================================================================
# Enable-LMS Enterprise — PostgreSQL Backup Script
#
# Supports both LOGICAL and PHYSICAL backups with retention management.
#
# Usage:
#   ./pg_backup.sh logical              Logical backup (pg_dump)
#   ./pg_backup.sh physical             Physical backup (pg_basebackup)
#   ./pg_backup.sh logical-schema       Schema-only dump (no data)
#   ./pg_backup.sh logical-data         Data-only dump (no schema)
#   ./pg_backup.sh restore <file>       Restore from a logical backup
#   ./pg_backup.sh list                 List available backups
#   ./pg_backup.sh cleanup              Remove backups older than retention
#
# Cron examples:
#   # Daily logical backup at 2 AM
#   0 2 * * * /u01/app/Enable-LMS/scripts/pg_backup.sh logical >> /var/log/lms-backup.log 2>&1
#
#   # Weekly physical backup at 3 AM Sunday
#   0 3 * * 0 /u01/app/Enable-LMS/scripts/pg_backup.sh physical >> /var/log/lms-backup.log 2>&1
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/docker/.env"

# ── Load environment ─────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

# ── Configuration (override via environment or .env) ─────────────────────────
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-LMS_PROD_DB}"
DB_USER="${DB_USER:-lms_app_user}"
DB_PASSWORD="${DB_PASSWORD:-}"

BACKUP_DIR="${BACKUP_DIR:-/u01/backups/postgres}"
LOGICAL_DIR="$BACKUP_DIR/logical"
PHYSICAL_DIR="$BACKUP_DIR/physical"
LOG_FILE="${BACKUP_LOG:-/var/log/lms-pg-backup.log}"

# Retention in days
LOGICAL_RETENTION="${LOGICAL_RETENTION:-30}"
PHYSICAL_RETENTION="${PHYSICAL_RETENTION:-7}"

# Compression
PARALLEL_JOBS="${PARALLEL_JOBS:-4}"

# Timestamp
TS=$(date +%Y%m%d_%H%M%S)

# ── Color helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"; }
err()   { echo -e "${RED}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE" >&2; }
warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"; }

# ── Prerequisites check ─────────────────────────────────────────────────────
check_prereqs() {
    for cmd in pg_dump pg_basebackup psql; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            err "Required command '$cmd' not found. Install postgresql client tools."
            exit 1
        fi
    done
}

# ── Test database connectivity ───────────────────────────────────────────────
test_connection() {
    info "Testing connection to ${DB_HOST}:${DB_PORT}/${DB_NAME}..."
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1;" >/dev/null 2>&1; then
        ok "Database connection successful"
    else
        err "Cannot connect to database"
        exit 1
    fi
}

# ── Create directories ───────────────────────────────────────────────────────
init_dirs() {
    mkdir -p "$LOGICAL_DIR" "$PHYSICAL_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
}

# =============================================================================
# LOGICAL BACKUP (pg_dump)
# =============================================================================
cmd_logical() {
    local format="${1:-custom}"  # custom, plain, directory
    local suffix label extra_args=""

    case "$format" in
        schema)
            suffix="schema.sql"
            label="Schema-only"
            extra_args="--schema-only --format=plain"
            ;;
        data)
            suffix="data.dump"
            label="Data-only"
            extra_args="--data-only --format=custom"
            ;;
        *)
            suffix="full.dump"
            label="Full"
            extra_args="--format=custom --compress=zstd:6"
            ;;
    esac

    local backup_file="$LOGICAL_DIR/${DB_NAME}_${TS}_${suffix}"

    info "=========================================="
    info "LOGICAL BACKUP — ${label}"
    info "=========================================="
    info "  Database : ${DB_NAME}"
    info "  Host     : ${DB_HOST}:${DB_PORT}"
    info "  Output   : ${backup_file}"
    info "  Started  : $(date)"

    local start_time=$SECONDS

    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --schema=public \
        --enable-row-security \
        --verbose \
        --no-owner \
        --no-privileges \
        $extra_args \
        -f "$backup_file" 2>> "$LOG_FILE"

    local duration=$((SECONDS - start_time))
    local size
    size=$(du -sh "$backup_file" | awk '{print $1}')

    ok "Backup completed in ${duration}s"
    ok "  File: ${backup_file}"
    ok "  Size: ${size}"

    # Verify backup integrity
    if [[ "$format" != "schema" && "$format" != "plain" ]]; then
        info "Verifying backup integrity..."
        if pg_restore --list "$backup_file" >/dev/null 2>&1; then
            ok "Backup verification: PASSED"
        else
            err "Backup verification: FAILED — file may be corrupt"
            exit 1
        fi
    fi

    # Generate SHA256 checksum
    sha256sum "$backup_file" > "${backup_file}.sha256"
    ok "Checksum: ${backup_file}.sha256"
    echo ""
}

# =============================================================================
# PHYSICAL BACKUP (pg_basebackup)
# =============================================================================
cmd_physical() {
    local backup_subdir="$PHYSICAL_DIR/${DB_NAME}_${TS}"

    info "=========================================="
    info "PHYSICAL BACKUP (pg_basebackup)"
    info "=========================================="
    info "  Host     : ${DB_HOST}:${DB_PORT}"
    info "  Output   : ${backup_subdir}"
    info "  Format   : tar + gzip"
    info "  Started  : $(date)"
    warn "  Note     : Requires REPLICATION or SUPERUSER privileges"

    local start_time=$SECONDS

    mkdir -p "$backup_subdir"

    PGPASSWORD="$DB_PASSWORD" pg_basebackup \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -D "$backup_subdir" \
        --format=tar \
        --gzip \
        --checkpoint=fast \
        --wal-method=stream \
        --progress \
        --verbose 2>> "$LOG_FILE"

    local duration=$((SECONDS - start_time))
    local size
    size=$(du -sh "$backup_subdir" | awk '{print $1}')

    ok "Physical backup completed in ${duration}s"
    ok "  Directory: ${backup_subdir}"
    ok "  Size: ${size}"

    # SHA256 for all files
    find "$backup_subdir" -type f -exec sha256sum {} \; > "${backup_subdir}.sha256"
    ok "Checksum: ${backup_subdir}.sha256"
    echo ""
}

# =============================================================================
# RESTORE (from logical backup)
# =============================================================================
cmd_restore() {
    local backup_file="${1:-}"
    if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
        err "Usage: $0 restore <backup_file>"
        err "Available backups:"
        cmd_list
        exit 1
    fi

    warn "=========================================="
    warn "RESTORE from ${backup_file}"
    warn "=========================================="
    warn "  Target: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
    warn ""
    warn "  THIS WILL OVERWRITE DATA IN ${DB_NAME}!"
    read -rp "  Type 'yes' to continue: " confirm
    if [[ "$confirm" != "yes" ]]; then
        info "Restore cancelled"
        exit 0
    fi

    # Verify checksum if available
    if [[ -f "${backup_file}.sha256" ]]; then
        info "Verifying checksum..."
        if sha256sum -c "${backup_file}.sha256" >/dev/null 2>&1; then
            ok "Checksum verified"
        else
            err "Checksum mismatch! Backup may be corrupt."
            exit 1
        fi
    fi

    info "Restoring..."
    local start_time=$SECONDS

    if [[ "$backup_file" == *.sql ]]; then
        # Plain SQL restore
        PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -f "$backup_file" 2>> "$LOG_FILE"
    else
        # Custom format restore
        PGPASSWORD="$DB_PASSWORD" pg_restore \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-owner \
            --no-privileges \
            --clean \
            --if-exists \
            --verbose \
            "$backup_file" 2>> "$LOG_FILE"
    fi

    local duration=$((SECONDS - start_time))
    ok "Restore completed in ${duration}s"
    echo ""
}

# =============================================================================
# LIST BACKUPS
# =============================================================================
cmd_list() {
    echo ""
    info "Available backups in ${BACKUP_DIR}"
    echo ""

    if [[ -d "$LOGICAL_DIR" ]]; then
        echo "── Logical Backups ──────────────────────────────────────────────"
        local count=0
        while IFS= read -r f; do
            [[ -z "$f" ]] && continue
            local size
            size=$(du -sh "$f" | awk '{print $1}')
            local mtime
            mtime=$(stat -c '%y' "$f" 2>/dev/null | cut -d. -f1)
            printf "  %-60s %8s  %s\n" "$(basename "$f")" "$size" "$mtime"
            count=$((count + 1))
        done < <(find "$LOGICAL_DIR" -maxdepth 1 -type f \( -name "*.dump" -o -name "*.sql" \) | sort)
        if [[ $count -eq 0 ]]; then
            echo "  (none)"
        fi
        echo ""
    fi

    if [[ -d "$PHYSICAL_DIR" ]]; then
        echo "── Physical Backups ─────────────────────────────────────────────"
        local count=0
        while IFS= read -r d; do
            [[ -z "$d" ]] && continue
            local size
            size=$(du -sh "$d" | awk '{print $1}')
            local mtime
            mtime=$(stat -c '%y' "$d" 2>/dev/null | cut -d. -f1)
            printf "  %-60s %8s  %s\n" "$(basename "$d")" "$size" "$mtime"
            count=$((count + 1))
        done < <(find "$PHYSICAL_DIR" -maxdepth 1 -type d ! -path "$PHYSICAL_DIR" | sort)
        if [[ $count -eq 0 ]]; then
            echo "  (none)"
        fi
        echo ""
    fi
}

# =============================================================================
# CLEANUP — Remove old backups based on retention
# =============================================================================
cmd_cleanup() {
    info "Cleaning up backups older than retention..."
    echo ""

    # Logical backups
    local logical_removed=0
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        info "Removing: $(basename "$f")"
        rm -f "$f" "${f}.sha256"
        logical_removed=$((logical_removed + 1))
    done < <(find "$LOGICAL_DIR" -maxdepth 1 -type f -name "*.dump" -mtime +"$LOGICAL_RETENTION" 2>/dev/null)
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        rm -f "$f" "${f}.sha256"
        logical_removed=$((logical_removed + 1))
    done < <(find "$LOGICAL_DIR" -maxdepth 1 -type f -name "*.sql" -mtime +"$LOGICAL_RETENTION" 2>/dev/null)

    # Physical backups
    local physical_removed=0
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        info "Removing: $(basename "$d")"
        rm -rf "$d" "${d}.sha256"
        physical_removed=$((physical_removed + 1))
    done < <(find "$PHYSICAL_DIR" -maxdepth 1 -type d ! -path "$PHYSICAL_DIR" -mtime +"$PHYSICAL_RETENTION" 2>/dev/null)

    ok "Removed: ${logical_removed} logical, ${physical_removed} physical backups"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================
check_prereqs
init_dirs

case "${1:-}" in
    logical)
        test_connection
        cmd_logical custom
        ;;
    logical-schema)
        test_connection
        cmd_logical schema
        ;;
    logical-data)
        test_connection
        cmd_logical data
        ;;
    physical)
        test_connection
        cmd_physical
        ;;
    restore)
        test_connection
        cmd_restore "${2:-}"
        ;;
    list)
        cmd_list
        ;;
    cleanup)
        cmd_cleanup
        ;;
    *)
        echo "Enable-LMS — PostgreSQL Backup Management"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  logical           Full logical backup (pg_dump, custom format + zstd)"
        echo "  logical-schema    Schema-only backup (DDL statements)"
        echo "  logical-data      Data-only backup (no schema)"
        echo "  physical          Physical backup (pg_basebackup, tar + gzip)"
        echo "  restore <file>    Restore from a logical backup file"
        echo "  list              List all available backups"
        echo "  cleanup           Remove backups exceeding retention period"
        echo ""
        echo "Configuration (via .env or environment):"
        echo "  BACKUP_DIR             = ${BACKUP_DIR}"
        echo "  LOGICAL_RETENTION      = ${LOGICAL_RETENTION} days"
        echo "  PHYSICAL_RETENTION     = ${PHYSICAL_RETENTION} days"
        echo "  DB_HOST                = ${DB_HOST}"
        echo "  DB_NAME                = ${DB_NAME}"
        echo ""
        exit 1
        ;;
esac
