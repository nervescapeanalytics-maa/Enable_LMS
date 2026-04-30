# Enable-LMS — AceCloud Container Service Deployment

Kubernetes-compatible manifests for deploying Enable-LMS to AceCloud Container Service.

## Prerequisites

1. PostgreSQL VM provisioned on `45.194.90.251` (see `scripts/01-setup-postgres-vm.sh`)
2. Images pushed to `registry.internal.acecloud.io/enable-lms/{api,nginx}`
3. `kubectl` configured against the AceCloud cluster
4. DB restored from source dump (see `scripts/02-restore-db.sh`)

## File layout

| File | Purpose |
|------|---------|
| `00-namespace.yaml`        | Creates `lms-prod` namespace |
| `10-configmap.yaml`        | Non-secret env vars (DB host, Django settings) |
| `20-redis.yaml`            | Redis StatefulSet + Service |
| `30-media-pvc.yaml`        | Shared media storage PVC (RWX) |
| `40-migrate-job.yaml`      | One-shot Django migration Job |
| `50-api.yaml`              | Gunicorn Deployment + Service + HPA + PDB |
| `51-websocket.yaml`        | Daphne ASGI Deployment + Service + HPA |
| `52-celery-worker.yaml`    | Celery worker Deployment + HPA |
| `53-celery-beat.yaml`      | Celery beat Deployment (1 replica, no HPA) |
| `60-nginx.yaml`            | Reverse proxy Deployment + Service |
| `70-cloudflared.yaml`      | Cloudflare Tunnel connector (HA, 2 replicas) |
| `80-networkpolicy.yaml`    | Default-deny + explicit allow rules |

## One-time setup (secrets are NOT in Git)

Run `scripts/03-create-secrets.sh` after filling in the env values — it creates:
- `acecloud-registry` — imagePullSecret for private registry
- `lms-secrets` — DJANGO_SECRET_KEY, DB_PASSWORD, CLOUDFLARE_TUNNEL_TOKEN

## Deploy

```bash
# Set image tag you pushed in Phase 2
export IMAGE_TAG=v1.0.0-YYYYMMDD-HHMMSS

# Run the full deploy sequence
bash scripts/04-deploy.sh
```

## Rollback

```bash
bash scripts/99-rollback.sh
```
