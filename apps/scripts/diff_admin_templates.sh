#!/bin/bash
# ================================================================
#  Admin Template Diff Tool
#  Run this AFTER every Django upgrade to check template compatibility.
#
#  Usage:
#    ./scripts/diff_admin_templates.sh              # Show diffs
#    ./scripts/diff_admin_templates.sh --save       # Save baseline for current version
#    ./scripts/diff_admin_templates.sh --check      # Exit 1 if diffs found
# ================================================================

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PROJECT_DIR"

DJANGO_VERSION=$(python -c "import django; print(django.get_version())" 2>/dev/null)
DJANGO_PATH=$(python -c "import django; print(django.__path__[0])" 2>/dev/null)
DJANGO_ADMIN_TPL="$DJANGO_PATH/contrib/admin/templates/admin"
LOCAL_ADMIN_TPL="$PROJECT_DIR/templates/admin"
BASELINE_DIR="$PROJECT_DIR/docs/admin_template_baselines/django_${DJANGO_VERSION}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo "================================================================"
echo "  Admin Template Diff — Django $DJANGO_VERSION"
echo "================================================================"
echo ""

# Templates to check
TEMPLATES=(
    "base_site.html"
    "index.html"
    "change_list.html"
    "login.html"
)

DIFFS_FOUND=0

for tmpl in "${TEMPLATES[@]}"; do
    DJANGO_FILE="$DJANGO_ADMIN_TPL/$tmpl"
    LOCAL_FILE="$LOCAL_ADMIN_TPL/$tmpl"

    if [ ! -f "$LOCAL_FILE" ]; then
        continue
    fi

    if [ ! -f "$DJANGO_FILE" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $tmpl — no Django source (custom template)"
        continue
    fi

    echo -e "${BOLD}=== $tmpl ===${NC}"

    if diff -u "$DJANGO_FILE" "$LOCAL_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} Identical to Django source"
    else
        DIFFS_FOUND=$((DIFFS_FOUND + 1))
        echo -e "${YELLOW}[DIFF]${NC} Your override differs from Django $DJANGO_VERSION source:"
        diff -u "$DJANGO_FILE" "$LOCAL_FILE" --color=auto 2>/dev/null | head -40
        echo ""
        echo -e "${CYAN}  Full diff: diff -u $DJANGO_FILE $LOCAL_FILE${NC}"
    fi
    echo ""
done

# Check if Django source has changed since last baseline
if [ -d "$BASELINE_DIR" ]; then
    echo "--- Checking for Django source changes since baseline ---"
    for tmpl in "${TEMPLATES[@]}"; do
        BASELINE_FILE="$BASELINE_DIR/$tmpl"
        DJANGO_FILE="$DJANGO_ADMIN_TPL/$tmpl"

        if [ -f "$BASELINE_FILE" ] && [ -f "$DJANGO_FILE" ]; then
            if ! diff -q "$BASELINE_FILE" "$DJANGO_FILE" > /dev/null 2>&1; then
                echo -e "${RED}[CHANGED]${NC} Django source for $tmpl has changed since baseline!"
                echo -e "  ${YELLOW}You MUST review and update your override.${NC}"
                DIFFS_FOUND=$((DIFFS_FOUND + 1))
            fi
        fi
    done
else
    echo -e "${YELLOW}No baseline for Django $DJANGO_VERSION — run with --save to create one${NC}"
fi

echo ""
if [ "$DIFFS_FOUND" -gt 0 ]; then
    echo -e "${YELLOW}$DIFFS_FOUND template(s) need review${NC}"
else
    echo -e "${GREEN}All template overrides are compatible${NC}"
fi

# Handle --save flag
if [ "${1:-}" = "--save" ]; then
    mkdir -p "$BASELINE_DIR"
    for tmpl in "${TEMPLATES[@]}"; do
        [ -f "$DJANGO_ADMIN_TPL/$tmpl" ] && cp "$DJANGO_ADMIN_TPL/$tmpl" "$BASELINE_DIR/$tmpl"
    done
    echo -e "${GREEN}Saved baselines for Django $DJANGO_VERSION${NC}"
fi

# Handle --check flag (for CI)
if [ "${1:-}" = "--check" ] && [ "$DIFFS_FOUND" -gt 0 ]; then
    exit 1
fi
