#!/usr/bin/env bash
# Middleware tier — Redis (Docker container)
set -euo pipefail
LMS_ROOT=/u01/app/Enable-LMS
COMPOSE_FILE=${LMS_ROOT}/docker/docker-compose.yml
cd "${LMS_ROOT}/docker"
SVC=redis

case "${1:-status}" in
  start)   docker compose up -d "$SVC"    && echo "  [ OK ]  redis started" ;;
  stop)    docker compose stop "$SVC"     && echo "  [ OK ]  redis stopped" ;;
  restart) docker compose restart "$SVC"  && echo "  [ OK ]  redis restarted" ;;
  status)
    state=$(docker compose ps --format '{{.Name}} {{.State}} {{.Status}}' "$SVC" 2>/dev/null)
    if [[ -n "$state" ]]; then echo "  [ OK ]  $state"; else echo "  [FAIL]  redis not running"; fi
    docker compose exec -T "$SVC" redis-cli -a "$(grep '^REDIS_PASSWORD' /u01/app/Enable-LMS/docker/.env 2>/dev/null | cut -d= -f2 | tr -d '"')" ping 2>/dev/null \
      | grep -q PONG && echo "  [ OK ]  redis PING : PONG" || echo "  [WARN]  redis PING failed"
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;;
esac
