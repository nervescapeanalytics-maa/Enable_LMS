#!/usr/bin/env bash
# Database tier — PostgreSQL (host systemd service)
set -euo pipefail
PGSVC=${PGSVC:-postgres}

# Auto-detect systemd unit name (check running first, then unit files)
detect() {
  for u in postgres postgresql-18 postgresql-17 postgresql-16 postgresql-15 postgresql; do
    if systemctl list-units --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -qx "${u}.service"; then
      echo "$u"; return
    fi
  done
  for u in postgres postgresql-18 postgresql-17 postgresql-16 postgresql-15 postgresql; do
    if systemctl list-unit-files 2>/dev/null | grep -q "^${u}.service"; then
      echo "$u"; return
    fi
  done
  echo "postgres"
}
PGSVC=$(detect)

case "${1:-status}" in
  start)    systemctl start "$PGSVC"   && echo "  [ OK ]  $PGSVC started" ;;
  stop)     systemctl stop  "$PGSVC"   && echo "  [ OK ]  $PGSVC stopped" ;;
  restart)  systemctl restart "$PGSVC" && echo "  [ OK ]  $PGSVC restarted" ;;
  status)
    systemctl is-active --quiet "$PGSVC" \
      && echo "  [ OK ]  $PGSVC : active" \
      || echo "  [FAIL]  $PGSVC : inactive"
    # Connection test
    sudo -u pgadmin psql -h /d01/postgresql/run -d LMS_PROD_DB -c "SELECT 1;" >/dev/null 2>&1 \
      && echo "  [ OK ]  DB connect (LMS_PROD_DB) : OK" \
      || echo "  [WARN]  DB connect : FAILED"
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;;
esac
