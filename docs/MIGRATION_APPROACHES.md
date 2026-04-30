# LMS Enterprise — Migration Approaches

> Three production-grade strategies for migrating the LMS application from host-based systemd deployment to containerized infrastructure.

---

## Current State (Before)

| Component       | Detail                                    |
|-----------------|-------------------------------------------|
| **Application** | Django 5.2 LTS + DRF 3.16.1              |
| **Runtime**     | Python 3.13, Gunicorn + Daphne            |
| **Database**    | PostgreSQL 18.2 (standalone, 23 MB)       |
| **Cache/Broker**| Redis 7                                   |
| **Proxy**       | Nginx 1.28                                |
| **Workers**     | Celery Worker + Celery Beat               |
| **OS**          | Rocky Linux 9.7                           |
| **Deployment**  | systemd units, manual `manage.py` deploys |
| **Tunnel**      | Cloudflare Tunnel (token-based)           |

---

## Approach 1 — Podman Compose (Single-Host, Current Implementation)

### Overview
Run all application services as rootless Podman containers on the same host, orchestrated by `podman-compose`. The database remains standalone on the host. This is the approach already implemented in `/u01/app/Enable-LMS/`.

### Architecture

```
  Internet
    │
    ▼
  Cloudflare Tunnel ──► localhost:8080
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Podman Pod (enable-lms)                        │
│                                                 │
│  ┌─────────┐   ┌──────────┐   ┌──────────────┐ │
│  │  Nginx   │──▶│ Gunicorn │   │   Daphne     │ │
│  │  :8080   │   │  :8000   │   │   :8001      │ │
│  └─────────┘   └──────────┘   └──────────────┘ │
│                                                 │
│  ┌──────────┐  ┌─────────────┐  ┌───────────┐  │
│  │  Redis   │  │ Celery      │  │ Celery    │  │
│  │  :6379   │  │ Worker      │  │ Beat      │  │
│  └──────────┘  └─────────────┘  └───────────┘  │
└─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ PostgreSQL 18.2  │  ← Host-level (192.168.1.113:5432)
│ /d01/postgres/   │
└──────────────────┘
```

### Step-by-Step Migration

#### Phase 1 — Prepare (30 min)
1. **Create project directory**
   ```bash
   mkdir -p /u01/app/Enable-LMS/{docker/nginx,apps,logs}
   ```
2. **Copy application code**
   ```bash
   rsync -a --exclude='venv*' --exclude='__pycache__' \
     /u01/app/LMS-Portal/apps/ /u01/app/Enable-LMS/apps/
   ```
3. **Create environment file** (`docker/.env`)
   ```env
   DJANGO_ENV=production
   SECRET_KEY=<generate-new-key>
   DB_HOST=192.168.1.113
   DB_PORT=5432
   DB_NAME=LMS_PROD_DB
   DB_USER=lms_app_user
   DB_PASSWORD=<password>
   REDIS_URL=redis://redis:6379/0
   ALLOWED_HOSTS=lms.automatebot.shop,localhost
   HTTP_PORT=8080
   ```

#### Phase 2 — Build Docker Assets (1 hour)
4. **Create Dockerfile** — Multi-stage build:
   - Builder stage: install Python deps from `requirements.lock`
   - Runtime stage: slim base + app code + entrypoint
5. **Create `entrypoint.sh`** — Handles: wait for DB/Redis → migrate → collectstatic → start service (gunicorn/daphne/celery)
6. **Create `docker-compose.yml`** — 6 services: redis, api, websocket, celery-worker, celery-beat, nginx
7. **Create Nginx config** — Reverse proxy with rate limiting, security headers, WebSocket upgrade support
8. **Create Nginx Dockerfile** — Alpine-based, custom config

#### Phase 3 — Database Preparation (15 min)
9. **Backup database**
   ```bash
   pg_dump -U pgadmin -Fc LMS_PROD_DB > /backup/lms_pre_migration.dump
   ```
10. **Update `pg_hba.conf`** — Allow container subnet (10.88.0.0/16, 10.89.0.0/16)
    ```
    host    LMS_PROD_DB    lms_app_user    10.0.0.0/8    scram-sha-256
    ```
11. **Reload PostgreSQL**
    ```bash
    sudo -u pgadmin /d01/postgres/18/bin/pg_ctl reload -D /d01/postgres/18/data
    ```

#### Phase 4 — Deploy (20 min)
12. **Stop old services**
    ```bash
    sudo systemctl stop gunicorn daphne celery-worker celery-beat
    sudo systemctl disable gunicorn daphne celery-worker celery-beat
    ```
13. **Build images**
    ```bash
    cd /u01/app/Enable-LMS
    podman-compose -f docker/docker-compose.yml build
    ```
14. **Start stack**
    ```bash
    podman-compose -f docker/docker-compose.yml up -d
    ```
15. **Verify**
    ```bash
    curl -s http://localhost:8080/health/
    # {"status":"healthy","django_version":"5.2","database":"connected"}
    ```

#### Phase 5 — Cutover (10 min)
16. **Update Cloudflare Tunnel** — Change origin from `localhost:8000` to `localhost:8080`
17. **Smoke test** production URL
18. **Monitor** logs: `podman logs -f enable-lms-api`

### Pros
- **Simplest** — single host, no orchestrator learning curve
- **No infrastructure changes** — runs on existing server
- **Fastest deployment** — under 2 hours
- **Database stays external** — no data migration needed
- **Rootless containers** — security benefit over systemd

### Cons
- **Single point of failure** — one host runs everything
- **Manual scaling** — must adjust `docker-compose.yml` replica counts
- **No auto-recovery across hosts** — if server dies, manual intervention
- **No rolling updates** — brief downtime during container restart

### Best For
- Small to medium deployments (< 500 concurrent users)
- Teams without Kubernetes experience
- Budget-constrained environments

---

## Approach 2 — Container Registry + Kubernetes / K3s

### Overview
Push container images to a registry (Docker Hub, GitHub Container Registry, or private Harbor). Deploy to a lightweight Kubernetes cluster (K3s) with built-in ingress, auto-scaling, and self-healing.

### Architecture

```
  Internet
    │
    ▼
  Cloudflare ──► K3s Ingress Controller (:443)
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
   ┌─────────┐ ┌─────────┐   ┌──────────┐
   │ API Pod  │ │ API Pod │   │ WS Pod   │
   │ (replica)│ │ (replica)│   │ (Daphne) │
   └─────────┘ └─────────┘   └──────────┘
        │           │               │
        ▼           ▼               ▼
   ┌──────────────────────────────────────┐
   │           Cluster Services           │
   │  Redis (StatefulSet)                 │
   │  Celery Worker (Deployment, 2 pods)  │
   │  Celery Beat (Deployment, 1 pod)     │
   └──────────────────────────────────────┘
                    │
                    ▼
           ┌──────────────────┐
           │ PostgreSQL 18.2  │  ← External DB
           │ (ExternalName    │
           │  Service)        │
           └──────────────────┘
```

### Step-by-Step Migration

#### Phase 1 — Container Registry Setup (30 min)
1. **Create registry account** (GitHub Container Registry recommended)
   ```bash
   podman login ghcr.io -u <github-user>
   ```
2. **Tag and push images**
   ```bash
   podman tag localhost/enable-lms:latest ghcr.io/<org>/lms-api:v1.0.0
   podman tag localhost/enable-lms-nginx:latest ghcr.io/<org>/lms-nginx:v1.0.0
   podman push ghcr.io/<org>/lms-api:v1.0.0
   podman push ghcr.io/<org>/lms-nginx:v1.0.0
   ```

#### Phase 2 — K3s Cluster Setup (1 hour)
3. **Install K3s** (single-node to start)
   ```bash
   curl -sfL https://get.k3s.io | sh -
   ```
4. **Create namespace**
   ```bash
   kubectl create namespace lms
   ```
5. **Create secrets**
   ```bash
   kubectl create secret generic lms-env -n lms \
     --from-env-file=docker/.env
   kubectl create secret docker-registry regcred -n lms \
     --docker-server=ghcr.io \
     --docker-username=<user> \
     --docker-password=<token>
   ```

#### Phase 3 — Kubernetes Manifests (2 hours)
6. **Create Kubernetes manifests** in `k8s/` directory:

   **`k8s/api-deployment.yaml`**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: lms-api
     namespace: lms
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: lms-api
     template:
       metadata:
         labels:
           app: lms-api
       spec:
         containers:
         - name: api
           image: ghcr.io/<org>/lms-api:v1.0.0
           ports:
           - containerPort: 8000
           envFrom:
           - secretRef:
               name: lms-env
           readinessProbe:
             httpGet:
               path: /health/
               port: 8000
             initialDelaySeconds: 10
             periodSeconds: 5
           livenessProbe:
             httpGet:
               path: /health/
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           resources:
             requests:
               memory: "256Mi"
               cpu: "250m"
             limits:
               memory: "512Mi"
               cpu: "500m"
   ```

   **`k8s/api-service.yaml`**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: lms-api
     namespace: lms
   spec:
     selector:
       app: lms-api
     ports:
     - port: 8000
       targetPort: 8000
   ```

   **`k8s/ingress.yaml`**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: lms-ingress
     namespace: lms
     annotations:
       traefik.ingress.kubernetes.io/router.tls: "true"
   spec:
     rules:
     - host: lms.automatebot.shop
       http:
         paths:
         - path: /ws/
           pathType: Prefix
           backend:
             service:
               name: lms-websocket
               port:
                 number: 8001
         - path: /
           pathType: Prefix
           backend:
             service:
               name: lms-api
               port:
                 number: 8000
   ```

   **`k8s/hpa.yaml`** (Horizontal Pod Autoscaler)
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: lms-api-hpa
     namespace: lms
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: lms-api
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

   Similar manifests for: `websocket-deployment.yaml`, `redis-statefulset.yaml`, `celery-worker-deployment.yaml`, `celery-beat-deployment.yaml`

7. **External database service**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: postgres-external
     namespace: lms
   spec:
     type: ExternalName
     externalName: 192.168.1.113
   ```

#### Phase 4 — Deploy (30 min)
8. **Apply manifests**
   ```bash
   kubectl apply -f k8s/ -n lms
   ```
9. **Verify pods**
   ```bash
   kubectl get pods -n lms -w
   ```
10. **Run migrations** (one-time Job)
    ```bash
    kubectl create job lms-migrate --from=cronjob/lms-migrate -n lms
    ```

#### Phase 5 — CI/CD Pipeline (1 hour)
11. **GitHub Actions workflow** (`.github/workflows/deploy.yml`)
    ```yaml
    on:
      push:
        branches: [main]
    jobs:
      build-deploy:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - name: Build & push
          run: |
            docker build -f docker/Dockerfile -t ghcr.io/<org>/lms-api:${{ github.sha }} .
            docker push ghcr.io/<org>/lms-api:${{ github.sha }}
        - name: Deploy to K3s
          run: |
            kubectl set image deployment/lms-api api=ghcr.io/<org>/lms-api:${{ github.sha }} -n lms
    ```

### Pros
- **Auto-scaling** — HPA scales API pods based on CPU/memory
- **Self-healing** — Kubernetes restarts failed pods automatically
- **Rolling updates** — zero-downtime deployments
- **Built-in ingress** — Traefik included with K3s
- **CI/CD ready** — push to main → automatic deploy
- **Multi-node** — add worker nodes with one command

### Cons
- **Learning curve** — requires Kubernetes knowledge
- **More infrastructure** — K3s needs 512MB+ RAM overhead
- **Complexity** — YAML manifests, secrets management, RBAC
- **Monitoring** — needs Prometheus/Grafana stack for visibility
- **Overkill** for small deployments

### Best For
- Growing applications (500 – 10,000 concurrent users)
- Teams with some DevOps/Kubernetes experience
- Environments needing auto-scaling and HA

### Estimated Effort
- Initial setup: 1–2 days
- CI/CD pipeline: 0.5 day
- Monitoring stack: 0.5 day

---

## Approach 3 — Infrastructure-as-Code with Ansible + Podman Quadlet

### Overview
Use Ansible playbooks to automate the entire deployment lifecycle. Leverage Podman Quadlet (systemd-native container management) instead of `podman-compose` for production-grade service management with auto-restart, journal logging, and standard systemd tooling.

### Architecture

```
  Ops Workstation
    │
    │ ansible-playbook deploy.yml
    ▼
┌─────────────────────────────────────────────────┐
│  Target Server (Rocky Linux 9.7)                │
│                                                 │
│  systemd (manages Quadlet containers)           │
│  ┌─────────────────────────────────────────┐    │
│  │ lms-nginx.container    → nginx:8080     │    │
│  │ lms-api.container      → gunicorn:8000  │    │
│  │ lms-ws.container       → daphne:8001    │    │
│  │ lms-worker.container   → celery worker  │    │
│  │ lms-beat.container     → celery beat    │    │
│  │ lms-redis.container    → redis:6379     │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  Podman Network: lms-net                        │
└─────────────────────────────────────────────────┘
         │
         ▼
  PostgreSQL 18.2 (192.168.1.113:5432)
```

### Step-by-Step Migration

#### Phase 1 — Ansible Project Structure (1 hour)
1. **Create Ansible project**
   ```
   ansible-lms/
   ├── inventory/
   │   ├── production.yml
   │   └── staging.yml
   ├── roles/
   │   ├── common/          # OS packages, firewall, SELinux
   │   ├── podman/           # Install Podman, configure registries
   │   ├── postgres/         # pg_hba.conf, backup scripts
   │   ├── lms-build/        # Build container images
   │   └── lms-deploy/       # Quadlet files, start services
   ├── group_vars/
   │   └── all.yml           # Shared variables
   ├── deploy.yml            # Main playbook
   └── rollback.yml          # Rollback playbook
   ```

2. **Inventory** (`inventory/production.yml`)
   ```yaml
   all:
     hosts:
       lms-prod:
         ansible_host: 192.168.1.113
         ansible_user: root
     vars:
       app_version: "v1.0.0"
       db_host: "192.168.1.113"
       db_name: "LMS_PROD_DB"
       domain: "lms.automatebot.shop"
   ```

#### Phase 2 — Quadlet Container Files (1 hour)
3. **Create Quadlet unit files** (systemd-native container definitions)

   **`/etc/containers/systemd/lms-api.container`**
   ```ini
   [Unit]
   Description=LMS API (Gunicorn)
   After=lms-redis.service
   Requires=lms-redis.service

   [Container]
   Image=localhost/enable-lms:latest
   ContainerName=lms-api
   Network=lms-net
   EnvironmentFile=/etc/lms/env
   PublishPort=
   Exec=gunicorn
   HealthCmd=python /app/healthcheck.py
   HealthInterval=30s
   HealthRetries=3
   AutoUpdate=registry

   [Service]
   Restart=always
   RestartSec=5
   TimeoutStartSec=120

   [Install]
   WantedBy=multi-user.target default.target
   ```

   **`/etc/containers/systemd/lms-nginx.container`**
   ```ini
   [Unit]
   Description=LMS Nginx Reverse Proxy
   After=lms-api.service lms-ws.service

   [Container]
   Image=localhost/enable-lms-nginx:latest
   ContainerName=lms-nginx
   Network=lms-net
   PublishPort=8080:80
   Volume=/u01/app/Enable-LMS/apps/staticfiles:/app/staticfiles:ro,z

   [Service]
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target default.target
   ```

   Similar files for: `lms-ws.container`, `lms-worker.container`, `lms-beat.container`, `lms-redis.container`

4. **Create Podman network**
   ```ini
   # /etc/containers/systemd/lms-net.network
   [Network]
   Subnet=10.90.0.0/24
   Gateway=10.90.0.1
   ```

#### Phase 3 — Ansible Roles (2 hours)
5. **Deploy role** (`roles/lms-deploy/tasks/main.yml`)
   ```yaml
   - name: Create env file
     ansible.builtin.template:
       src: env.j2
       dest: /etc/lms/env
       mode: '0600'

   - name: Copy Quadlet files
     ansible.builtin.copy:
       src: "{{ item }}"
       dest: /etc/containers/systemd/
       mode: '0644'
     loop: "{{ lookup('fileglob', 'files/*.container', wantlist=True) }}"
     notify: Reload systemd

   - name: Build LMS image
     containers.podman.podman_image:
       name: enable-lms
       tag: "{{ app_version }}"
       path: /u01/app/Enable-LMS
       build:
         file: docker/Dockerfile

   - name: Run migrations
     containers.podman.podman_container:
       name: lms-migrate
       image: "enable-lms:{{ app_version }}"
       command: python manage.py migrate --noinput
       env_file: /etc/lms/env
       network: lms-net
       state: started
       detach: false
       rm: true

   - name: Start services
     ansible.builtin.systemd:
       name: "{{ item }}"
       state: started
       enabled: true
       daemon_reload: true
     loop:
       - lms-redis
       - lms-api
       - lms-ws
       - lms-worker
       - lms-beat
       - lms-nginx
   ```

6. **Rollback role** (`roles/lms-rollback/tasks/main.yml`)
   ```yaml
   - name: Revert to previous image
     containers.podman.podman_image:
       name: enable-lms
       tag: "{{ rollback_version }}"

   - name: Restart all services
     ansible.builtin.systemd:
       name: "{{ item }}"
       state: restarted
     loop:
       - lms-api
       - lms-ws
       - lms-worker
       - lms-beat
       - lms-nginx
   ```

7. **Backup role** (`roles/postgres/tasks/backup.yml`)
   ```yaml
   - name: Create database backup
     ansible.builtin.shell: |
       pg_dump -U pgadmin -Fc LMS_PROD_DB \
         > /backup/lms_{{ ansible_date_time.date }}.dump
     become_user: pgadmin

   - name: Prune old backups (keep 7 days)
     ansible.builtin.find:
       paths: /backup
       patterns: "lms_*.dump"
       age: 7d
     register: old_backups

   - name: Remove old backups
     ansible.builtin.file:
       path: "{{ item.path }}"
       state: absent
     loop: "{{ old_backups.files }}"
   ```

#### Phase 4 — Deploy (15 min)
8. **Run playbook**
   ```bash
   ansible-playbook -i inventory/production.yml deploy.yml
   ```
9. **Verify**
   ```bash
   ansible lms-prod -m shell -a 'systemctl status lms-api lms-nginx'
   ansible lms-prod -m uri -a 'url=http://localhost:8080/health/ return_content=yes'
   ```

#### Phase 5 — Ongoing Operations
10. **Update deployment** — Change `app_version` in group_vars, re-run playbook
11. **Rollback** — `ansible-playbook rollback.yml -e rollback_version=v0.9.0`
12. **Scale** — Add hosts to inventory, re-run playbook
13. **Monitor** — `journalctl -u lms-api -f` (native systemd logging)

### Pros
- **Infrastructure-as-Code** — entire stack defined in version-controlled playbooks
- **Idempotent** — re-run safely without side effects
- **Native systemd** — `systemctl start/stop/restart lms-api`, journal logging, auto-restart
- **Multi-host** — add servers to inventory for horizontal scaling
- **Rollback** — one-command rollback to any previous version
- **No orchestrator overhead** — lighter than Kubernetes
- **Audit trail** — Ansible logs every change

### Cons
- **Ansible expertise required** — playbook development and testing
- **No auto-scaling** — manual scaling via inventory changes
- **No self-healing across hosts** — systemd only restarts on same host
- **Initial setup time** — more upfront work than Approach 1
- **Network complexity** — must manage Podman networks manually

### Best For
- Ops teams familiar with Ansible and systemd
- Environments with strict change-management requirements
- Multi-server deployments without Kubernetes
- Organizations that need audit trails and IaC compliance

### Estimated Effort
- Ansible playbooks: 1–2 days
- Quadlet files: 0.5 day
- Testing on staging: 0.5 day
- Production cutover: 1 hour

---

## Comparison Matrix

| Criteria               | Approach 1: Podman Compose | Approach 2: K3s/Kubernetes | Approach 3: Ansible + Quadlet |
|------------------------|:--------------------------:|:--------------------------:|:-----------------------------:|
| **Setup Complexity**   | Low                        | High                       | Medium                        |
| **Learning Curve**     | Minimal                    | Steep                      | Moderate                      |
| **Auto-Scaling**       | No                         | Yes (HPA)                  | No                            |
| **Self-Healing**       | Container restart only     | Full (reschedule pods)     | Container restart only        |
| **Rolling Updates**    | No (brief downtime)        | Yes (zero-downtime)        | Yes (sequential restart)      |
| **Multi-Host**         | No                         | Yes                        | Yes (via inventory)           |
| **CI/CD Integration**  | Basic (scripts)            | Native (kubectl)           | Native (ansible-playbook)     |
| **Monitoring**         | `podman logs`              | Prometheus/Grafana         | `journalctl`                  |
| **Rollback**           | Manual image swap          | `kubectl rollout undo`     | Playbook with version flag    |
| **Infrastructure Cost**| Lowest                     | Medium (K3s overhead)      | Low                           |
| **Production Readiness**| Good                      | Excellent                  | Very Good                     |
| **Best Concurrent Users**| < 500                   | 500 – 10,000+             | 500 – 5,000                   |

---

## Recommendation

For the current LMS deployment:

1. **Start with Approach 1** (already implemented) — it's running, tested, and stable
2. **Plan for Approach 3** as the next step — adds IaC, rollback, and multi-host capability without Kubernetes complexity
3. **Graduate to Approach 2** when auto-scaling becomes a requirement (sustained > 500 concurrent users)

The migration path is progressive: each approach builds on the Docker images created in Approach 1, so no rework is needed when upgrading.
