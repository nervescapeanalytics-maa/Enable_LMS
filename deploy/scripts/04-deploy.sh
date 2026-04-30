#!/usr/bin/env bash
# =============================================================================
# 04-deploy.sh — Full deployment orchestrator
#
# Applies all manifests in order, waits for each rollout before proceeding.
# NetworkPolicy + cloudflared are applied LAST so you can verify internally
# first and cut over to public traffic on your own schedule.
#
# Usage:
#   source deploy/.env
#   bash 04-deploy.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$DEPLOY_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

: "${IMAGE_TAG:?Set IMAGE_TAG in deploy/.env (e.g. v1.0.0-20260422-120000)}"

NS=lms-prod
APPLY() {
    local f="$1"
    echo "==> Applying $f"
    envsubst < "$DEPLOY_DIR/$f" | kubectl apply -f -
}

WAIT() {
    local kind="$1" name="$2" timeout="${3:-300s}"
    echo "==> Waiting for $kind/$name (timeout=$timeout)..."
    kubectl rollout status "$kind/$name" -n "$NS" --timeout="$timeout"
}

# ── Step 1: Namespace + Secrets + Config ──────────────────────────────────
APPLY 00-namespace.yaml
bash "$SCRIPT_DIR/03-create-secrets.sh"
APPLY 10-configmap.yaml

# ── Step 2: Stateful dependencies (Redis + Media PVC) ─────────────────────
APPLY 20-redis.yaml
WAIT statefulset redis 180s
APPLY 30-media-pvc.yaml
echo "==> Waiting for media-pvc to bind..."
for i in {1..30}; do
    phase=$(kubectl get pvc media-pvc -n "$NS" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
    if [[ "$phase" == "Bound" ]]; then
        echo "   PVC Bound."
        break
    fi
    sleep 2
done

# ── Step 3: Run migrations ────────────────────────────────────────────────
kubectl delete job lms-migrate -n "$NS" --ignore-not-found=true
APPLY 40-migrate-job.yaml
echo "==> Waiting for migrations to complete..."
kubectl wait --for=condition=complete job/lms-migrate -n "$NS" --timeout=600s
kubectl logs job/lms-migrate -n "$NS" --tail=50

# ── Step 4: App workloads ─────────────────────────────────────────────────
APPLY 50-api.yaml
APPLY 51-websocket.yaml
APPLY 52-celery-worker.yaml
APPLY 53-celery-beat.yaml
APPLY 60-nginx.yaml

for d in api websocket celery-worker celery-beat nginx; do
    WAIT deployment "$d" 300s
done

# ── Step 5: Internal smoke test ───────────────────────────────────────────
echo "==> Running internal smoke test..."
kubectl run smoke-$$ --rm -i --image=curlimages/curl --restart=Never -n "$NS" -- \
    sh -c "curl -sf http://nginx/health/ && echo ' -- health OK' && \
           curl -sf -o /dev/null -w 'admin: %{http_code}\n' http://nginx/admin/"

# ── Step 6: Cloudflared (public traffic cutover) ──────────────────────────
read -rp "Internal smoke OK. Proceed with Cloudflared + NetworkPolicy? [y/N] " ans
if [[ "${ans,,}" != "y" ]]; then
    echo "Stopping before public cutover. Run manually when ready:"
    echo "  kubectl apply -f $DEPLOY_DIR/70-cloudflared.yaml"
    echo "  kubectl apply -f $DEPLOY_DIR/80-networkpolicy.yaml"
    exit 0
fi

APPLY 70-cloudflared.yaml
WAIT deployment cloudflared 180s

# ── Step 7: Lock down networking ──────────────────────────────────────────
APPLY 80-networkpolicy.yaml

echo ""
echo "=============================================================="
echo " Deploy complete."
echo ""
echo " Verify:"
echo "   curl -sf https://lms.automatebot.shop/health/"
echo "   kubectl get pods -n $NS"
echo "   kubectl get hpa -n $NS"
echo ""
echo " When ready, stop the OLD tunnel:"
echo "   ssh $SOURCE_HOST 'podman stop docker_tunnel_1'"
echo "=============================================================="
