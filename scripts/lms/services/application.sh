#!/usr/bin/env bash
# Application tier — orchestrates full docker-compose stack
set -euo pipefail
LMS_ROOT=/u01/app/Enable-LMS
cd "${LMS_ROOT}/docker"

case "${1:-status}" in
  start)   docker compose up -d ;;
  stop)    docker compose stop ;;
  restart) docker compose restart ;;
  status)  docker compose ps ;;
  *) echo "Usage: $0 {start|stop|restart|status}"; exit 2 ;;
esac
