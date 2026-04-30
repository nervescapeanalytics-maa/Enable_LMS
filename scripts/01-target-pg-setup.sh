#!/usr/bin/env bash
# =============================================================================
#  01-target-pg-setup.sh
#  Install & Configure PostgreSQL 18 on Rocky Linux 8 (Target: 45.194.90.251)
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║  Run this script ON THE TARGET MACHINE (45.194.90.251) as root          ║
#  ║                                                                          ║
#  ║  Upload:  scp scripts/01-target-pg-setup.sh root@45.194.90.251:/tmp/    ║
#  ║  Run:     ssh root@45.194.90.251 'bash /tmp/01-target-pg-setup.sh'      ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
#
#  What this script does (in order):
#  ──────────────────────────────────────────────────────────────────────────
#  [PHASE 1]  Pre-flight checks (OS, internet, existing installs)
#  [PHASE 2]  Install PGDG EL8 repo + PostgreSQL 18 packages
#  [PHASE 3]  Create OS user  pgadmin  (mirrors source machine)
#  [PHASE 4]  Create directory layout under  /d01/postgresql/
#                /d01/postgresql/bin        ← symlinks into /usr/pgsql-18/bin
#                /d01/postgresql/data       ← PGDATA (cluster files)
#                /d01/postgresql/wal        ← WAL files (pg_wal symlink target)
#                /d01/postgresql/archive    ← WAL archive
#                /d01/postgresql/log        ← server logs
#                /d01/postgresql/run        ← Unix socket + PID
#                /d01/postgresql/lib        ← symlink → /usr/pgsql-18/lib
#                /d01/postgresql/share      ← symlink → /usr/pgsql-18/share
#  [PHASE 5]  Initialise cluster (initdb)
#  [PHASE 6]  Write postgresql.conf  (mirrors source tuning, adapted paths)
#  [PHASE 7]  Write pg_hba.conf      (app server + localhost access)
#  [PHASE 8]  Generate self-signed SSL cert  (matches source ssl=on setting)
#  [PHASE 9]  Install custom systemd service  postgres.service
#  [PHASE 10] Start service, create DB role + database
#  [PHASE 11] Open firewalld port 5432
#  [PHASE 12] Final verification
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"; }
info()    { echo -e "${CYAN}  [INFO]  ${NC}$*"; }
ok()      { echo -e "${GREEN}  [ OK ]  ${NC}$*"; }
warn()    { echo -e "${YELLOW}  [WARN]  ${NC}$*"; }
die()     { echo -e "${RED}  [FAIL]  ${NC}$*" >&2; exit 1; }
ask()     { echo -e "${YELLOW}  [?]  ${NC}$*"; }

confirm() {
    local msg="${1:-Continue?}"
    ask "$msg [y/N] "
    read -r ans
    [[ "$ans" =~ ^[Yy]$ ]] || { warn "Aborted by user."; exit 0; }
}

pause() {
    echo ""
    ask "Press ENTER to continue or Ctrl-C to abort..."
    read -r
}

LOG=/var/log/lms-pg18-setup.log
exec > >(tee -a "$LOG") 2>&1
info "All output is being logged to: $LOG"

# ── Fixed values (do not change) ──────────────────────────────────────────────
SOURCE_IP="192.168.1.113"
TARGET_IP="45.194.90.251"
PG_MAJOR=18
PG_BASE="/d01/postgresql"          # ← ALL postgres files live here on target
PG_BIN_LINK="$PG_BASE/bin"
PG_DATA="$PG_BASE/data"
PG_WAL="$PG_BASE/wal"
PG_ARCHIVE="$PG_BASE/archive"
PG_LOG="$PG_BASE/log"
PG_RUN="$PG_BASE/run"
PG_LIB_LINK="$PG_BASE/lib"
PG_SHARE_LINK="$PG_BASE/share"
PGDG_BIN="/usr/pgsql-${PG_MAJOR}/bin"
PGDG_LIB="/usr/pgsql-${PG_MAJOR}/lib"
PGDG_SHARE="/usr/pgsql-${PG_MAJOR}/share"
PG_SVC="postgres"                  # custom service name (matches source)
PG_USER="pgadmin"
PG_GROUP="pgadmin"
DB_NAME="LMS_PROD_DB"
APP_SUBNET="192.168.0.0/16"       # source app server network
DOCKER_SUBNET="172.16.0.0/12"     # Docker bridge networks

# =============================================================================
# BANNER
# =============================================================================
clear
echo -e "${BOLD}"
cat <<'BANNER'
 ╔══════════════════════════════════════════════════════════════╗
 ║     Enable-LMS — PostgreSQL 18 Target Setup                 ║
 ║     Target: 45.194.90.251  (Rocky Linux 8)                  ║
 ║     PG Base Dir: /d01/postgresql                            ║
 ╚══════════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

# =============================================================================
# INTERACTIVE INPUTS
# =============================================================================
banner "CONFIGURATION INPUT"

echo ""
info "Source machine : ${SOURCE_IP} (Rocky Linux 9 — PostgreSQL 18.2)"
info "Target machine : ${TARGET_IP} (Rocky Linux 8)"
info "PG base dir    : ${PG_BASE}"
info "DB Name        : ${DB_NAME}"
info "PG OS user     : ${PG_USER}"
echo ""

ask "Enter DB password for role '${DB_NAME}' user 'lms_app_user'"
ask "(Press ENTER to use default: LmsSecure@2024!): "
read -r -s DB_PASSWORD_INPUT
echo ""
DB_USER_PASSWORD="${DB_PASSWORD_INPUT:-LmsSecure@2024!}"

ask "Enter IP of the application/Docker server that will connect to this DB"
ask "(Press ENTER to use default: ${SOURCE_IP}): "
read -r APP_SERVER_IP_INPUT
APP_SERVER_IP="${APP_SERVER_IP_INPUT:-$SOURCE_IP}"
DB_APP_USER="lms_app_user"

echo ""
info "Summary of what will be installed:"
echo "  PostgreSQL version : 18 (PGDG EL8)"
echo "  PG base directory  : $PG_BASE"
echo "  PGDATA             : $PG_DATA"
echo "  WAL directory      : $PG_WAL"
echo "  Archive directory  : $PG_ARCHIVE"
echo "  Log directory      : $PG_LOG"
echo "  Socket/PID dir     : $PG_RUN"
echo "  OS User            : $PG_USER"
echo "  DB name            : $DB_NAME"
echo "  App user           : $DB_APP_USER"
echo "  App server IP      : $APP_SERVER_IP"
echo ""
confirm "Proceed with installation?"

# =============================================================================
# PHASE 1 — Pre-flight checks
# =============================================================================
banner "PHASE 1 — Pre-flight Checks"

info "Checking: running as root..."
[[ $EUID -eq 0 ]] || die "Must be run as root. Try: sudo bash $0"
ok "Running as root"

info "Checking: OS version..."
OS_NAME=$(grep -oP '(?<=^NAME=")[^"]+' /etc/os-release 2>/dev/null || echo "unknown")
OS_VER=$(grep -oP '(?<=^VERSION_ID=")[^"]+' /etc/os-release 2>/dev/null || echo "0")
MAJOR_VER="${OS_VER%%.*}"
info "Detected: $OS_NAME $OS_VER"
[[ "$MAJOR_VER" == "8" ]] || warn "Expected Rocky/RHEL 8 — found major version $MAJOR_VER. Proceeding anyway."
ok "OS check passed"

info "Checking: internet connectivity (downloading PGDG repo)..."
curl -sf --max-time 10 https://download.postgresql.org/pub/repos/yum/ -o /dev/null \
    || die "Cannot reach download.postgresql.org. Check DNS and internet access."
ok "Internet connectivity OK"

info "Checking: existing PostgreSQL installation..."
if rpm -q "postgresql${PG_MAJOR}-server" &>/dev/null; then
    warn "postgresql${PG_MAJOR}-server is already installed."
    confirm "Reinstall / reconfigure anyway?"
fi

info "Checking: existing data directory..."
if [[ -f "${PG_DATA}/PG_VERSION" ]]; then
    warn "A PostgreSQL cluster already exists at ${PG_DATA}"
    warn "Continuing will WIPE it on initdb step."
    confirm "Are you sure? The existing cluster will be destroyed."
    WIPE_EXISTING=true
else
    WIPE_EXISTING=false
fi

info "Checking: /d01 mountpoint..."
if ! mountpoint -q /d01 2>/dev/null && [[ ! -d /d01 ]]; then
    warn "/d01 does not exist. It will be created as a regular directory."
    warn "If /d01 should be a separate disk/LVM volume, abort now and mount it first."
    confirm "Create /d01 as a directory and continue?"
fi
ok "Pre-flight checks complete"
pause

# =============================================================================
# PHASE 2 — Install PostgreSQL 18 (PGDG EL8)
# =============================================================================
banner "PHASE 2 — Install PostgreSQL 18 (PGDG EL8)"

info "Installing PGDG EL8 repo RPM..."
dnf install -y \
    https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
    2>&1 | grep -E "install|already|error|ERROR" || true
ok "PGDG repo installed"

info "Disabling Rocky 8 AppStream postgresql module (prevents version conflicts)..."
dnf module disable -y postgresql 2>&1 | tail -3
ok "AppStream postgresql module disabled"

info "Installing postgresql18-server, postgresql18-contrib, postgresql18..."
dnf install -y \
    "postgresql${PG_MAJOR}" \
    "postgresql${PG_MAJOR}-server" \
    "postgresql${PG_MAJOR}-contrib" \
    2>&1 | grep -E "install|already|error|ERROR|Running" | tail -10
ok "PostgreSQL packages installed"

PG_VER_INSTALLED=$("${PGDG_BIN}/postgres" --version 2>/dev/null | awk '{print $3}')
ok "PostgreSQL version confirmed: $PG_VER_INSTALLED (at ${PGDG_BIN})"
pause

# =============================================================================
# PHASE 3 — Create OS user pgadmin
# =============================================================================
banner "PHASE 3 — Create OS user '${PG_USER}'"

if id "$PG_USER" &>/dev/null; then
    ok "User '$PG_USER' already exists (uid=$(id -u $PG_USER))"
else
    info "Creating group and user '$PG_USER'..."
    groupadd -r "$PG_GROUP"
    useradd -r -g "$PG_GROUP" -d "$PG_BASE" -s /bin/bash -c "PostgreSQL Admin" "$PG_USER"
    ok "User '$PG_USER' created (uid=$(id -u $PG_USER), gid=$(id -g $PG_USER))"
fi

# Set up .bash_profile for pgadmin with PG env vars
cat > "/home/${PG_USER}/.bash_profile" 2>/dev/null || cat > "${PG_BASE}/.bash_profile" <<PROFILE
# PostgreSQL environment for pgadmin
export PGHOME=${PG_BASE}
export PGDATA=${PG_DATA}
export PGPORT=5432
export PATH=${PG_BASE}/bin:/usr/pgsql-${PG_MAJOR}/bin:\$PATH
export LD_LIBRARY_PATH=${PGDG_LIB}:\$LD_LIBRARY_PATH
export PGLOG=${PG_LOG}
PROFILE
ok "pgadmin bash_profile written"
pause

# =============================================================================
# PHASE 4 — Directory Structure under /d01/postgresql
# =============================================================================
banner "PHASE 4 — Create Directory Structure under ${PG_BASE}"

mkdir -p /d01

info "Creating directory tree..."
for dir in "$PG_BASE" "$PG_DATA" "$PG_WAL" "$PG_ARCHIVE" "$PG_LOG" "$PG_RUN"; do
    mkdir -p "$dir"
    chown "${PG_USER}:${PG_GROUP}" "$dir"
    ok "Created: $dir"
done

# Permissions: data and wal must be 0700 (PostgreSQL requirement)
chmod 0700 "$PG_DATA" "$PG_WAL"
chmod 0755 "$PG_ARCHIVE" "$PG_LOG" "$PG_RUN" "$PG_BASE"
ok "Permissions set"

# Create bin directory populated with symlinks into PGDG bin
info "Creating ${PG_BIN_LINK}/ with symlinks to ${PGDG_BIN}/..."
mkdir -p "$PG_BIN_LINK"
for exe in "$PGDG_BIN"/*; do
    lnk="${PG_BIN_LINK}/$(basename "$exe")"
    [[ -e "$lnk" ]] || ln -s "$exe" "$lnk"
done
chown -R "${PG_USER}:${PG_GROUP}" "$PG_BIN_LINK"
ok "${PG_BIN_LINK}/ populated ($(ls "$PG_BIN_LINK" | wc -l) symlinks)"

# Symlink lib and share
ln -sfn "$PGDG_LIB"   "$PG_LIB_LINK"
ln -sfn "$PGDG_SHARE" "$PG_SHARE_LINK"
ok "${PG_LIB_LINK}   → ${PGDG_LIB}"
ok "${PG_SHARE_LINK} → ${PGDG_SHARE}"

info "Directory tree:"
ls -la "$PG_BASE"
pause

# =============================================================================
# PHASE 5 — Initialise Cluster (initdb)
# =============================================================================
banner "PHASE 5 — Initialise Cluster (initdb)"

if [[ "${WIPE_EXISTING:-false}" == "true" ]]; then
    info "Wiping existing data directory..."
    rm -rf "${PG_DATA:?}/"*
    ok "Existing cluster wiped"
fi

if [[ -f "${PG_DATA}/PG_VERSION" ]]; then
    warn "Cluster already initialised at ${PG_DATA} — skipping initdb"
else
    info "Running initdb with checksums enabled..."
    sudo -u "$PG_USER" "${PGDG_BIN}/initdb" \
        --pgdata="$PG_DATA" \
        --encoding=UTF8 \
        --locale=en_US.UTF-8 \
        --auth-local=peer \
        --auth-host=scram-sha-256 \
        --data-checksums \
        2>&1
    ok "Cluster initialised at ${PG_DATA}"

    # Redirect pg_wal to the dedicated WAL directory
    info "Redirecting pg_wal → ${PG_WAL}..."
    rm -rf "${PG_DATA}/pg_wal"
    ln -s "$PG_WAL" "${PG_DATA}/pg_wal"
    chown -h "${PG_USER}:${PG_GROUP}" "${PG_DATA}/pg_wal"
    ok "pg_wal symlink: ${PG_DATA}/pg_wal → ${PG_WAL}"
fi
pause

# =============================================================================
# PHASE 6 — PostgreSQL Configuration (mirrors source tuning)
# =============================================================================
banner "PHASE 6 — Write postgresql.conf"

# Auto-calculate memory settings from available RAM
TOTAL_RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
SHARED_BUFFERS_MB=$(( TOTAL_RAM_MB / 4 ))
EFFECTIVE_CACHE_MB=$(( TOTAL_RAM_MB * 3 / 4 ))
WORK_MEM_MB=$(( TOTAL_RAM_MB / 200 ))
MAINT_WORK_MEM_MB=$(( TOTAL_RAM_MB / 16 ))
(( SHARED_BUFFERS_MB  < 128 )) && SHARED_BUFFERS_MB=128
(( EFFECTIVE_CACHE_MB < 256 )) && EFFECTIVE_CACHE_MB=256
(( WORK_MEM_MB        < 4   )) && WORK_MEM_MB=4
(( MAINT_WORK_MEM_MB  < 64  )) && MAINT_WORK_MEM_MB=64

info "Memory auto-tune: RAM=${TOTAL_RAM_MB}MB  shared_buffers=${SHARED_BUFFERS_MB}MB  eff_cache=${EFFECTIVE_CACHE_MB}MB  work_mem=${WORK_MEM_MB}MB"

cat > "${PG_DATA}/postgresql.conf" <<EOF
# ============================================================
# Enable-LMS Enterprise — PostgreSQL 18 Configuration
# Generated by 01-target-pg-setup.sh on $(date)
# Target: ${TARGET_IP}  PG base: ${PG_BASE}
# Source mirror of: ${SOURCE_IP}:/d01/postgres/18/data/postgresql.conf
# ============================================================

# ── Connection ──────────────────────────────────────────────
listen_addresses = '*'
port = 5432
max_connections = 200
superuser_reserved_connections = 5
unix_socket_directories = '${PG_RUN}'
external_pid_file = '${PG_RUN}/postmaster.pid'

# ── SSL ─────────────────────────────────────────────────────
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file  = 'server.key'
ssl_min_protocol_version = 'TLSv1.2'

# ── Shared Libraries ────────────────────────────────────────
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max   = 10000
pg_stat_statements.track = all

# ── Memory (auto-calculated from ${TOTAL_RAM_MB} MB RAM) ──────────────────
shared_buffers            = ${SHARED_BUFFERS_MB}MB
effective_cache_size      = ${EFFECTIVE_CACHE_MB}MB
work_mem                  = ${WORK_MEM_MB}MB
maintenance_work_mem      = ${MAINT_WORK_MEM_MB}MB
huge_pages                = try
temp_buffers              = 32MB
max_prepared_transactions = 100

# ── WAL & Checkpoints ───────────────────────────────────────
wal_level                    = replica
wal_buffers                  = 64MB
max_wal_size                 = 4GB
min_wal_size                 = 1GB
checkpoint_completion_target = 0.9
checkpoint_timeout           = 15min

# ── Archiving ───────────────────────────────────────────────
archive_mode    = on
archive_command = 'cp %p ${PG_ARCHIVE}/%f'
archive_timeout = 300

# ── Replication ─────────────────────────────────────────────
max_wal_senders      = 5
max_replication_slots= 5
hot_standby          = on

# ── Query Planner ───────────────────────────────────────────
random_page_cost             = 1.1
effective_io_concurrency     = 200
default_statistics_target    = 200
seq_page_cost                = 1.0
max_parallel_workers_per_gather = 4
max_parallel_workers         = 8
max_parallel_maintenance_workers = 4
parallel_leader_participation = on

# ── Logging ─────────────────────────────────────────────────
logging_collector           = on
log_directory               = '${PG_LOG}'
log_filename                = 'postgresql-%Y-%m-%d.log'
log_rotation_age            = 1d
log_rotation_size           = 100MB
log_min_duration_statement  = 1000
log_checkpoints             = on
log_connections             = on
log_disconnections          = on
log_lock_waits              = on
log_temp_files              = 0
log_autovacuum_min_duration = 0
log_line_prefix             = '%t [%p-%l] %q%u@%d '
log_timezone                = 'Asia/Kolkata'

# ── Autovacuum ──────────────────────────────────────────────
autovacuum                       = on
autovacuum_max_workers           = 4
autovacuum_naptime               = 30s
autovacuum_vacuum_threshold      = 50
autovacuum_analyze_threshold     = 50
autovacuum_vacuum_scale_factor   = 0.1
autovacuum_analyze_scale_factor  = 0.05
autovacuum_vacuum_cost_delay     = 2ms

# ── Background Writer ───────────────────────────────────────
bgwriter_delay          = 200ms
bgwriter_lru_maxpages   = 100
bgwriter_lru_multiplier = 2.0
bgwriter_flush_after    = 512kB

# ── Lock & Timeout ──────────────────────────────────────────
statement_timeout       = 30000
lock_timeout            = 10000
deadlock_timeout        = 1s
max_locks_per_transaction = 128

# ── TCP Keepalives ──────────────────────────────────────────
tcp_keepalives_idle     = 600
tcp_keepalives_interval = 30
tcp_keepalives_count    = 10

# ── JIT ─────────────────────────────────────────────────────
jit = off

# ── Locale / Encoding ───────────────────────────────────────
timezone                    = 'Asia/Kolkata'
datestyle                   = 'iso, mdy'
lc_messages                 = 'en_US.UTF-8'
lc_monetary                 = 'en_US.UTF-8'
lc_numeric                  = 'en_US.UTF-8'
lc_time                     = 'en_US.UTF-8'
default_text_search_config  = 'pg_catalog.english'
EOF

chown "${PG_USER}:${PG_GROUP}" "${PG_DATA}/postgresql.conf"
chmod 0600 "${PG_DATA}/postgresql.conf"
ok "postgresql.conf written"
pause

# =============================================================================
# PHASE 7 — pg_hba.conf  (access control, mirrors source)
# =============================================================================
banner "PHASE 7 — Write pg_hba.conf"

cat > "${PG_DATA}/pg_hba.conf" <<EOF
# ============================================================
# Enable-LMS Enterprise — pg_hba.conf
# Generated by 01-target-pg-setup.sh on $(date)
# ============================================================

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Unix socket — local access (pgadmin OS user → peer)
local   all             ${PG_USER}                              peer
local   all             all                                     md5

# IPv4 localhost
host    all             ${PG_USER}      127.0.0.1/32            scram-sha-256
host    all             ${DB_APP_USER}  127.0.0.1/32            scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 localhost
host    all             all             ::1/128                 scram-sha-256

# App server / Docker host  (specific IP)
hostssl ${DB_NAME}      ${DB_APP_USER}  ${APP_SERVER_IP}/32     scram-sha-256
host    ${DB_NAME}      ${DB_APP_USER}  ${APP_SERVER_IP}/32     scram-sha-256

# Private network ranges (covers LAN, VPN, Docker subnets)
hostssl ${DB_NAME}      ${DB_APP_USER}  10.0.0.0/8              scram-sha-256
hostssl ${DB_NAME}      ${DB_APP_USER}  ${APP_SUBNET}           scram-sha-256
hostssl ${DB_NAME}      ${DB_APP_USER}  ${DOCKER_SUBNET}        scram-sha-256
host    ${DB_NAME}      ${DB_APP_USER}  10.0.0.0/8              scram-sha-256
host    ${DB_NAME}      ${DB_APP_USER}  ${DOCKER_SUBNET}        scram-sha-256
host    all             ${DB_APP_USER}  10.0.0.0/8              scram-sha-256

# Replication
host    replication     ${PG_USER}      127.0.0.1/32            scram-sha-256
host    replication     ${PG_USER}      ::1/128                 scram-sha-256
local   replication     ${PG_USER}                              peer
EOF

chown "${PG_USER}:${PG_GROUP}" "${PG_DATA}/pg_hba.conf"
chmod 0600 "${PG_DATA}/pg_hba.conf"
ok "pg_hba.conf written"
pause

# =============================================================================
# PHASE 8 — Generate Self-Signed SSL Certificate
# =============================================================================
banner "PHASE 8 — SSL Certificate"

if [[ -f "${PG_DATA}/server.crt" && -f "${PG_DATA}/server.key" ]]; then
    ok "SSL cert already exists — skipping"
else
    info "Generating self-signed TLS certificate (10-year validity)..."
    openssl req -new -x509 -days 3650 -nodes \
        -out  "${PG_DATA}/server.crt" \
        -keyout "${PG_DATA}/server.key" \
        -subj "/CN=lms-db.internal/O=Enable-LMS/C=IN" \
        -addext "subjectAltName=IP:${TARGET_IP},IP:127.0.0.1"
    chown "${PG_USER}:${PG_GROUP}" "${PG_DATA}/server.crt" "${PG_DATA}/server.key"
    chmod 0640 "${PG_DATA}/server.crt"
    chmod 0600 "${PG_DATA}/server.key"
    ok "SSL certificate generated"
    info "  cert: ${PG_DATA}/server.crt"
    info "  key:  ${PG_DATA}/server.key"
fi
pause

# =============================================================================
# PHASE 9 — Systemd Service  (postgres.service — mirrors source definition)
# =============================================================================
banner "PHASE 9 — Install systemd Service 'postgres.service'"

info "SELinux: setting file context for ${PG_BASE} and ${PG_DATA}..."
if command -v semanage &>/dev/null; then
    semanage fcontext -a -t postgresql_db_t "${PG_DATA}(/.*)?" 2>/dev/null || true
    semanage fcontext -a -t postgresql_log_t "${PG_LOG}(/.*)?"  2>/dev/null || true
    semanage fcontext -a -t postgresql_var_run_t "${PG_RUN}(/.*)?" 2>/dev/null || true
    restorecon -Rv "$PG_BASE" 2>/dev/null || true
    ok "SELinux contexts applied"
else
    warn "semanage not found — skipping SELinux context (install policycoreutils-python-utils if needed)"
fi

cat > /etc/systemd/system/postgres.service <<UNIT
[Unit]
Description=PostgreSQL 18 database server - LMS Enterprise
Documentation=https://www.postgresql.org/docs/18/
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=${PG_USER}
Group=${PG_GROUP}

# All PostgreSQL files consolidated under ${PG_BASE}
Environment=PGHOME=${PG_BASE}
Environment=PGDATA=${PG_DATA}
Environment=PGPORT=5432
Environment=PGLOG=${PG_LOG}
Environment=PGRUN=${PG_RUN}

ExecStartPre=/usr/bin/install -d -m 0755 -o ${PG_USER} -g ${PG_GROUP} ${PG_RUN}
ExecStart=${PG_BIN_LINK}/pg_ctl start -D \${PGDATA} -s -w -t 300
ExecStop=${PG_BIN_LINK}/pg_ctl stop  -D \${PGDATA} -s -m fast
ExecReload=${PG_BIN_LINK}/pg_ctl reload -D \${PGDATA} -s

TimeoutSec=300
Restart=on-failure
RestartSec=10

# Hardening
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
NoNewPrivileges=true

# Logging
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=postgresql

# Resource limits
LimitNOFILE=65536
LimitNPROC=65536

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
ok "postgres.service unit installed and daemon reloaded"
pause

# =============================================================================
# PHASE 10 — Start Service, Create DB Role & Database
# =============================================================================
banner "PHASE 10 — Start PostgreSQL & Create DB Objects"

info "Enabling and starting postgres.service..."
systemctl enable postgres.service
systemctl start postgres.service

# Wait up to 30s for postgres to be ready
for i in $(seq 1 30); do
    if sudo -u "$PG_USER" "${PG_BIN_LINK}/pg_isready" -h 127.0.0.1 -p 5432 -q 2>/dev/null; then
        ok "PostgreSQL is accepting connections (after ${i}s)"
        break
    fi
    sleep 1
    (( i == 30 )) && die "PostgreSQL did not start in 30s. Check logs: journalctl -u postgres.service -n 50"
done

info "Creating DB role '${DB_APP_USER}'..."
sudo -u "$PG_USER" "${PG_BIN_LINK}/psql" -h 127.0.0.1 -p 5432 -d postgres <<SQL
-- Role
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_APP_USER}') THEN
        CREATE ROLE "${DB_APP_USER}" WITH LOGIN PASSWORD '${DB_USER_PASSWORD}';
        RAISE NOTICE 'Role ${DB_APP_USER} created.';
    ELSE
        ALTER ROLE "${DB_APP_USER}" WITH PASSWORD '${DB_USER_PASSWORD}';
        RAISE NOTICE 'Role ${DB_APP_USER} password updated.';
    END IF;
END
\$\$;
SQL
ok "Role '${DB_APP_USER}' ready"

info "Creating database '${DB_NAME}'..."
DB_EXISTS=$(sudo -u "$PG_USER" "${PG_BIN_LINK}/psql" -h 127.0.0.1 -p 5432 -d postgres \
    -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';")
if [[ "$DB_EXISTS" == "1" ]]; then
    warn "Database '${DB_NAME}' already exists — skipping CREATE"
else
    sudo -u "$PG_USER" "${PG_BIN_LINK}/psql" -h 127.0.0.1 -p 5432 -d postgres \
        -c "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_APP_USER}\" ENCODING 'UTF8';"
    ok "Database '${DB_NAME}' created"
fi

info "Granting privileges..."
sudo -u "$PG_USER" "${PG_BIN_LINK}/psql" -h 127.0.0.1 -p 5432 -d "$DB_NAME" <<SQL
GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO "${DB_APP_USER}";
GRANT ALL ON SCHEMA public TO "${DB_APP_USER}";
ALTER DATABASE "${DB_NAME}" OWNER TO "${DB_APP_USER}";
SQL
ok "Privileges granted"
pause

# =============================================================================
# PHASE 11 — Firewall
# =============================================================================
banner "PHASE 11 — Firewall"

if command -v firewall-cmd &>/dev/null; then
    STATE=$(firewall-cmd --state 2>/dev/null || echo "not running")
    if [[ "$STATE" == "running" ]]; then
        info "Opening port 5432/tcp permanently..."
        firewall-cmd --permanent --add-port=5432/tcp
        firewall-cmd --reload
        ok "Port 5432 opened in firewalld"
    else
        warn "firewalld is installed but not running — opening port 5432 when it starts"
        firewall-cmd --permanent --add-port=5432/tcp 2>/dev/null || true
    fi
else
    warn "firewalld not found. Ensure port 5432 is open:"
    warn "  iptables -I INPUT -p tcp --dport 5432 -j ACCEPT"
fi

# =============================================================================
# PHASE 12 — Final Verification
# =============================================================================
banner "PHASE 12 — Verification"

info "Service status:"
systemctl status postgres.service --no-pager -l | head -20

info "pg_isready:"
sudo -u "$PG_USER" "${PG_BIN_LINK}/pg_isready" -h 127.0.0.1 -p 5432

info "PostgreSQL version:"
PGPASSWORD="$DB_USER_PASSWORD" "${PG_BIN_LINK}/psql" \
    -h 127.0.0.1 -p 5432 -U "$DB_APP_USER" -d "$DB_NAME" \
    -c "SELECT version();" -t

info "Database size:"
PGPASSWORD="$DB_USER_PASSWORD" "${PG_BIN_LINK}/psql" \
    -h 127.0.0.1 -p 5432 -U "$DB_APP_USER" -d "$DB_NAME" \
    -c "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'));" -t

info "Directory layout:"
ls -la "$PG_BASE"

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}"
cat <<DONE
 ╔══════════════════════════════════════════════════════════════╗
 ║   PostgreSQL 18 setup COMPLETE on ${TARGET_IP}           ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  PG base dir   :  ${PG_BASE}                ║
 ║  PGDATA        :  ${PG_DATA}           ║
 ║  WAL dir       :  ${PG_WAL}            ║
 ║  Archive dir   :  ${PG_ARCHIVE}        ║
 ║  Log dir       :  ${PG_LOG}            ║
 ║  Socket/PID    :  ${PG_RUN}            ║
 ║  Binaries      :  ${PG_BIN_LINK}/      ║
 ║  Service       :  postgres.service (systemd)                ║
 ║  Log file      :  ${LOG}    ║
 ╠══════════════════════════════════════════════════════════════╣
 ║  NEXT STEP: Run 02-db-migrate.sh FROM THE SOURCE MACHINE    ║
 ║    SOURCE (192.168.1.113):                                   ║
 ║    export TARGET_HOST='root@45.194.90.251'                  ║
 ║    bash scripts/02-db-migrate.sh                            ║
 ╚══════════════════════════════════════════════════════════════╝
DONE
echo -e "${NC}"
