#!/usr/bin/env python3
"""
Lightweight health check for Docker HEALTHCHECK directive.
Exits 0 if the service is healthy, 1 otherwise.
"""
import os
import sys
import urllib.request

port = os.environ.get("GUNICORN_PORT", "8000")
url = f"http://127.0.0.1:{port}/health/"

try:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        if resp.status == 200 or resp.status == 401:
            sys.exit(0)
        sys.exit(1)
except Exception:
    sys.exit(1)
