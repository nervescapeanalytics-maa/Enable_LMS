"""Custom AI Governance & Operations admin pages.

These three views power the management UI for AI:

  * `/admin/ai_core/ai-dashboard/`   — operational overview (today's KPIs)
  * `/admin/ai_core/ai-cost-report/` — 30-day cost & token roll-up
  * `/admin/ai_core/ai-health/`      — provider circuit / latency / health grid

Permissions: any staff user with `is_staff=True` AND either superuser OR
`StaffRole.can_manage_ai` (or `can_view_audit` for the cost report).

Registered with the default `admin.site` via `get_urls` monkey-patch from
`apps/core/enf_admin_site.py`.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator

from .models import (
    AIAuditLog,
    AICostTracking,
    AIFeature,
    AIModel,
    AIProvider,
    AIUsageLog,
)


def _can_manage_ai(user) -> bool:
    if not user or not user.is_authenticated or not user.is_staff:
        return False
    if user.is_superuser:
        return True
    sr = getattr(user, "staff_role", None)
    return bool(sr and (getattr(sr, "can_manage_ai", False) or getattr(sr, "can_view_audit", False)))


def _tenant_filter(qs, request):
    tid = request.session.get("admin_tenant_id")
    if tid and hasattr(qs.model, "tenant"):
        return qs.filter(tenant_id=tid)
    return qs


def _common_context(request, *, title: str, subtitle: str = "") -> dict:
    return {
        **admin.site.each_context(request),
        "title": title,
        "subtitle": subtitle,
        "has_permission": _can_manage_ai(request.user),
        "viewing_tenant": request.session.get("admin_tenant_name"),
    }


@staff_member_required
def ai_dashboard(request):
    """Top-level operational overview."""
    today = date.today()
    week_ago = today - timedelta(days=6)

    usage_today = _tenant_filter(AIUsageLog.objects.filter(created_at__date=today), request)
    usage_week = _tenant_filter(AIUsageLog.objects.filter(created_at__date__gte=week_ago), request)

    today_agg = usage_today.aggregate(
        n=Count("id"),
        success=Count("id", filter=Q(status="SUCCESS")),
        failed=Count("id", filter=~Q(status="SUCCESS")),
        tokens=Sum("total_tokens"),
        cost=Sum("cost_usd"),
        avg_lat=Avg("latency_ms"),
    )

    week_per_day = (
        usage_week
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(
            n=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("cost_usd"),
        )
        .order_by("day")
    )

    top_features = (
        usage_week.values("feature__code", "feature__name")
        .annotate(n=Count("id"), tokens=Sum("total_tokens"), cost=Sum("cost_usd"))
        .order_by("-n")[:8]
    )

    recent_errors = (
        usage_today.exclude(status="SUCCESS")
        .select_related("feature", "provider", "model")
        .order_by("-created_at")[:10]
    )

    provider_health = AIProvider.objects.order_by("priority", "name")[:25]

    flagged_audit = (
        _tenant_filter(AIAuditLog.objects.filter(flagged=True), request)
        .order_by("-created_at")[:5]
    )

    ctx = _common_context(request, title="AI Governance Dashboard",
                         subtitle="Real-time operational overview")
    ctx.update({
        "today": today,
        "today_agg": today_agg,
        "week_per_day": list(week_per_day),
        "top_features": list(top_features),
        "recent_errors": recent_errors,
        "provider_health": provider_health,
        "flagged_audit": flagged_audit,
        "feature_count": AIFeature.objects.filter(is_enabled=True).count(),
        "provider_count": AIProvider.objects.filter(is_enabled=True).count(),
        "model_count": AIModel.objects.filter(is_enabled=True).count(),
    })
    return render(request, "admin/ai_core/dashboard.html", ctx)


@staff_member_required
def ai_cost_report(request):
    """30-day cost + token roll-up by feature, model & provider."""
    today = date.today()
    start = today - timedelta(days=29)
    rows = _tenant_filter(
        AICostTracking.objects.filter(date__gte=start), request,
    ).select_related("feature", "model", "provider")

    by_day = OrderedDict()
    for i in range(30):
        d = start + timedelta(days=i)
        by_day[d.isoformat()] = {"date": d.isoformat(), "requests": 0, "tokens": 0, "cost": Decimal("0")}
    by_feature: dict = {}
    by_provider: dict = {}
    totals = {"requests": 0, "tokens": 0, "cost": Decimal("0")}

    for r in rows:
        d = r.date.isoformat()
        if d in by_day:
            by_day[d]["requests"] += int(r.requests)
            by_day[d]["tokens"] += int(r.total_tokens)
            by_day[d]["cost"] += Decimal(r.cost_usd)
        fkey = r.feature.code if r.feature else "—"
        bf = by_feature.setdefault(fkey, {
            "feature": fkey, "name": r.feature.name if r.feature else "—",
            "requests": 0, "tokens": 0, "cost": Decimal("0"),
        })
        bf["requests"] += int(r.requests)
        bf["tokens"] += int(r.total_tokens)
        bf["cost"] += Decimal(r.cost_usd)
        pkey = r.provider.name if r.provider else "—"
        bp = by_provider.setdefault(pkey, {
            "provider": pkey, "requests": 0, "tokens": 0, "cost": Decimal("0"),
        })
        bp["requests"] += int(r.requests)
        bp["tokens"] += int(r.total_tokens)
        bp["cost"] += Decimal(r.cost_usd)
        totals["requests"] += int(r.requests)
        totals["tokens"] += int(r.total_tokens)
        totals["cost"] += Decimal(r.cost_usd)

    ctx = _common_context(request, title="AI Cost Report",
                         subtitle=f"30-day spend: {start.isoformat()} → {today.isoformat()}")
    ctx.update({
        "by_day": list(by_day.values()),
        "by_feature": sorted(by_feature.values(), key=lambda r: r["cost"], reverse=True),
        "by_provider": sorted(by_provider.values(), key=lambda r: r["cost"], reverse=True),
        "totals": totals,
        "start": start,
        "end": today,
    })
    return render(request, "admin/ai_core/cost_report.html", ctx)


@staff_member_required
def ai_health(request):
    """Provider health: circuit state, latency, success rate."""
    providers = AIProvider.objects.order_by("priority", "name")
    now = timezone.now()
    rows = []
    for p in providers:
        open_now = bool(p.circuit_open_until and p.circuit_open_until > now)
        rows.append({
            "obj": p,
            "open_now": open_now,
            "fails": p.consecutive_failures,
            "avg_latency_ms": int(p.avg_latency_ms or 0),
            "success_rate_pct": round(float(p.success_rate or 0) * 100, 1),
            "last_success": p.last_success_at,
            "last_failure": p.last_failure_at,
            "status": p.status,
            "model_count": p.models.filter(is_enabled=True).count(),
        })
    ctx = _common_context(request, title="AI Provider Health",
                         subtitle="Circuit-breaker, latency and success-rate per provider")
    ctx["rows"] = rows
    return render(request, "admin/ai_core/health.html", ctx)
