#!/usr/bin/env bash
# =============================================================================
# 03-create-secrets.sh
#
# Creates the two Kubernetes Secrets in the lms-prod namespace.
# Run this ONCE before deploying. Re-run to rotate credentials.
#
# Usage:
#   source deploy/.env
#   bash 03-create-secrets.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

: "${REGISTRY_URL:?}"; : "${REGISTRY_ROBOT_USER:?}"; : "${REGISTRY_ROBOT_TOKEN:?}"
: "${DJANGO_SECRET_KEY:?}"; : "${DB_PASSWORD:?}"; : "${CLOUDFLARE_TUNNEL_TOKEN:?}"

NS=lms-prod

echo "==> Ensuring namespace exists"
kubectl apply -f "$SCRIPT_DIR/../00-namespace.yaml"

echo "==> Creating/updating registry pull secret"
kubectl create secret docker-registry acecloud-registry \
    --namespace "$NS" \
    --docker-server="${REGISTRY_URL%%/*}" \
    --docker-username="$REGISTRY_ROBOT_USER" \
    --docker-password="$REGISTRY_ROBOT_TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "==> Creating/updating application secret"
kubectl create secret generic lms-secrets \
    --namespace "$NS" \
    --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
    --from-literal=DB_PASSWORD="$DB_PASSWORD" \
    --from-literal=CLOUDFLARE_TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "Secrets ready in namespace $NS:"
kubectl get secrets -n "$NS"
