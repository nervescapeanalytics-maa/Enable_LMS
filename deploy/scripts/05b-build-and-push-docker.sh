#!/usr/bin/env bash
# =============================================================================
# 05b-build-and-push-docker.sh
#
# Docker-based equivalent of 05-build-and-push.sh. Builds `api` + `nginx`
# images and pushes them to the AceCloud private registry.
#
# Required env (supply via deploy/.env or `export` before running):
#   REGISTRY_URL          e.g. registry.internal.acecloud.io/enable-lms
#   REGISTRY_ROBOT_USER   registry robot / service account name
#   REGISTRY_ROBOT_TOKEN  robot account password / CLI secret
#   IMAGE_TAG             optional — defaults to v1.0.0-<UTC stamp>
#
# Usage:
#   sudo -E bash deploy/scripts/05b-build-and-push-docker.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

: "${REGISTRY_URL:?Set REGISTRY_URL (e.g. registry.internal.acecloud.io/enable-lms)}"
: "${REGISTRY_ROBOT_USER:?Set REGISTRY_ROBOT_USER}"
: "${REGISTRY_ROBOT_TOKEN:?Set REGISTRY_ROBOT_TOKEN}"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY_HOST="${REGISTRY_URL%%/*}"
STAMP=$(date -u +%Y%m%d-%H%M%S)
TAG="${IMAGE_TAG:-v1.0.0-$STAMP}"

echo "==> Logging in to $REGISTRY_HOST as $REGISTRY_ROBOT_USER"
echo "$REGISTRY_ROBOT_TOKEN" | docker login "$REGISTRY_HOST" \
    --username "$REGISTRY_ROBOT_USER" --password-stdin

cd "$REPO_ROOT"

echo "==> Building api image ($TAG)"
docker build \
    -f docker/Dockerfile \
    --build-arg APP_VERSION="$STAMP" \
    -t "$REGISTRY_URL/api:$TAG" \
    -t "$REGISTRY_URL/api:latest" \
    .

echo "==> Building nginx image ($TAG)"
docker build \
    -f docker/Dockerfile.nginx \
    -t "$REGISTRY_URL/nginx:$TAG" \
    -t "$REGISTRY_URL/nginx:latest" \
    .

echo "==> Pushing api:$TAG"
docker push "$REGISTRY_URL/api:$TAG"
docker push "$REGISTRY_URL/api:latest"

echo "==> Pushing nginx:$TAG"
docker push "$REGISTRY_URL/nginx:$TAG"
docker push "$REGISTRY_URL/nginx:latest"

# Optional image integrity report
echo "==> Image digests"
docker inspect --format='{{.RepoDigests}}' "$REGISTRY_URL/api:$TAG"
docker inspect --format='{{.RepoDigests}}' "$REGISTRY_URL/nginx:$TAG"

cat <<EOF

==============================================================
 Images pushed with tag: $TAG
   $REGISTRY_URL/api:$TAG
   $REGISTRY_URL/nginx:$TAG

 Next:
   1. Update deploy/.env:   IMAGE_TAG=$TAG
   2. Deploy on cluster:    bash deploy/scripts/04-deploy.sh
   3. Or run with compose:  IMAGE_REGISTRY=$REGISTRY_URL/ IMAGE_TAG=$TAG \\
                              docker compose -f docker/docker-compose.yml pull && \\
                              docker compose -f docker/docker-compose.yml up -d
==============================================================
EOF
