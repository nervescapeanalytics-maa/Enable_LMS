#!/usr/bin/env bash
# =============================================================================
# 01-setup-postgres-vm.sh
#
# Run ONCE on the freshly provisioned PostgreSQL VM (45.194.90.251).
# Assumes Rocky Linux 9 / RHEL 9. Adapt for Ubuntu if needed.
#
# Usage (on the DB VM as root):
#   export DB_PASSWORD='<strong-password>'
#   export VPC_CIDR='10.50.0.0/16'
#   bash 01-setup-postgres-vm.sh
# =============================================================================
set -euo pipefail

: "${DB_PASSWORD:?Set DB_PASSWORD env var}"
: "${VPC_CIDR:=10.50.0.0/16}"

DB_NAME="LMS_PROD_DB"
DB_USER="lms_app_user"
PGDATA="/var/lib/pgsql/16/data"

echo "==> Installing PostgreSQL 16 + pgBackRest"
dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf module disable -y postgresql
dnf install -y postgresql16-server postgresql16-contrib pgbackrest

echo "==> Initializing database cluster"
/usr/pgsql-16/bin/postgresql-16-setup initdb
systemctl enable --now postgresql-16

echo "==> Generating self-signed TLS cert"
cd "$PGDATA"
if [[ ! -f server.crt ]]; then
    openssl req -new -x509 -days 3650 -nodes -text \
        -out server.crt -keyout server.key \
        -subj "/CN=lms-db.internal"
    chmod 600 server.key
    chown postgres:postgres server.crt server.key
fi

echo "==> Writing postgresql.conf tuning"
cat > "$PGDATA/postgresql.conf.lms" <<EOF
listen_addresses = '*'
port = 5432
max_connections = 200

shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 16MB
maintenance_work_mem = 256MB

wal_level = replica
max_wal_size = 2GB
min_wal_size = 512MB
checkpoint_completion_target = 0.9
archive_mode = on
archive_command = 'pgbackrest --stanza=lms archive-push %p'

ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file  = 'server.key'

logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%a.log'
log_rotation_age = 1d
log_min_duration_statement = 500ms
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p] %u@%d '
EOF
# Append only if not already done
if ! grep -q "archive_command = 'pgbackrest" "$PGDATA/postgresql.conf"; then
    cat "$PGDATA/postgresql.conf.lms" >> "$PGDATA/postgresql.conf"
fi

echo "==> Writing pg_hba.conf (hostssl only, VPC CIDR: $VPC_CIDR)"
cat > "$PGDATA/pg_hba.conf" <<EOF
local   all            postgres                        peer
hostssl $DB_NAME       $DB_USER       $VPC_CIDR       scram-sha-256
hostssl all            postgres       $VPC_CIDR       scram-sha-256
host    all            all            0.0.0.0/0       reject
EOF
chown postgres:postgres "$PGDATA/pg_hba.conf"

systemctl restart postgresql-16

echo "==> Creating database and application user"
sudo -u postgres psql <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') THEN
        CREATE DATABASE "$DB_NAME" ENCODING 'UTF8' TEMPLATE template0;
    END IF;
END
\$\$;

DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD' CONNECTION LIMIT 150;
    ELSE
        ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO $DB_USER;
ALTER DATABASE "$DB_NAME" OWNER TO $DB_USER;
EOF

sudo -u postgres psql -d "$DB_NAME" <<EOF
GRANT ALL ON SCHEMA public TO $DB_USER;
EOF

echo "==> Configuring firewalld"
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --zone=public \
        --add-rich-rule="rule family=\"ipv4\" source address=\"$VPC_CIDR\" port port=\"5432\" protocol=\"tcp\" accept" || true
    firewall-cmd --reload
fi

echo "==> Initializing pgBackRest"
mkdir -p /var/lib/pgbackrest /var/log/pgbackrest
chown -R postgres:postgres /var/lib/pgbackrest /var/log/pgbackrest

if [[ ! -f /etc/pgbackrest/pgbackrest.conf ]]; then
cat > /etc/pgbackrest/pgbackrest.conf <<EOF
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=7
repo1-retention-diff=14
process-max=2
log-level-console=info
start-fast=y
compress-type=zst

[lms]
pg1-path=$PGDATA
pg1-port=5432
EOF
fi

sudo -u postgres pgbackrest --stanza=lms stanza-create || true
sudo -u postgres pgbackrest --stanza=lms --type=full backup

echo "==> Installing backup cron"
(sudo -u postgres crontab -l 2>/dev/null | grep -v pgbackrest; cat <<EOF
0 2 * * 0   pgbackrest --stanza=lms --type=full backup
0 2 * * 1-6 pgbackrest --stanza=lms --type=incr backup
EOF
) | sudo -u postgres crontab -

echo ""
echo "=============================================================="
echo " PostgreSQL VM ready."
echo "   DB:   $DB_NAME"
echo "   User: $DB_USER"
echo "   TLS:  required (hostssl)"
echo "   Test: PGPASSWORD=... psql 'host=45.194.90.251 sslmode=require"
echo "         user=$DB_USER dbname=$DB_NAME' -c 'SELECT 1;'"
echo "=============================================================="
