#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# lms-ctl — Unified LMS service controller
# Works from any user via sudo. Delegates to /u01/app/Enable-LMS/scripts/lms/services/*.sh
# Usage:
#   sudo lms-ctl start|stop|status|restart|list [service]
#   sudo lms-ctl healthcheck
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

LMS_ROOT=/u01/app/Enable-LMS
SVC_DIR=${LMS_ROOT}/scripts/lms/services
COMPOSE_FILE=${LMS_ROOT}/docker/docker-compose.yml
LOG_DIR=/var/log/lms
mkdir -p "$LOG_DIR"

# Each entry: "NAME|SCRIPT|TIER"
SERVICES=(
  "database|database.sh|data"
  "middleware|middleware.sh|data"
  "backend|backend.sh|app"
  "frontend|frontend.sh|app"
  "application|application.sh|app"
)

color() { local c=$1; shift; printf "\e[${c}m%s\e[0m\n" "$*"; }
ok()    { color "32" "  [ OK ]  $*"; }
warn()  { color "33" "  [WARN]  $*"; }
err()   { color "31" "  [FAIL]  $*"; }
info()  { color "36" "  [INFO]  $*"; }

need_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Re-running with sudo..."; exec sudo -E "$0" "$@"
  fi
}

usage() {
  cat <<EOF
lms-ctl — LMS Service Controller

USAGE:
  sudo lms-ctl <command> [service]

COMMANDS:
  start       [svc]   Start all services (or one)
  stop        [svc]   Stop all services (or one)
  restart     [svc]   Restart all services (or one)
  status      [svc]   Show status of all (or one)
  list                List all registered services + scripts
  healthcheck         Run full application health check
  logs        [svc]   Tail logs for one container

SERVICES:
  database     — PostgreSQL (host systemd service)
  middleware   — Redis (container)
  backend      — Django API + Celery worker + Celery beat + WebSocket
  frontend     — Nginx
  application  — Full docker stack (api + websocket + workers + nginx)

EXAMPLES:
  sudo lms-ctl start                  # Start everything
  sudo lms-ctl status                 # Show all statuses
  sudo lms-ctl restart backend        # Restart just backend containers
  sudo lms-ctl healthcheck            # Full E2E health check
  sudo lms-ctl logs api               # Tail API container logs
EOF
}

run_service() {
  local svc=$1 action=$2
  local script="${SVC_DIR}/${svc}.sh"
  [[ -x "$script" ]] || { err "Script missing: $script"; return 1; }
  "$script" "$action"
}

cmd=${1:-}; target=${2:-}

case "$cmd" in
  list)
    printf "%-15s %-30s %-10s\n" "SERVICE" "SCRIPT" "TIER"
    printf "%-15s %-30s %-10s\n" "---------------" "------------------------------" "----------"
    for row in "${SERVICES[@]}"; do
      IFS='|' read -r n s t <<< "$row"
      printf "%-15s %-30s %-10s\n" "$n" "${SVC_DIR}/${s}" "$t"
    done
    ;;
  start|stop|restart|status)
    need_root "$@"
    if [[ -n "$target" ]]; then
      run_service "$target" "$cmd"
    else
      # data-tier first on start; reverse on stop
      order=(database middleware backend frontend)
      [[ "$cmd" == "stop" ]] && order=(frontend backend middleware database)
      for svc in "${order[@]}"; do
        info "── $cmd :: $svc ──"
        run_service "$svc" "$cmd" || err "$svc $cmd failed"
      done
    fi
    ;;
  healthcheck)
    need_root "$@"
    exec "${SVC_DIR}/healthcheck.sh"
    ;;
  logs)
    need_root "$@"
    [[ -n "$target" ]] || { err "Usage: lms-ctl logs <container-service>"; exit 1; }
    cd "${LMS_ROOT}/docker" && docker compose logs -f --tail=200 "$target"
    ;;
  ""|-h|--help|help) usage ;;
  *) err "Unknown command: $cmd"; usage; exit 2 ;;
esac
