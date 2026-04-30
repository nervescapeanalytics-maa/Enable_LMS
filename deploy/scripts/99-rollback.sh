#!/usr/bin/env bash
# =============================================================================
# 99-rollback.sh — Emergency rollback to the source environment
#
# Use this if anything breaks during cutover. It:
#   1. Scales cloudflared in K8s to 0 (stops new public traffic)
#   2. Restarts the old tunnel on the source machine
#   3. Lifts maintenance mode on source
#
# The K8s stack is LEFT IN PLACE so you can troubleshoot after.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

NS=lms-prod

echo "==> Scaling down new cloudflared"
kubectl scale deployment/cloudflared -n "$NS" --replicas=0 || true

echo "==> Restarting source tunnel on ${SOURCE_HOST:-192.168.1.113}"
ssh "${SOURCE_HOST:-root@192.168.1.113}" "podman start docker_tunnel_1 || true"

echo "==> Lifting maintenance mode on source"
ssh "${SOURCE_HOST:-root@192.168.1.113}" "
    podman exec docker_api_1 python manage.py shell -c '
from django.core.cache import cache
cache.delete(\"maintenance_mode\")
print(\"Maintenance mode cleared.\")
' || true
"

echo ""
echo "=============================================================="
echo " Rollback complete."
echo ""
echo " Verify public URL now points to source:"
echo "   curl -sf https://lms.automatebot.shop/health/"
echo ""
echo " K8s stack is still up for troubleshooting."
echo " To tear it down completely:"
echo "   kubectl delete namespace $NS"
echo "=============================================================="
