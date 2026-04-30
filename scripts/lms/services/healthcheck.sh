#!/usr/bin/env bash
# Comprehensive end-to-end healthcheck
set -euo pipefail
LMS_ROOT=/u01/app/Enable-LMS
cd "${LMS_ROOT}/docker"

pass=0; fail=0
ok()   { echo "  [ OK ]  $*"; pass=$((pass+1)); }
bad()  { echo "  [FAIL]  $*"; fail=$((fail+1)); }
section(){ echo; echo "── $* ──"; }

# 1. PostgreSQL — detect unit name
section "Database"
PGSVC=$(for u in postgres postgresql-18 postgresql-17 postgresql-16 postgresql; do
  if systemctl list-units --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -qx "${u}.service"; then echo "$u"; break; fi
done)
PGSVC=${PGSVC:-postgres}
if systemctl is-active --quiet "$PGSVC"; then ok "$PGSVC : active"; else bad "$PGSVC : inactive"; fi
if sudo -u pgadmin psql -h /d01/postgresql/run -d LMS_PROD_DB -c "SELECT 1;" >/dev/null 2>&1; then
  ok "DB (LMS_PROD_DB) reachable"
  rows=$(sudo -u pgadmin psql -h /d01/postgresql/run -d LMS_PROD_DB -tAc "SELECT COUNT(*) FROM students;" 2>/dev/null || echo 0)
  ok "students table rows: $rows"
else bad "DB unreachable"; fi

# 2. Redis
section "Middleware"
state=$(docker compose ps --format '{{.State}}' redis 2>/dev/null)
[[ "$state" == "running" ]] && ok "redis : $state" || bad "redis : $state"

# 3. Backend containers
section "Backend"
for c in api websocket celery-worker celery-beat; do
  st=$(docker compose ps --format '{{.State}}' "$c" 2>/dev/null)
  [[ "$st" == "running" ]] && ok "$c : $st" || bad "$c : $st"
done

# API endpoint
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health/ || echo 000)
[[ "$code" =~ ^(200|204|301|302)$ ]] && ok "api /health/ : HTTP $code" || bad "api /health/ : HTTP $code"

# 4. Frontend
section "Frontend"
for c in nginx tunnel; do
  st=$(docker compose ps --format '{{.State}}' "$c" 2>/dev/null)
  [[ "$st" == "running" ]] && ok "$c : $st" || bad "$c : $st"
done
# nginx is internal-only (accessed via tunnel); check via container
code=$(docker compose exec -T nginx wget -qO- -S http://127.0.0.1/ 2>&1 | grep -oE 'HTTP/[0-9.]+ [0-9]+' | head -1 | awk '{print $2}')
code=${code:-000}
[[ "$code" =~ ^(200|301|302|403)$ ]] && ok "nginx (internal) : HTTP $code" || bad "nginx (internal) : HTTP $code"

# 5. Summary
section "Summary"
echo "  Passed: $pass   Failed: $fail"
exit $(( fail > 0 ? 1 : 0 ))
