"""Resolve feature → prompt + provider/model failover chain."""
from __future__ import annotations

import logging
from typing import Iterable

from django.db.models import Q

from ..models import AIFeature, AIModel, AIPromptVersion

logger = logging.getLogger(__name__)


def resolve_feature(feature_code: str, tenant_id=None) -> AIFeature | None:
    """Prefer tenant-scoped row; fall back to global default (tenant IS NULL)."""
    qs = AIFeature.objects.filter(code=feature_code, is_enabled=True)
    if tenant_id:
        f = qs.filter(tenant_id=tenant_id).first()
        if f:
            return f
    return qs.filter(tenant__isnull=True).first()


def resolve_active_prompt_version(feature: AIFeature) -> AIPromptVersion | None:
    pv = feature.active_prompt_version
    if pv:
        return pv
    # Otherwise pick newest published version for this feature's prompts
    return (
        AIPromptVersion.objects
        .filter(prompt__feature=feature, status="PUBLISHED")
        .order_by("-version")
        .first()
    )


def resolve_model_chain(feature: AIFeature, capability: str = "CHAT") -> list[AIModel]:
    """Return [primary, *fallbacks] — filtered to enabled rows with usable providers."""
    chain: list[AIModel] = []
    if feature.default_model_id and feature.default_model and feature.default_model.is_enabled:
        chain.append(feature.default_model)
    for m in feature.fallback_models.filter(is_enabled=True):
        if m.id not in {x.id for x in chain}:
            chain.append(m)
    # If nothing configured, use platform default for this capability.
    if not chain:
        platform_default = (
            AIModel.objects
            .filter(capability=capability, is_enabled=True, is_default_for_capability=True)
            .select_related("provider")
            .order_by("provider__priority")
            .first()
        )
        if platform_default:
            chain.append(platform_default)
    # Final filter: provider enabled
    chain = [m for m in chain if m.provider and m.provider.is_enabled]
    return chain
