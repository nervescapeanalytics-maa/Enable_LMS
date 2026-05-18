"""GET /admin/ai-metrics/  → Prometheus exposition format."""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse


@staff_member_required
def ai_metrics_view(request):
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore
    except Exception:
        return HttpResponse("prometheus_client not installed\n",
                            status=503, content_type="text/plain")
    data = generate_latest()
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
