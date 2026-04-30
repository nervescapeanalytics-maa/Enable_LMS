#!/usr/bin/env bash
# =============================================================================
# 02-restore-db.sh
#
# Dumps the SOURCE database and restores it on the target VM.
# Run this from your workstation (needs SSH to both source and target).
#
# Usage:
#   source deploy/.env
#   bash 02-restore-db.sh
# =============================================================================
set -euo pipefail

# Load env from repo .env if present
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

: "${SOURCE_HOST:?Set SOURCE_HOST (e.g. root@192.168.1.113)}"
: "${SOURCE_DB_HOST:?}"; : "${SOURCE_DB_USER:?}"
: "${SOURCE_DB_PASSWORD:?}"; : "${SOURCE_DB_NAME:?}"
: "${DB_VM_PUBLIC_IP:?}"; : "${DB_USER:?}"
: "${DB_PASSWORD:?}"; : "${DB_NAME:?}"

STAMP=$(date +%Y%m%d-%H%M%S)
DUMP="/tmp/lms-${STAMP}.dump"

echo "==> Dumping source database..."
ssh "$SOURCE_HOST" \
    "PGPASSWORD='$SOURCE_DB_PASSWORD' pg_dump \
        -h $SOURCE_DB_HOST -U $SOURCE_DB_USER -d $SOURCE_DB_NAME \
        --format=custom --compress=9 \
        -f $DUMP"

echo "==> Transferring dump to target VM..."
ssh "$SOURCE_HOST" "cat $DUMP" | ssh "root@$DB_VM_PUBLIC_IP" "cat > $DUMP"

echo "==> Restoring dump on target VM..."
ssh "root@$DB_VM_PUBLIC_IP" "
    PGPASSWORD='$DB_PASSWORD' pg_restore \
        -h localhost -U $DB_USER -d $DB_NAME \
        --no-owner --no-acl --clean --if-exists --jobs=4 \
        $DUMP
"

echo "==> Verifying row counts..."
ssh "root@$DB_VM_PUBLIC_IP" "
    PGPASSWORD='$DB_PASSWORD' psql -h localhost -U $DB_USER -d $DB_NAME \
        -c \"SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables
             ORDER BY n_live_tup DESC LIMIT 20;\"
"

echo "==> Taking fresh pgBackRest baseline..."
ssh "root@$DB_VM_PUBLIC_IP" "sudo -u postgres pgbackrest --stanza=lms --type=full backup"

echo ""
echo "=============================================================="
echo " Database restored successfully."
echo " Dump file kept at: $DB_VM_PUBLIC_IP:$DUMP"
echo "=============================================================="
