#!/usr/bin/env bash
# Frontend tier — Nginx reverse proxy + Cloudflare tunnel
set -euo pipefail
LMS_ROOT=/u01/app/Enable-LMS
cd "${LMS_ROOT}/docker"
SVCS=(nginx tunnel)

case "${1:-status}" in
  start)   docker compose up -d "${SVCS[@]}" ;;
  stop)    docker compose stop "${SVCS[@]}" ;;
  restart) docker compose restart "${SVCS[@]}" ;;
  status)
    for s in "${SVCS[@]}"; do
      line=$(docker compose ps --format '{{.Name}} {{.State}} {{.Status}}' "$s" 2>/dev/null)
      [[ -n "$line" ]] && echo "  [ OK ]  $line" || echo "  [FAIL]  $s not running"
    done
    code=$(docker compose exec -T nginx wget -qO- -S http://127.0.0.1/ 2>&1 | grep -oE 'HTTP/[0-9.]+ [0-9]+' | head -1 | awk '{print $2}')
    code=${code:-000}
    [[ "$code" =~ ^(200|301|302|403)$ ]] \
      && echo "  [ OK ]  nginx (internal) : HTTP $code" \
      || echo "  [WARN]  nginx (internal) : HTTP $code"
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;;
esac
