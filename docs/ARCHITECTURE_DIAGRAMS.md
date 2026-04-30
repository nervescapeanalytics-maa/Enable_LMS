# LMS Enterprise — Architecture & Dataflow Diagrams

---

## 1. High-Level Architecture & Dataflow

Shows all components, their ports, and how data flows between them.

```mermaid
graph TB
    subgraph Internet
        U[/"👤 Users<br/>(Browser / Mobile)"\]
        CF["☁️ Cloudflare CDN<br/>+ WAF + DDoS Protection"]
        CFT["🔒 Cloudflare Tunnel<br/>(cloudflared)"]
    end

    subgraph Host["Rocky Linux 9.7 (192.168.1.113)"]
        subgraph Podman["Podman Container Stack"]
            NGX["🔀 Nginx 1.28<br/>Reverse Proxy<br/>:8080 → :80"]
            
            subgraph AppLayer["Application Layer"]
                API["🐍 Gunicorn<br/>Django 5.2 + DRF<br/>:8000<br/>(REST API)"]
                WS["⚡ Daphne<br/>Django Channels<br/>:8001<br/>(WebSocket)"]
            end
            
            subgraph WorkerLayer["Background Workers"]
                CW["⚙️ Celery Worker<br/>(Task Execution)"]
                CB["⏰ Celery Beat<br/>(Periodic Scheduler)"]
            end
            
            RD["🗄️ Redis 7<br/>:6379<br/>Cache / Broker / Channels"]
        end
        
        PG[("🐘 PostgreSQL 18.2<br/>LMS_PROD_DB<br/>:5432<br/>(113 tables)")]
    end

    U -->|"HTTPS"| CF
    CF -->|"Tunnel"| CFT
    CFT -->|"HTTP :8080"| NGX
    
    NGX -->|"/api/* /admin/*<br/>HTTP :8000"| API
    NGX -->|"/ws/*<br/>WebSocket :8001"| WS
    NGX -->|"/static/*<br/>Direct serve"| NGX
    
    API -->|"SQL Queries"| PG
    API -->|"Cache R/W<br/>db0"| RD
    API -->|"Task Dispatch"| RD
    
    WS -->|"Channel Layer<br/>db1"| RD
    WS -->|"SQL Queries"| PG
    
    CW -->|"Consume Tasks<br/>db0"| RD
    CW -->|"SQL Queries"| PG
    CB -->|"Schedule Tasks<br/>db3"| RD

    classDef internet fill:#e1f5fe,stroke:#0288d1,color:#01579b
    classDef container fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
    classDef app fill:#e8f5e9,stroke:#388e3c,color:#1b5e20
    classDef worker fill:#fff3e0,stroke:#f57c00,color:#e65100
    classDef data fill:#fce4ec,stroke:#c62828,color:#b71c1c

    class U,CF,CFT internet
    class NGX container
    class API,WS app
    class CW,CB worker
    class RD,PG data
```

### Component Details

| Container            | Image                    | Port | Purpose                                |
|----------------------|--------------------------|------|----------------------------------------|
| `enable-lms-nginx`   | `enable-lms-nginx:latest`| 8080 | Reverse proxy, static files, rate limiting |
| `enable-lms-api`     | `enable-lms:latest`      | 8000 | REST API (Gunicorn, 4 workers)         |
| `enable-lms-websocket`| `enable-lms:latest`     | 8001 | WebSocket server (Daphne, ASGI)        |
| `enable-lms-celery-worker`| `enable-lms:latest` | —    | Async task execution                   |
| `enable-lms-celery-beat`| `enable-lms:latest`    | —    | Periodic task scheduler                |
| `enable-lms-redis`   | `redis:7-alpine`         | 6379 | Cache (db0), Channels (db1), Celery (db3), Sessions (db4) |
| PostgreSQL           | Host-installed           | 5432 | Primary data store (113 tables)        |

---

## 2. Request Flow — Sequence Diagram

Shows the complete lifecycle of student login, dashboard load, WebSocket connection, and background task processing.

```mermaid
sequenceDiagram
    participant B as Browser
    participant CF as Cloudflare
    participant NGX as Nginx
    participant API as Gunicorn/Django
    participant RD as Redis
    participant PG as PostgreSQL
    participant CW as Celery Worker
    participant WS as Daphne/WebSocket

    Note over B,WS: === Student Login Flow ===
    B->>+CF: POST /api/v1/auth/login
    CF->>+NGX: HTTP via Tunnel
    NGX->>+API: proxy_pass :8000
    API->>+PG: SELECT * FROM auth_user
    PG-->>-API: User record
    API->>+RD: Cache session (db0)
    RD-->>-API: OK
    API-->>-NGX: JWT Token + 200
    NGX-->>-CF: Response
    CF-->>-B: JWT Token

    Note over B,WS: === Load Dashboard ===
    B->>+CF: GET /api/v1/student/dashboard
    CF->>+NGX: HTTP via Tunnel
    NGX->>+API: proxy_pass :8000
    API->>+RD: Check cache
    RD-->>API: Cache miss
    API->>+PG: Query classes, grades, schedule
    PG-->>-API: Result set
    API->>RD: Set cache (TTL=300s)
    RD-->>-API: OK
    API-->>-NGX: Dashboard JSON
    NGX-->>-CF: Response
    CF-->>-B: Dashboard data

    Note over B,WS: === Real-time Notifications ===
    B->>+NGX: WS Upgrade /ws/notifications/
    NGX->>+WS: Upgrade to WebSocket
    WS->>+RD: Subscribe channel_layer (db1)
    RD-->>-WS: Subscribed
    WS-->>-NGX: WS Connected
    NGX-->>-B: WS Connected

    Note over B,WS: === Background Task (Email) ===
    API->>+RD: celery.send_task('send_email')
    RD-->>-API: Task queued
    CW->>+RD: Consume task
    RD-->>-CW: Task payload
    CW->>CW: Send email via SMTP
    CW->>+PG: Log audit trail
    PG-->>-CW: OK
    CW->>+RD: Publish notification
    RD-->>-CW: OK
    RD-->>WS: Channel message
    WS-->>B: Push notification
```

---

## 3. Application Module & Data Store Map

Shows how Django apps connect to frontends and data stores.

```mermaid
graph LR
    subgraph Frontend["Frontend (Static)"]
        SD["Student Dashboard<br/>Vite + React"]
        TD["Teacher Dashboard<br/>Vite + React"]
        AD["Admin Panel<br/>Django Admin"]
    end

    subgraph DjangoApps["Django Apps (29 installed)"]
        AUTH["accounts<br/>Auth + JWT + MFA"]
        ACAD["academics<br/>Programs, Subjects<br/>Sections"]
        CLS["classes<br/>Live Classes<br/>YouTube/Zoom"]
        ASM["assessments<br/>Tests, Exams<br/>Grading"]
        ATT["attendance<br/>Student<br/>Attendance"]
        MAT["materials<br/>Study Materials<br/>File Upload"]
        COMM["communication<br/>Notifications<br/>Announcements"]
        SCHED["scheduling<br/>Time Tables<br/>Calendar"]
        SESS["sessions_tracking<br/>Login History<br/>Device Trust"]
        AUDIT["audit<br/>Change Logs<br/>Activity Trail"]
        ALERT["alerts<br/>System Alerts<br/>Thresholds"]
        RT["realtime<br/>WebSocket<br/>Consumers"]
        PROMO["promotions<br/>Student<br/>Promotions"]
        TENANT["tenants<br/>Multi-tenancy<br/>Isolation"]
        SYSCONF["system_config<br/>Feature Flags<br/>Settings"]
    end

    subgraph DataStores["Data Stores"]
        PG[("PostgreSQL 18.2<br/>113 Tables<br/>79 Migrations")]
        RD_CACHE["Redis db0<br/>API Cache"]
        RD_CHAN["Redis db1<br/>Channel Layer"]
        RD_CELERY["Redis db3<br/>Celery Broker"]
        RD_SESS["Redis db4<br/>Sessions"]
    end

    SD --> AUTH
    TD --> AUTH
    AD --> AUTH
    SD --> CLS & ASM & ATT & MAT
    TD --> CLS & ASM & ATT & SCHED

    AUTH --> PG
    ACAD --> PG
    CLS --> PG
    ASM --> PG
    ATT --> PG
    COMM --> PG
    AUDIT --> PG
    SESS --> PG
    TENANT --> PG

    AUTH --> RD_SESS
    CLS --> RD_CACHE
    RT --> RD_CHAN
    COMM --> RD_CELERY
    ALERT --> RD_CELERY

    classDef frontend fill:#e3f2fd,stroke:#1565c0
    classDef app fill:#f1f8e9,stroke:#558b2f
    classDef data fill:#fce4ec,stroke:#c62828

    class SD,TD,AD frontend
    class AUTH,ACAD,CLS,ASM,ATT,MAT,COMM,SCHED,SESS,AUDIT,ALERT,RT,PROMO,TENANT,SYSCONF app
    class PG,RD_CACHE,RD_CHAN,RD_CELERY,RD_SESS data
```

### Redis Database Allocation

| DB  | Purpose           | Used By                     | TTL     |
|-----|-------------------|-----------------------------|---------|
| db0 | API Cache + Celery Broker | API, Celery Worker/Beat | 300s    |
| db1 | Channel Layer     | Daphne (WebSocket)          | Session |
| db3 | Celery Beat Schedule | Celery Beat               | —       |
| db4 | Django Sessions   | API (DRF)                   | 1 week  |

---

## 4. Network Topology

```mermaid
graph TB
    subgraph PublicNet["Public Internet"]
        DNS["DNS: lms.automatebot.shop<br/>→ Cloudflare Proxy"]
    end

    subgraph CloudflareEdge["Cloudflare Edge"]
        WAF["WAF + DDoS<br/>SSL Termination"]
        TUN["Tunnel Endpoint<br/>→ cloudflared daemon"]
    end

    subgraph HostNet["Host Network (192.168.1.113)"]
        CFD["cloudflared<br/>→ localhost:8080"]
        PG2[("PostgreSQL<br/>0.0.0.0:5432")]
    end

    subgraph PodmanNet["Podman Network (10.89.0.0/24)"]
        N["nginx<br/>10.89.0.x:80<br/>Published: 8080"]
        A["api<br/>10.89.0.x:8000"]
        W["websocket<br/>10.89.0.x:8001"]
        R["redis<br/>10.89.0.x:6379"]
        CW2["celery-worker"]
        CB2["celery-beat"]
    end

    DNS --> WAF --> TUN --> CFD --> N
    N --> A
    N --> W
    A --> R
    W --> R
    CW2 --> R
    CB2 --> R
    A -->|"host.containers.internal<br/>:5432"| PG2
    W -->|"host.containers.internal<br/>:5432"| PG2
    CW2 -->|"host.containers.internal<br/>:5432"| PG2

    classDef pub fill:#ffebee,stroke:#c62828
    classDef cf fill:#e3f2fd,stroke:#1565c0
    classDef host fill:#f1f8e9,stroke:#2e7d32
    classDef pod fill:#fff3e0,stroke:#e65100

    class DNS pub
    class WAF,TUN cf
    class CFD,PG2 host
    class N,A,W,R,CW2,CB2 pod
```

---

## 5. Deployment Pipeline

```mermaid
graph LR
    A["1. Code Change<br/>git push"] --> B["2. Build Image<br/>podman build<br/>--build-arg APP_VERSION"]
    B --> C["3. Stop Containers<br/>podman stop/rm"]
    C --> D["4. Start Stack<br/>podman-compose up -d"]
    D --> E["5. Health Check<br/>curl /health/"]
    E --> F{"Healthy?"}
    F -->|Yes| G["6. ✅ Deploy Complete"]
    F -->|No| H["7. Rollback<br/>podman tag prev:latest<br/>podman-compose up -d"]
    H --> E

    style A fill:#e3f2fd,stroke:#1565c0
    style B fill:#fff3e0,stroke:#e65100
    style C fill:#fce4ec,stroke:#c62828
    style D fill:#e8f5e9,stroke:#2e7d32
    style G fill:#c8e6c9,stroke:#1b5e20
    style H fill:#ffcdd2,stroke:#b71c1c
```
