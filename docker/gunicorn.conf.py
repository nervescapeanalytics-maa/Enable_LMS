# =============================================================================
# Enable-LMS Enterprise — Gunicorn Configuration (Docker)
# Tuned for container environments and high throughput.
# All values driven by environment variables for K8s HPA flexibility.
# =============================================================================
import multiprocessing
import os

# ── Bind ─────────────────────────────────────────────────────────────────────
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
backlog = int(os.environ.get("GUNICORN_BACKLOG", 2048))

# ── Workers ──────────────────────────────────────────────────────────────────
workers = int(os.environ.get(
    "GUNICORN_WORKERS",
    multiprocessing.cpu_count() * 2 + 1
))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", 1000))

# ── Recycling (memory-leak protection) ───────────────────────────────────────
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 5000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 500))

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))

# ── Logging (stdout for Docker log driver collection) ────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ── Process ──────────────────────────────────────────────────────────────────
proc_name = "enable_lms"
preload_app = True
daemon = False
tmp_upload_dir = None

# ── Hooks ────────────────────────────────────────────────────────────────────
def on_starting(server):
    server.log.info("Enable-LMS Gunicorn starting")

def when_ready(server):
    server.log.info("Server ready. Spawning workers")

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
