#!/bin/bash
# =============================================================================
# Enable-LMS Enterprise — Service Control Script
#
# Usage:  ./lms-ctl.sh {start|stop|restart|status|logs|health}
#
# Commands:
#   start     Start all containers (build if images missing)
#   stop      Stop all containers (keeps volumes)
#   restart   Restart all containers (or a specific service)
#   status    Show container states, resource usage, and health
#   logs      Tail logs for all services (or a specific one)
#   health    Quick health check of all endpoints
#
# Examples:
#   ./lms-ctl.sh start
#   ./lms-ctl.sh restart api
#   ./lms-ctl.sh logs celery-worker
#   ./lms-ctl.sh status
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/docker/.env"

# ── Load environment ─────────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found."
    exit 1
fi
set -a; source "$ENV_FILE"; set +a

HTTP_PORT="${HTTP_PORT:-8080}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docker}"
COMPOSE="docker compose -f $COMPOSE_FILE -p $PROJECT_NAME"

# ── Color helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Wait for health endpoint ────────────────────────────────────────────────
wait_healthy() {
    local max="${1:-60}" i=0
    info "Waiting for health endpoint (max ${max}s)..."
    while [[ $i -lt $max ]]; do
        if curl -sf --max-time 3 "http://localhost:${HTTP_PORT}/health/" >/dev/null 2>&1; then
            ok "Healthy after ${i}s"
            return 0
        fi
        i=$((i+1)); sleep 1
    done
    err "Not healthy after ${max}s"
    return 1
}

# =============================================================================
# COMMANDS
# =============================================================================

cmd_start() {
    info "Starting Enable-LMS stack..."

    # Build images if they don't exist
    if ! docker image inspect enable-lms:${IMAGE_TAG:-latest} >/dev/null 2>&1; then
        info "Image not found — building..."
        $COMPOSE build --build-arg APP_VERSION="$(date +%s)" api
        $COMPOSE build nginx
    fi

    $COMPOSE up -d
    sleep 3
    wait_healthy 60

    echo ""
    ok "Enable-LMS is running"
    echo "  Local URL : http://localhost:${HTTP_PORT}/"
    echo "  Admin     : http://localhost:${HTTP_PORT}/admin/"
    echo "  Health    : http://localhost:${HTTP_PORT}/health/"
    echo "  Public    : https://lms.automatebot.shop/"
    echo ""
}

cmd_stop() {
    info "Stopping Enable-LMS stack..."
    $COMPOSE down
    ok "All containers stopped (volumes preserved)"
}

cmd_restart() {
    local service="${1:-}"
    if [[ -n "$service" ]]; then
        info "Restarting service: $service"
        $COMPOSE restart "$service"
        ok "$service restarted"
    else
        info "Restarting all services..."
        $COMPOSE down
        $COMPOSE up -d
        sleep 3
        wait_healthy 60
        ok "All services restarted"
    fi
}

cmd_status() {
    echo ""
    echo "=================================================================="
    echo "  Enable-LMS Enterprise — Service Status"
    echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "=================================================================="
    echo ""

    # Container status
    info "Container Status:"
    echo "─────────────────────────────────────────────────────────────────"
    docker ps --filter "name=${PROJECT_NAME}_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
        || $COMPOSE ps
    echo ""

    # Resource usage
    info "Resource Usage:"
    echo "─────────────────────────────────────────────────────────────────"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null \
        || info "stats unavailable"
    echo ""

    # Health check
    info "Health Check:"
    echo "─────────────────────────────────────────────────────────────────"
    local health
    health=$(curl -s --max-time 5 "http://localhost:${HTTP_PORT}/health/" 2>/dev/null)
    if [[ $? -eq 0 ]] && echo "$health" | python3 -m json.tool 2>/dev/null; then
        ok "API is healthy"
    else
        err "API health check failed"
    fi
    echo ""

    # Nginx self-check
    local nginx_status
    nginx_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:${HTTP_PORT}/nginx-health" 2>/dev/null)
    if [[ "$nginx_status" == "200" ]]; then
        ok "Nginx is healthy"
    else
        err "Nginx health check returned: $nginx_status"
    fi

    # Redis check
    local redis_container="${PROJECT_NAME}_redis_1"
    if docker exec "$redis_container" redis-cli ping 2>/dev/null | grep -q PONG; then
        ok "Redis is healthy (PONG)"
    else
        warn "Redis health check inconclusive"
    fi

    # Tunnel check
    local tunnel_container="${PROJECT_NAME}_tunnel_1"
    info "Tunnel (last 3 log lines):"
    docker logs --tail 3 "$tunnel_container" 2>&1 || warn "Cannot read tunnel logs"
    echo ""

    # Database connectivity
    info "Database:"
    echo "  Host: ${DB_HOST:-unknown}:${DB_PORT:-5432}"
    echo "  Name: ${DB_NAME:-unknown}"
    if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT 1;" >/dev/null 2>&1; then
        ok "PostgreSQL is connected"
    else
        err "PostgreSQL connection failed"
    fi
    echo ""
}

cmd_logs() {
    local service="${1:-}"
    if [[ -n "$service" ]]; then
        $COMPOSE logs -f --tail=100 "$service"
    else
        $COMPOSE logs -f --tail=50
    fi
}

cmd_health() {
    echo ""
    info "Quick endpoint health check"
    echo "─────────────────────────────────────────────────────────────────"

    local urls=(
        "/health/|Health API"
        "/|Home Page"
        "/admin/|Django Admin"
        "/login/|Login Page"
        "/api/v1/|API Root"
        "/nginx-health|Nginx"
        "/student/dashboard/|Student Dashboard"
        "/teacher/dashboard/|Teacher Dashboard"
        "/staff/dashboard/|Staff Dashboard"
        "/programs/|Programs"
        "/about/|About"
    )

    for entry in "${urls[@]}"; do
        IFS='|' read -r url name <<< "$entry"
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:${HTTP_PORT}${url}" 2>/dev/null)
        case "$code" in
            200)     printf "  ${GREEN}%-30s %s${NC}\n" "$name" "$code" ;;
            301|302) printf "  ${YELLOW}%-30s %s (redirect)${NC}\n" "$name" "$code" ;;
            401)     printf "  ${YELLOW}%-30s %s (auth required)${NC}\n" "$name" "$code" ;;
            *)       printf "  ${RED}%-30s %s${NC}\n" "$name" "$code" ;;
        esac
    done
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================
case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart "${2:-}" ;;
    status)  cmd_status ;;
    logs)    cmd_logs "${2:-}" ;;
    health)  cmd_health ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health} [service]"
        echo ""
        echo "Commands:"
        echo "  start             Start all containers"
        echo "  stop              Stop all containers (volumes kept)"
        echo "  restart [svc]     Restart all or a specific service"
        echo "  status            Full status report with resource usage"
        echo "  logs [svc]        Tail logs (all or specific service)"
        echo "  health            Quick HTTP endpoint checks"
        echo ""
        echo "Services: redis, api, websocket, celery-worker, celery-beat, nginx, tunnel"
        exit 1
        ;;
esac
