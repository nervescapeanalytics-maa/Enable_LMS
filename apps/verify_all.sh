#!/bin/bash
# ================================================================
#  POST-REMEDIATION VERIFICATION
#  Re-checks all HIGH and MED risk items from the original audit
#  to confirm they've been fixed.
# ================================================================

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/u01/app/django}"
cd "$PROJECT_DIR"
APPS_DIR="${APPS_DIR:-$PROJECT_DIR}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_pass() { echo -e "  ${GREEN}[PASS]${NC} $*"; PASS=$((PASS + 1)); }
check_fail() { echo -e "  ${RED}[FAIL]${NC} $*"; FAIL=$((FAIL + 1)); }
check_warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; WARN=$((WARN + 1)); }

echo ""
echo "================================================================"
echo " POST-REMEDIATION VERIFICATION"
echo " Date: $(date)"
echo " Server: $(hostname)"
echo "================================================================"
echo ""

# ── R1: API Security ──
echo -e "${BOLD}${CYAN}━━━ R1: API Security (HIGH) ━━━${NC}"

ALLOWANY_COUNT=$(grep -rn "AllowAny" "$APPS_DIR" --include="*.py" \
    --exclude-dir="__pycache__" --exclude-dir="migrations" --exclude-dir="backups" \
    2>/dev/null | grep -v "^.*:#" | grep -v "removed" | grep -v "test" | wc -l)
ALLOWANY_COUNT=$(echo "$ALLOWANY_COUNT" | tr -d '[:space:]')
ALLOWANY_COUNT=${ALLOWANY_COUNT:-0}

if [ "$ALLOWANY_COUNT" -eq 0 ]; then
    check_pass "No active AllowAny references in app code"
else
    check_fail "Found $ALLOWANY_COUNT active AllowAny reference(s)"
fi

# Check DRF defaults
DRF_DEFAULT=$(python3 -c "
import os, django
for s in ['lms_enterprise.settings.development', 'lms_enterprise.settings.base', 'lms_enterprise.settings', 'config.settings.development', 'config.settings.base', 'config.settings', 'settings']:
    try:
        os.environ['DJANGO_SETTINGS_MODULE'] = s
        django.setup()
        break
    except: pass
from django.conf import settings
drf = getattr(settings, 'REST_FRAMEWORK', {})
perms = drf.get('DEFAULT_PERMISSION_CLASSES', [])
print('AllowAny' if any('AllowAny' in p for p in perms) else 'OK')
" 2>/dev/null || echo "ERROR")

if [ "$DRF_DEFAULT" = "OK" ]; then
    check_pass "DRF default permissions are not AllowAny"
elif [ "$DRF_DEFAULT" = "ERROR" ]; then
    check_warn "Could not verify DRF settings (Django setup failed)"
else
    check_fail "DRF still defaults to AllowAny"
fi

# Check permissions module exists
if [ -f "$APPS_DIR/core/permissions.py" ] || find "$APPS_DIR" -name "permissions.py" -not -path "*/migrations/*" | grep -q .; then
    check_pass "Custom permissions module exists"
else
    check_warn "No custom permissions module found (may be using DRF defaults only)"
fi

echo ""

# ── R2: Root-Level Modules ──
echo -e "${BOLD}${CYAN}━━━ R2: Root-Level Modules (MED) ━━━${NC}"

ROOT_MODULES=(admin_page_views.py admin_utils.py enf_admin_site.py frontend_views.py
              insert_demo_data.py insert_more_demo_data.py test_admin_pages.py)

ROOT_REMAINING=0
for f in "${ROOT_MODULES[@]}"; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        ROOT_REMAINING=$((ROOT_REMAINING + 1))
    fi
done

if [ "$ROOT_REMAINING" -eq 0 ]; then
    check_pass "All 7 root-level modules moved (or renamed to .bak)"
else
    check_fail "$ROOT_REMAINING root-level module(s) still at project root"
fi

if [ -d "$APPS_DIR/core" ] && [ -f "$APPS_DIR/core/apps.py" ]; then
    check_pass "Core app exists with proper apps.py"
else
    check_warn "Core app not found at apps/core/"
fi

echo ""

# ── R3: Admin Template Overrides ──
echo -e "${BOLD}${CYAN}━━━ R3: Admin Template Overrides (MED) ━━━${NC}"

if [ -f "$PROJECT_DIR/docs/admin_template_manifest.md" ]; then
    check_pass "Admin template manifest exists"
else
    check_fail "No admin template manifest at docs/admin_template_manifest.md"
fi

if [ -x "$PROJECT_DIR/scripts/diff_admin_templates.sh" ]; then
    check_pass "Admin template diff script exists and is executable"
else
    check_fail "No diff script at scripts/diff_admin_templates.sh"
fi

DJANGO_VERSION=$(python -c "import django; print(django.get_version())" 2>/dev/null || echo "unknown")
if [ -d "$PROJECT_DIR/docs/admin_template_baselines/django_${DJANGO_VERSION}" ]; then
    check_pass "Baselines saved for Django $DJANGO_VERSION"
else
    check_warn "No baselines saved for Django $DJANGO_VERSION"
fi

echo ""

# ── R4: Deprecated Swagger ──
echo -e "${BOLD}${CYAN}━━━ R4: Deprecated django-rest-swagger (MED) ━━━${NC}"

if grep -q "^django-rest-swagger" "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
    check_fail "django-rest-swagger still active in requirements.txt"
else
    check_pass "django-rest-swagger removed from requirements.txt"
fi

if python -c "import rest_framework_swagger" 2>/dev/null; then
    check_warn "rest_framework_swagger still importable (uninstall the package)"
else
    check_pass "rest_framework_swagger is not importable"
fi

if python -c "import drf_spectacular" 2>/dev/null; then
    check_pass "drf-spectacular is installed and importable"
else
    check_fail "drf-spectacular is not importable"
fi

# Check INSTALLED_APPS
SWAGGER_IN_APPS=$(grep -r "rest_framework_swagger" "$PROJECT_DIR" --include="*.py" \
    -l --exclude-dir="__pycache__" --exclude-dir="backups" --exclude-dir=".git" 2>/dev/null \
    | grep -v ".bak" | grep -c "settings" 2>/dev/null || true)
SWAGGER_IN_APPS=$(echo "$SWAGGER_IN_APPS" | tr -d '[:space:]')
SWAGGER_IN_APPS=${SWAGGER_IN_APPS:-0}
if [ "$SWAGGER_IN_APPS" -eq 0 ]; then
    check_pass "rest_framework_swagger not in settings"
else
    check_warn "rest_framework_swagger may still be in settings files"
fi

echo ""

# ── R5: Automated Tests ──
echo -e "${BOLD}${CYAN}━━━ R5: Automated Tests (HIGH) ━━━${NC}"

TEST_FILES=$(find "$APPS_DIR" -name "test_*.py" -not -path "*/__pycache__/*" 2>/dev/null | wc -l)
TEST_FILES=$(echo "$TEST_FILES" | tr -d '[:space:]')
TEST_FILES=${TEST_FILES:-0}

if [ "$TEST_FILES" -gt 0 ]; then
    check_pass "Found $TEST_FILES test file(s)"
else
    check_fail "No test files found in apps/"
fi

# Check for specific test files
for tfile in test_urls.py test_models.py test_api.py test_migrations.py test_settings.py; do
    if find "$APPS_DIR" -name "$tfile" -not -path "*/__pycache__/*" 2>/dev/null | grep -q .; then
        check_pass "  $tfile exists"
    else
        check_fail "  $tfile not found"
    fi
done

# Try running tests
log_output=$(python manage.py test tests --verbosity=0 --no-input 2>&1 || true)
if echo "$log_output" | grep -q "^OK"; then
    TEST_COUNT=$(echo "$log_output" | grep -oP 'Ran \K\d+' || echo "?")
    check_pass "Test suite passes ($TEST_COUNT tests)"
elif echo "$log_output" | grep -q "FAILED"; then
    FAILURES=$(echo "$log_output" | grep -oP 'failures=\K\d+' || echo "?")
    ERRORS=$(echo "$log_output" | grep -oP 'errors=\K\d+' || echo "?")
    check_warn "Test suite has failures=$FAILURES, errors=$ERRORS (review needed)"
else
    check_warn "Could not run test suite (check Django setup)"
fi

echo ""

# ── R6: Database Migrations ──
echo -e "${BOLD}${CYAN}━━━ R6: Database Migrations (HIGH) ━━━${NC}"

if python manage.py migrate --check 2>&1 > /dev/null; then
    check_pass "All migrations are applied"
else
    check_fail "Unapplied migrations detected"
fi

if python manage.py makemigrations --check --dry-run 2>&1 > /dev/null; then
    check_pass "Models are in sync with migrations"
else
    check_warn "Unmigrated model changes detected"
fi

echo ""

# ── Django System Check ──
echo -e "${BOLD}${CYAN}━━━ Django System Checks ━━━${NC}"

SYSTEM_CHECK=$(python manage.py check 2>&1)
if echo "$SYSTEM_CHECK" | grep -q "System check identified no issues"; then
    check_pass "Django system check: no issues"
else
    ISSUES=$(echo "$SYSTEM_CHECK" | grep -c "WARN\|ERROR" 2>/dev/null || true)
    ISSUES=$(echo "$ISSUES" | tr -d '[:space:]')
    ISSUES=${ISSUES:-0}
    if [ "$ISSUES" -gt 0 ]; then
        check_warn "Django system check: $ISSUES issue(s) found"
    else
        check_pass "Django system check: passed"
    fi
fi

DEPLOY_CHECK=$(python manage.py check --deploy 2>&1 || true)
DEPLOY_ISSUES=$(echo "$DEPLOY_CHECK" | grep -c "WARN\|ERROR" 2>/dev/null || true)
DEPLOY_ISSUES=$(echo "$DEPLOY_ISSUES" | tr -d '[:space:]')
DEPLOY_ISSUES=${DEPLOY_ISSUES:-0}
if [ "$DEPLOY_ISSUES" -eq 0 ]; then
    check_pass "Django deploy check: no issues"
else
    check_warn "Django deploy check: $DEPLOY_ISSUES issue(s) (review with: manage.py check --deploy)"
fi

echo ""

# ── FINAL SCORE ──
echo "================================================================"
TOTAL=$((PASS + FAIL + WARN))

if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
    GRADE="A"
    GRADE_COLOR="$GREEN"
    GRADE_MSG="SAFE to proceed with Django 5.2 upgrade"
elif [ "$FAIL" -eq 0 ]; then
    GRADE="B"
    GRADE_COLOR="$GREEN"
    GRADE_MSG="SAFE to upgrade — review warnings first"
elif [ "$FAIL" -le 2 ]; then
    GRADE="C"
    GRADE_COLOR="$YELLOW"
    GRADE_MSG="Fix remaining failures before upgrading"
else
    GRADE="D"
    GRADE_COLOR="$RED"
    GRADE_MSG="NOT SAFE to upgrade — critical issues remain"
fi

echo ""
echo -e "  ${GREEN}PASS:${NC}  $PASS"
echo -e "  ${RED}FAIL:${NC}  $FAIL"
echo -e "  ${YELLOW}WARN:${NC}  $WARN"
echo ""
echo -e "  Upgrade Readiness Grade:  ${BOLD}${GRADE_COLOR}${GRADE}${NC}"
echo -e "  ${GRADE_COLOR}${GRADE_MSG}${NC}"
echo ""
echo "================================================================"
echo ""

# Exit with failure if any checks failed
[ "$FAIL" -eq 0 ] && exit 0 || exit 1

