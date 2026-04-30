#!/usr/bin/env bash
# Backend tier — Django API, WebSocket (Daphne), Celery worker, Celery beat
set -euo pipefail
LMS_ROOT=/u01/app/Enable-LMS
cd "${LMS_ROOT}/docker"
SVCS=(api websocket celery-worker celery-beat)

case "${1:-status}" in
  start)   docker compose up -d "${SVCS[@]}" ;;
  stop)    docker compose stop "${SVCS[@]}" ;;
  restart) docker compose restart "${SVCS[@]}" ;;
  status)
    for s in "${SVCS[@]}"; do
      line=$(docker compose ps --format '{{.Name}} {{.State}} {{.Status}}' "$s" 2>/dev/null)
      [[ -n "$line" ]] && echo "  [ OK ]  $line" || echo "  [FAIL]  $s not running"
    done
    # API health endpoint
    code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' http://localhost:8000/health/ || echo 000)
    [[ "$code" =~ ^(200|204|301|302)$ ]] \
      && echo "  [ OK ]  /health/ : HTTP $code" \
      || echo "  [WARN]  /health/ : HTTP $code"
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;;
esac
