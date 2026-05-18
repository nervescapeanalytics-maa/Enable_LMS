"""Per-feature budget + rate-limit + quota enforcement.

The ledger is Redis-backed when available (django-cache compatible) so that
counters are shared across workers; falls back to the local-memory cache
otherwise (correct for single-process dev).

Keys:
  ai:rl:<feature>:<user>:m<minute>      → per-minute request count (rate_limit_per_minute)
  ai:q:<feature>:<user>:d<YYYYMMDD>     → per-user daily request count (per_user_daily_quota)
  ai:q:<feature>:tenant:<t>:d<YYYYMMDD> → per-tenant daily request count (daily_request_budget)
  ai:tok:<feature>:tenant:<t>:m<YYYYMM> → per-tenant monthly tokens   (monthly_token_budget)
  ai:cost:<feature>:tenant:<t>:m<YYYYMM>→ per-tenant monthly cost USD (monthly_cost_budget_usd, basis-points)
"""
from __future__ import annotations

from datetime import datetime

from django.core.cache import cache

from .exceptions import BudgetExceeded, RateLimited


def _now():
    return datetime.utcnow()


def _kpref(feature_code: str) -> str:
    return f"ai:rl:{feature_code}"


def _user_id(user) -> str:
    if not user or not getattr(user, "pk", None):
        return "anon"
    return str(user.pk)


def _tenant_id(tenant_id) -> str:
    return str(tenant_id) if tenant_id else "global"


def _incr(key: str, ttl: int, amount: int = 1) -> int:
    try:
        new_val = cache.incr(key, amount)
    except ValueError:
        # Key didn't exist — set it.
        cache.set(key, amount, ttl)
        return amount
    return new_val


def check_and_consume_request(feature, user, tenant_id) -> None:
    """Raise RateLimited / BudgetExceeded BEFORE making the upstream call."""
    now = _now()
    minute = now.strftime("%Y%m%d%H%M")
    day = now.strftime("%Y%m%d")
    uid = _user_id(user)
    tid = _tenant_id(tenant_id)
    fc = feature.code

    # Per-minute rate limit (per user)
    if feature.rate_limit_per_minute and feature.rate_limit_per_minute > 0:
        k = f"ai:rl:{fc}:{uid}:m{minute}"
        n = _incr(k, ttl=90)
        if n > feature.rate_limit_per_minute:
            raise RateLimited(
                f"Rate limit: {feature.rate_limit_per_minute}/min for {fc}",
                feature=fc, limit=feature.rate_limit_per_minute,
            )

    # Per-user daily quota
    if feature.per_user_daily_quota and feature.per_user_daily_quota > 0:
        k = f"ai:q:{fc}:{uid}:d{day}"
        n = _incr(k, ttl=90000)  # 25h
        if n > feature.per_user_daily_quota:
            raise BudgetExceeded(
                f"Daily user quota exceeded for {fc}",
                feature=fc, scope="user", limit=feature.per_user_daily_quota,
            )

    # Per-tenant daily request budget
    if feature.daily_request_budget and feature.daily_request_budget > 0:
        k = f"ai:q:{fc}:tenant:{tid}:d{day}"
        n = _incr(k, ttl=90000)
        if n > feature.daily_request_budget:
            raise BudgetExceeded(
                f"Tenant daily budget exceeded for {fc}",
                feature=fc, scope="tenant", limit=feature.daily_request_budget,
            )


def check_token_and_cost_budgets(feature, tenant_id, *, tokens: int, cost_usd: float) -> None:
    """Called AFTER a successful call to bump monthly counters.

    If the new value crosses the configured budget, we still allow the current
    response (don't punish the user for the call that crossed) but raise on the
    NEXT call attempt via `pre_check_monthly_budgets`.
    """
    now = _now()
    month = now.strftime("%Y%m")
    tid = _tenant_id(tenant_id)
    fc = feature.code
    if tokens:
        _incr(f"ai:tok:{fc}:tenant:{tid}:m{month}", ttl=40 * 86400, amount=int(tokens))
    if cost_usd:
        # store as integer micro-USD for cache.incr() integer math.
        _incr(f"ai:cost:{fc}:tenant:{tid}:m{month}", ttl=40 * 86400, amount=int(cost_usd * 1_000_000))


def pre_check_monthly_budgets(feature, tenant_id) -> None:
    now = _now()
    month = now.strftime("%Y%m")
    tid = _tenant_id(tenant_id)
    fc = feature.code
    if feature.monthly_token_budget and feature.monthly_token_budget > 0:
        used = cache.get(f"ai:tok:{fc}:tenant:{tid}:m{month}", 0) or 0
        if int(used) >= int(feature.monthly_token_budget):
            raise BudgetExceeded(
                f"Monthly token budget reached for {fc}",
                feature=fc, scope="tokens", limit=feature.monthly_token_budget, used=int(used),
            )
    if feature.monthly_cost_budget_usd and float(feature.monthly_cost_budget_usd) > 0:
        used_micro = cache.get(f"ai:cost:{fc}:tenant:{tid}:m{month}", 0) or 0
        used = float(used_micro) / 1_000_000.0
        if used >= float(feature.monthly_cost_budget_usd):
            raise BudgetExceeded(
                f"Monthly cost budget reached for {fc}",
                feature=fc, scope="cost", limit=float(feature.monthly_cost_budget_usd), used=used,
            )
