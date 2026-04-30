#!/usr/bin/env bash
# =============================================================================
# 05-build-and-push.sh
#
# Builds both container images and pushes to the AceCloud private registry.
# MUST be run from inside the VPC (e.g. a temporary build VM) because the
# registry has no public endpoint.
#
# Usage (on the build VM):
#   source deploy/.env
#   bash 05-build-and-push.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

: "${REGISTRY_URL:?}"; : "${REGISTRY_ROBOT_USER:?}"; : "${REGISTRY_ROBOT_TOKEN:?}"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY_HOST="${REGISTRY_URL%%/*}"
STAMP=$(date +%Y%m%d-%H%M%S)
TAG="${IMAGE_TAG:-v1.0.0-$STAMP}"

echo "==> Logging in to private registry ($REGISTRY_HOST)"
echo "$REGISTRY_ROBOT_TOKEN" | podman login "$REGISTRY_HOST" \
    --username "$REGISTRY_ROBOT_USER" --password-stdin

cd "$REPO_ROOT"

echo "==> Building api image ($TAG)"
podman build \
    -f docker/Dockerfile \
    --build-arg APP_VERSION="$STAMP" \
    -t "$REGISTRY_URL/api:$TAG" \
    -t "$REGISTRY_URL/api:latest" \
    .

echo "==> Building nginx image ($TAG)"
podman build \
    -f docker/Dockerfile.nginx \
    -t "$REGISTRY_URL/nginx:$TAG" \
    -t "$REGISTRY_URL/nginx:latest" \
    .

echo "==> Pushing images"
podman push "$REGISTRY_URL/api:$TAG"
podman push "$REGISTRY_URL/api:latest"
podman push "$REGISTRY_URL/nginx:$TAG"
podman push "$REGISTRY_URL/nginx:latest"

echo ""
echo "=============================================================="
echo " Images pushed with tag: $TAG"
echo ""
echo " Update deploy/.env:"
echo "   IMAGE_TAG=$TAG"
echo ""
echo " Then deploy:"
echo "   bash deploy/scripts/04-deploy.sh"
echo "=============================================================="
