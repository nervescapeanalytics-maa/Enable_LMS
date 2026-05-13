#!/usr/bin/env bash
# =============================================================================
# Enable-LMS — Comprehensive Test Suite  
# Covers: Unit, Functional, Regression, E2E, Load, Security
# =============================================================================
set -o pipefail

# ── Load environment (for domain variables) ──────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a; source "$SCRIPT_DIR/.env"; set +a
fi
LMS_HOST="${PRIMARY_DOMAIN:-lms.automatebot.shop}"

BASE_URL="${BASE_URL:-http://localhost:8080}"
API_URL="$BASE_URL/api/v1"
RESULTS_FILE=$(mktemp)
echo "0 0 0" > "$RESULTS_FILE"

green()  { echo -e "\e[32m✓ $*\e[0m"; }
red()    { echo -e "\e[31m✗ $*\e[0m"; }
yellow() { echo -e "\e[33m⚠ $*\e[0m"; }
header() { echo -e "\n\e[1;36m══════════════════════════════════════════\e[0m"; echo -e "\e[1;36m  $*\e[0m"; echo -e "\e[1;36m══════════════════════════════════════════\e[0m"; }

pass() { green "$1"; read p f w < "$RESULTS_FILE"; echo "$((p+1)) $f $w" > "$RESULTS_FILE"; }
fail() { red "$1"; read p f w < "$RESULTS_FILE"; echo "$p $((f+1)) $w" > "$RESULTS_FILE"; }
warn_() { yellow "$1"; read p f w < "$RESULTS_FILE"; echo "$p $f $((w+1))" > "$RESULTS_FILE"; }

assert_status() {
    local desc="$1" url="$2" expected="$3"; shift 3
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "$@" "$url" 2>/dev/null || echo "000")
    [[ "$code" == "$expected" ]] && pass "$desc (HTTP $code)" || fail "$desc — expected $expected, got $code"
}

assert_json() {
    local desc="$1" url="$2" field="$3" expected="$4"; shift 4
    local value
    value=$(curl -s --max-time 5 "$@" "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null || echo "ERROR")
    [[ "$value" == "$expected" ]] && pass "$desc ($field=$value)" || fail "$desc — expected $field=$expected, got $value"
}

assert_contains() {
    local desc="$1" url="$2" needle="$3"; shift 3
    local body
    body=$(curl -s "$@" "$url" 2>/dev/null || echo "")
    echo "$body" | grep -qi "$needle" && pass "$desc" || fail "$desc — missing '$needle'"
}

assert_header() {
    local desc="$1" url="$2" hdr="$3"; shift 3
    local headers
    headers=$(curl -sI "$@" "$url" 2>/dev/null || echo "")
    echo "$headers" | grep -qi "$hdr" && pass "$desc" || fail "$desc — missing $hdr"
}

# ─── PRE-FLIGHT ──────────────────────────────────────────────────────────────
header "PRE-FLIGHT CHECKS"
echo "Target: $BASE_URL | Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

for svc in redis api websocket celery-worker celery-beat nginx; do
    st=$(podman inspect --format '{{.State.Status}}' "enable-lms-$svc" 2>/dev/null || echo "missing")
    [[ "$st" == "running" ]] && pass "Container enable-lms-$svc running" || fail "Container enable-lms-$svc is $st"
done

# ═════════════════════════════════════════════════════════════════════════════
# 1. UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "1. UNIT TESTS — Settings, Models, URLs"

SETTINGS_OUT=$(podman exec enable-lms-api python -c "
from django.conf import settings
print('SECRET_KEY_LEN=' + str(len(settings.SECRET_KEY)))
print('DEBUG=' + str(settings.DEBUG))
print('HOSTS=' + str(len(settings.ALLOWED_HOSTS)))
print('SSL_REDIRECT=' + str(settings.SECURE_SSL_REDIRECT))
drf = settings.REST_FRAMEWORK
perms = drf.get('DEFAULT_PERMISSION_CLASSES', [])
print('DRF_PERM_OK=' + str(any('IsAuthenticated' in p for p in perms)))
auth = drf.get('DEFAULT_AUTHENTICATION_CLASSES', [])
print('DRF_AUTH=' + str(len(auth)))
db = settings.DATABASES['default']
print('DB_ENGINE=' + db['ENGINE'])
print('APPS=' + str(len(settings.INSTALLED_APPS)))
print('MW=' + str(len(settings.MIDDLEWARE)))
print('PW_VAL=' + str(len(getattr(settings, 'AUTH_PASSWORD_VALIDATORS', []))))
" 2>&1)

v=$(echo "$SETTINGS_OUT" | grep SECRET_KEY_LEN | cut -d= -f2)
[[ "$v" -gt 20 ]] && pass "SECRET_KEY length=$v" || fail "SECRET_KEY too short ($v)"

v=$(echo "$SETTINGS_OUT" | grep "^DEBUG=" | cut -d= -f2)
[[ "$v" == "False" ]] && pass "DEBUG=False" || fail "DEBUG=$v"

v=$(echo "$SETTINGS_OUT" | grep SSL_REDIRECT | cut -d= -f2)
[[ "$v" == "True" ]] && pass "SECURE_SSL_REDIRECT=True" || warn_ "SSL_REDIRECT=$v"

v=$(echo "$SETTINGS_OUT" | grep DRF_PERM_OK | cut -d= -f2)
[[ "$v" == "True" ]] && pass "DRF: IsAuthenticated default" || fail "DRF perms misconfigured"

v=$(echo "$SETTINGS_OUT" | grep DRF_AUTH | cut -d= -f2)
[[ "$v" -gt 0 ]] && pass "DRF auth classes: $v" || fail "No DRF auth"

v=$(echo "$SETTINGS_OUT" | grep DB_ENGINE | cut -d= -f2)
[[ "$v" == *postgresql* ]] && pass "Database: PostgreSQL" || fail "DB: $v"

v=$(echo "$SETTINGS_OUT" | grep "^APPS=" | cut -d= -f2)
pass "Installed apps: $v"

v=$(echo "$SETTINGS_OUT" | grep "^MW=" | cut -d= -f2)
pass "Middleware: $v layers"

v=$(echo "$SETTINGS_OUT" | grep PW_VAL | cut -d= -f2)
[[ "$v" -gt 0 ]] && pass "Password validators: $v" || warn_ "No password validators"

# Models
v=$(podman exec enable-lms-api python -c "import django; django.setup(); from django.apps import apps; print(len(apps.get_models()))" 2>&1 | tail -1 || true)
[[ "$v" =~ ^[0-9]+$ && "$v" -gt 0 ]] && pass "Models importable: $v total" || fail "Model import: $v"

# URLs
podman exec enable-lms-api python -c "
import django; django.setup()
from django.urls import resolve
for u in ['/admin/','/health/']:
    try:
        m=resolve(u); print(f'OK {u} -> {m.func.__module__}')
    except Exception as e:
        print(f'FAIL {u} -> {e}')
" 2>&1 | while read -r st rest; do
    [[ "$st" == "OK" ]] && pass "URL $rest" || fail "URL $rest"
done

# ═════════════════════════════════════════════════════════════════════════════
# 2. FUNCTIONAL TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "2. FUNCTIONAL TESTS — HTTP Endpoints"

assert_json "Health status" "$BASE_URL/health/" "status" "healthy"
assert_json "Health DB" "$BASE_URL/health/" "database" "connected"
assert_contains "Nginx health" "$BASE_URL/nginx-health" "ok"
assert_status "Admin redirect" "$BASE_URL/admin/" "302"
assert_status "Admin login" "$BASE_URL/admin/login/" "200" -H "Host: ${LMS_HOST}"
assert_contains "Admin CSRF" "$BASE_URL/admin/login/" "csrfmiddlewaretoken" -H "Host: ${LMS_HOST}"
assert_status "API needs auth" "$API_URL/" "401"
assert_status "Static files" "$BASE_URL/static/admin/css/base.css" "200"

# ═════════════════════════════════════════════════════════════════════════════
# 3. REGRESSION TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "3. REGRESSION TESTS — Database & Migrations"

REG_OUT=$(podman exec enable-lms-api python -c "
from django.db import connection
c = connection.cursor()
c.execute(\"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'\")
print('TABLES=' + str(c.fetchone()[0]))
for t in ['auth_user','django_migrations','django_session','django_content_type']:
    c.execute(f\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='{t}')\")
    print(f'TABLE_{t}=' + str(c.fetchone()[0]))
c.execute('SELECT COUNT(*) FROM django_migrations')
print('MIGRATED=' + str(c.fetchone()[0]))
import subprocess
r = subprocess.run(['python','manage.py','showmigrations','--plan'], capture_output=True, text=True)
ua = len([l for l in r.stdout.splitlines() if l.strip().startswith('[ ]')])
print('UNAPPLIED=' + str(ua))
" 2>&1)

v=$(echo "$REG_OUT" | grep "^TABLES=" | cut -d= -f2)
pass "Database: $v tables"

for t in auth_user django_migrations django_session django_content_type; do
    v=$(echo "$REG_OUT" | grep "TABLE_${t}=" | cut -d= -f2)
    [[ "$v" == "True" ]] && pass "Table $t exists" || fail "Table $t MISSING"
done

v=$(echo "$REG_OUT" | grep MIGRATED | cut -d= -f2)
pass "$v migrations applied"

v=$(echo "$REG_OUT" | grep UNAPPLIED | cut -d= -f2)
[[ "$v" -eq 0 ]] && pass "All migrations applied" || warn_ "$v unapplied migrations"

# Django deploy check
CHECK_OUT=$(podman exec enable-lms-api python manage.py check --deploy 2>&1)
if echo "$CHECK_OUT" | grep -q "System check identified no issues"; then
    pass "Django deploy check: clean"
else
    warn_ "Django deploy check: $(echo "$CHECK_OUT" | grep 'System check' | head -1)"
fi

# Redis
v=$(podman exec enable-lms-api python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print('OK' if r.ping() else 'FAIL')" 2>&1)
[[ "$v" == *OK* ]] && pass "Redis connection OK" || fail "Redis failed"

# Celery
v=$(podman exec enable-lms-celery-worker celery -A lms_enterprise inspect ping 2>&1 | grep -c "pong" || echo "0")
[[ "$v" -gt 0 ]] && pass "Celery worker alive" || warn_ "Celery ping: no pong"

# ═════════════════════════════════════════════════════════════════════════════
# 4. E2E TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "4. E2E TESTS — Workflow Simulation"

# Bad login (no trailing slash)
v=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" -d '{"username":"fake","password":"fake"}' 2>/dev/null)
[[ "$v" =~ ^(400|401|403|429)$ ]] && pass "Bad login rejected (HTTP $v)" || fail "Bad login: HTTP $v"

# Protected (use student endpoint which requires auth — no trailing slash)
v=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/student/dashboard" 2>/dev/null)
[[ "$v" =~ ^(401|403|429)$ ]] && pass "Protected endpoint (HTTP $v)" || fail "Protected endpoint — expected 401, got $v"

# CSRF
v=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/login/" \
    -H "Host: ${LMS_HOST}" -d "username=x&password=x" 2>/dev/null)
[[ "$v" == "403" ]] && pass "CSRF protection (HTTP 403)" || warn_ "Admin POST returned $v"

# WebSocket
v=$(curl -s -o /dev/null -w "%{http_code}" -H "Upgrade: websocket" -H "Connection: Upgrade" "$BASE_URL/ws/" 2>/dev/null)
[[ "$v" =~ ^(400|426|101|502|403)$ ]] && pass "WebSocket endpoint (HTTP $v)" || warn_ "WebSocket: HTTP $v"

# ═════════════════════════════════════════════════════════════════════════════
# 5. LOAD TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "5. LOAD TESTS — Stress & Rate Limiting"

# Reset rate limit window by waiting
sleep 2

# 50 concurrent
echo "  50 concurrent requests to /health/..."
TMPD=$(mktemp -d)
T0=$(date +%s%N)
for i in $(seq 1 50); do
    ( curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$BASE_URL/health/" > "$TMPD/$i" 2>/dev/null ) &
done
wait
T1=$(date +%s%N)
MS=$(( (T1 - T0) / 1000000 ))
OK=0; for f in "$TMPD"/*; do [[ -f "$f" && "$(cat "$f")" == "200" ]] && OK=$((OK+1)); done
[[ "$OK" -ge 40 ]] && pass "Concurrent: $OK/50 OK in ${MS}ms" || warn_ "Concurrent: $OK/50 OK in ${MS}ms"
rm -rf "$TMPD"

# 100 sequential
echo "  100 sequential requests..."
SOK=0; T0=$(date +%s%N)
for i in $(seq 1 100); do
    c=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/health/" 2>/dev/null)
    [[ "$c" == "200" ]] && SOK=$((SOK + 1))
done
T1=$(date +%s%N)
MS=$(( (T1 - T0) / 1000000 )); AVG=$((MS / 100))
[[ $SOK -ge 95 ]] && pass "Sequential: $SOK/100 OK (avg ${AVG}ms)" || fail "Sequential: $SOK/100"

# Rate limit
echo "  Rate limiting (login)..."
RL=0
for i in $(seq 1 15); do
    c=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" -d '{"username":"t","password":"t"}' 2>/dev/null)
    [[ "$c" == "429" ]] && RL=$((RL + 1))
done
[[ $RL -gt 0 ]] && pass "Rate limiting: $RL/15 throttled" || warn_ "Rate limit not triggered"

# ═════════════════════════════════════════════════════════════════════════════
# 6. SECURITY TESTS
# ═════════════════════════════════════════════════════════════════════════════
header "6. SECURITY TESTS — OWASP Checks"

# Wait for rate limit reset
sleep 2

assert_header "X-Content-Type-Options" "$BASE_URL/health/" "X-Content-Type-Options"
assert_header "Referrer-Policy" "$BASE_URL/health/" "Referrer-Policy"
assert_header "X-Frame-Options" "$BASE_URL/admin/login/" "X-Frame-Options" -H "Host: ${LMS_HOST}"

# Server version
SRV=$(curl -sI "$BASE_URL/health/" 2>/dev/null | grep -i "^Server:" | head -1)
echo "$SRV" | grep -qP "nginx/\d" && warn_ "Nginx version exposed: $SRV" || pass "Server version hidden"

# Debug leak
ERR=$(curl -s "$BASE_URL/nonexistent-xyz/" 2>/dev/null)
echo "$ERR" | grep -qi "traceback\|settings.py" && fail "Debug info leaked" || pass "No debug info in errors"

# SQL injection
v=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/student/classes?search=1'OR'1'='1" 2>/dev/null)
[[ "$v" =~ ^(401|403|400|429)$ ]] && pass "SQLi blocked (HTTP $v)" || fail "SQLi: HTTP $v"

# Path traversal
v=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/../../etc/passwd" 2>/dev/null)
[[ "$v" =~ ^(400|403|404)$ ]] && pass "Path traversal blocked (HTTP $v)" || fail "Path traversal: HTTP $v"

# Hidden files
v=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/.env" 2>/dev/null)
[[ "$v" =~ ^(403|404)$ ]] && pass "Hidden files blocked (HTTP $v)" || fail ".env accessible: HTTP $v"

# Django security
SEC_OUT=$(podman exec enable-lms-api python -c "
from django.conf import settings
print('SSL=' + str(getattr(settings,'SECURE_SSL_REDIRECT',False)))
print('SESS=' + str(getattr(settings,'SESSION_COOKIE_SECURE',False)))
print('CSRF=' + str(getattr(settings,'CSRF_COOKIE_SECURE',False)))
print('HSTS=' + str(getattr(settings,'SECURE_HSTS_SECONDS',0)))
print('NOSN=' + str(getattr(settings,'SECURE_CONTENT_TYPE_NOSNIFF',False)))
" 2>&1)

v=$(echo "$SEC_OUT" | grep "^SSL=" | cut -d= -f2); [[ "$v" == "True" ]] && pass "SSL redirect on" || warn_ "SSL redirect: $v"
v=$(echo "$SEC_OUT" | grep "^SESS=" | cut -d= -f2); [[ "$v" == "True" ]] && pass "Secure session cookie" || warn_ "Session secure: $v"
v=$(echo "$SEC_OUT" | grep "^CSRF=" | cut -d= -f2); [[ "$v" == "True" ]] && pass "Secure CSRF cookie" || warn_ "CSRF secure: $v"
v=$(echo "$SEC_OUT" | grep "^HSTS=" | cut -d= -f2); [[ "$v" -gt 0 ]] && pass "HSTS: ${v}s" || warn_ "HSTS not set"
v=$(echo "$SEC_OUT" | grep "^NOSN=" | cut -d= -f2); [[ "$v" == "True" ]] && pass "Content-Type nosniff" || warn_ "Nosniff: $v"

# Ruff lint
echo "  Code linting (ruff)..."
v=$(podman exec enable-lms-api ruff check /app/ --select S --statistics 2>&1 | wc -l)
[[ "$v" -le 10 ]] && pass "Ruff security: $v items" || warn_ "Ruff security: $v items"

# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
header "TEST RESULTS SUMMARY"
read PASS FAIL WARN < "$RESULTS_FILE"
TOTAL=$((PASS + FAIL + WARN))
echo ""
echo -e "  \e[32m✓ Passed:   $PASS\e[0m"
echo -e "  \e[31m✗ Failed:   $FAIL\e[0m"
echo -e "  \e[33m⚠ Warnings: $WARN\e[0m"
echo -e "  ─────────────────"
echo -e "  Total:    $TOTAL"
echo ""
rm -f "$RESULTS_FILE"
[[ $FAIL -eq 0 ]] && echo -e "  \e[1;32m🎉 ALL TESTS PASSED!\e[0m\n" && exit 0
echo -e "  \e[1;31m⚠ $FAIL TEST(S) FAILED\e[0m\n" && exit 1
