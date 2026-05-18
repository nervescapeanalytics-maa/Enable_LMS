"""
AI Governance admin — Super-Admin console for everything AI.

Pages registered:
    AI Providers              -> /admin/ai_core/aiprovider/
    AI Models                 -> /admin/ai_core/aimodel/
    AI Features               -> /admin/ai_core/aifeature/
    AI Prompts                -> /admin/ai_core/aiprompt/
    AI Prompt Versions        -> /admin/ai_core/aipromptversion/
    AI Usage Logs             -> /admin/ai_core/aiusagelog/   (read-only)
    AI Audit Logs             -> /admin/ai_core/aiauditlog/   (read-only)
    AI Cost Tracking          -> /admin/ai_core/aicosttracking/ (read-only)
    AI Feedback               -> /admin/ai_core/aifeedback/  (read-only)
    AI Student Profiles       -> /admin/ai_core/aistudentprofile/
    AI Learning Paths         -> /admin/ai_core/ailearningpath/

Tenant scoping & RBAC gating are applied where appropriate. Rollback actions are
exposed on AIPromptVersion. Health/cost dashboards live as custom changelist
columns and will be expanded in Batch 3.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html

from core.admin_utils import EnhancedModelAdmin

from .models import (
    AIAuditLog,
    AICostTracking,
    AIFeature,
    AIFeedback,
    AILearningPath,
    AIModel,
    AIProvider,
    AIPrompt,
    AIPromptVersion,
    AIStudentProfile,
    AIUsageLog,
)


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class _ReadOnlyAdmin(EnhancedModelAdmin):
    actions = None  # disable bulk export/activate actions on read-only ledgers

    def has_add_permission(self, request, obj=None):  # noqa: D401
        return False

    def has_change_permission(self, request, obj=None):  # noqa: D401
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: D401
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
@admin.register(AIProvider)
class AIProviderAdmin(EnhancedModelAdmin):
    list_display = (
        "name", "kind", "priority", "is_enabled", "status_pill",
        "success_rate_pct", "avg_latency_ms", "consecutive_failures",
        "last_success_at",
    )
    list_filter = ("kind", "status", "is_enabled")
    search_fields = ("name", "base_url")
    readonly_fields = (
        "consecutive_failures", "last_failure_at", "last_success_at",
        "circuit_open_until", "avg_latency_ms", "success_rate",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("Identity", {"fields": ("name", "kind", "base_url", "extra_headers", "timeout_seconds")}),
        ("Credentials", {"fields": ("api_key_encrypted",), "classes": ("collapse",)}),
        ("Routing", {"fields": ("priority", "weight", "is_enabled", "status", "notes")}),
        ("Health", {"fields": (
            "consecutive_failures", "last_failure_at", "last_success_at",
            "circuit_open_until", "avg_latency_ms", "success_rate",
        )}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = ("action_enable", "action_disable", "action_reset_breaker")

    @admin.display(description="Status")
    def status_pill(self, obj: AIProvider) -> str:
        color = {
            obj.Status.ACTIVE: "#2e7d32",
            obj.Status.DEGRADED: "#ed6c02",
            obj.Status.OUTAGE: "#c62828",
            obj.Status.DISABLED: "#616161",
        }.get(obj.status, "#616161")
        return format_html(
            '<span style="padding:2px 8px;border-radius:10px;background:{};color:#fff;font-size:11px">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="Success %")
    def success_rate_pct(self, obj: AIProvider) -> str:
        return f"{obj.success_rate * 100:.1f}%"

    @admin.action(description="Enable selected providers")
    def action_enable(self, request, queryset):
        n = queryset.update(is_enabled=True, status=AIProvider.Status.ACTIVE)
        self.message_user(request, f"Enabled {n} provider(s).", messages.SUCCESS)

    @admin.action(description="Disable selected providers")
    def action_disable(self, request, queryset):
        n = queryset.update(is_enabled=False, status=AIProvider.Status.DISABLED)
        self.message_user(request, f"Disabled {n} provider(s).", messages.WARNING)

    @admin.action(description="Reset circuit breaker")
    def action_reset_breaker(self, request, queryset):
        n = queryset.update(
            consecutive_failures=0, circuit_open_until=None,
            status=AIProvider.Status.ACTIVE,
        )
        self.message_user(request, f"Reset breaker on {n} provider(s).", messages.SUCCESS)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
@admin.register(AIModel)
class AIModelAdmin(EnhancedModelAdmin):
    list_display = (
        "name", "provider", "capability", "context_window", "max_output_tokens",
        "input_cost_per_1k", "output_cost_per_1k", "is_enabled",
        "is_default_for_capability",
    )
    list_filter = ("provider", "capability", "is_enabled", "is_default_for_capability")
    search_fields = ("name", "display_name", "provider__name")
    autocomplete_fields = ("provider",)


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
@admin.register(AIFeature)
class AIFeatureAdmin(EnhancedModelAdmin):
    list_display = (
        "code", "tenant", "is_enabled", "is_beta", "rollout_percent",
        "default_model", "rate_limit_per_minute", "exam_mode_block",
        "last_health_at", "last_health_ok",
    )
    list_filter = ("code", "is_enabled", "is_beta", "tenant")
    search_fields = ("name", "code", "description")
    autocomplete_fields = ("tenant", "default_model", "active_prompt_version")
    filter_horizontal = ("fallback_models",)
    readonly_fields = ("last_health_at", "last_health_ok", "created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("tenant", "code", "name", "description")}),
        ("Lifecycle", {"fields": ("is_enabled", "is_beta", "rollout_percent")}),
        ("Model routing", {"fields": ("default_model", "fallback_models", "active_prompt_version")}),
        ("Quotas & Cost", {"fields": (
            "max_input_tokens", "max_output_tokens",
            "daily_request_budget", "monthly_token_budget", "monthly_cost_budget_usd",
            "per_user_daily_quota", "rate_limit_per_minute",
        )}),
        ("Access Control", {"fields": ("allowed_roles",)}),
        ("Doubt Solver / Chat", {"fields": (
            "input_modes", "languages",
            "audio_transcription_enabled", "text_to_speech_enabled",
            "conversation_memory_enabled", "conversation_memory_turns",
            "response_style",
        ), "classes": ("collapse",)}),
        ("Safety", {"fields": (
            "hallucination_guard", "toxicity_filter_enabled",
            "prompt_injection_filter_enabled", "pii_masking_enabled",
            "exam_mode_block", "teacher_escalation_enabled",
        )}),
        ("Config", {"fields": ("config",), "classes": ("collapse",)}),
        ("Health", {"fields": ("last_health_at", "last_health_ok"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = ("action_enable", "action_disable")

    @admin.action(description="Enable selected features")
    def action_enable(self, request, queryset):
        n = queryset.update(is_enabled=True)
        self.message_user(request, f"Enabled {n} feature(s).", messages.SUCCESS)

    @admin.action(description="Disable selected features")
    def action_disable(self, request, queryset):
        n = queryset.update(is_enabled=False)
        self.message_user(request, f"Disabled {n} feature(s).", messages.WARNING)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
class AIPromptVersionInline(admin.TabularInline):
    model = AIPromptVersion
    extra = 0
    fields = ("version", "status", "author", "approved_by", "published_at", "change_note")
    readonly_fields = ("version", "author", "approved_by", "published_at")
    show_change_link = True


@admin.register(AIPrompt)
class AIPromptAdmin(EnhancedModelAdmin):
    list_display = ("name", "tenant", "feature", "is_active", "version_count", "active_version")
    list_filter = ("is_active", "tenant", "feature")
    search_fields = ("name", "description")
    autocomplete_fields = ("tenant", "feature")
    inlines = (AIPromptVersionInline,)

    @admin.display(description="Versions")
    def version_count(self, obj):
        return obj.versions.count()

    @admin.display(description="Active version")
    def active_version(self, obj):
        v = obj.versions.filter(status=AIPromptVersion.Status.PUBLISHED).order_by("-version").first()
        return f"v{v.version}" if v else "—"


@admin.register(AIPromptVersion)
class AIPromptVersionAdmin(EnhancedModelAdmin):
    list_display = ("prompt", "version", "status", "author", "approved_by", "published_at")
    list_filter = ("status", "prompt")
    search_fields = ("prompt__name", "change_note")
    autocomplete_fields = ("prompt",)
    readonly_fields = ("created_at", "updated_at", "approved_at", "published_at", "rolled_back_at")
    actions = ("action_approve", "action_publish", "action_rollback")

    @admin.action(description="Approve selected versions")
    def action_approve(self, request, queryset):
        now = timezone.now()
        n = queryset.filter(status=AIPromptVersion.Status.UNDER_REVIEW).update(
            status=AIPromptVersion.Status.APPROVED, approved_at=now, approved_by=request.user,
        )
        self.message_user(request, f"Approved {n} version(s).", messages.SUCCESS)

    @admin.action(description="Publish selected versions (activates them on their feature)")
    def action_publish(self, request, queryset):
        now = timezone.now()
        published = 0
        for v in queryset.select_related("prompt"):
            if v.status not in {AIPromptVersion.Status.APPROVED, AIPromptVersion.Status.ROLLED_BACK}:
                continue
            # Demote previous published versions of same prompt
            AIPromptVersion.objects.filter(
                prompt=v.prompt, status=AIPromptVersion.Status.PUBLISHED,
            ).update(status=AIPromptVersion.Status.DEPRECATED)
            v.status = AIPromptVersion.Status.PUBLISHED
            v.published_at = now
            v.save(update_fields=["status", "published_at", "updated_at"])
            # Point all features using this prompt to the new version
            AIFeature.objects.filter(prompts=v.prompt).update(active_prompt_version=v)
            published += 1
        self.message_user(request, f"Published {published} version(s).", messages.SUCCESS)

    @admin.action(description="Rollback selected versions")
    def action_rollback(self, request, queryset):
        now = timezone.now()
        n = 0
        for v in queryset:
            if v.status != AIPromptVersion.Status.PUBLISHED:
                continue
            v.status = AIPromptVersion.Status.ROLLED_BACK
            v.rolled_back_at = now
            v.save(update_fields=["status", "rolled_back_at", "updated_at"])
            # Reactivate previous published version if any
            prev = (AIPromptVersion.objects
                    .filter(prompt=v.prompt, version__lt=v.version)
                    .exclude(status=AIPromptVersion.Status.ROLLED_BACK)
                    .order_by("-version").first())
            if prev:
                prev.status = AIPromptVersion.Status.PUBLISHED
                prev.save(update_fields=["status", "updated_at"])
                AIFeature.objects.filter(prompts=v.prompt).update(active_prompt_version=prev)
            n += 1
        self.message_user(request, f"Rolled back {n} version(s).", messages.WARNING)


# ---------------------------------------------------------------------------
# Usage / Audit / Cost / Feedback — read-only ledgers
# ---------------------------------------------------------------------------
@admin.register(AIUsageLog)
class AIUsageLogAdmin(_ReadOnlyAdmin):
    list_display = (
        "created_at", "tenant", "feature", "provider", "model",
        "status", "latency_ms", "total_tokens", "cost_usd", "user",
    )
    list_filter = ("status", "feature", "provider", "model", "tenant")
    search_fields = ("request_id", "correlation_id", "error_code", "actor_id")
    date_hierarchy = "created_at"

    def changelist_view(self, request, extra_context=None):
        today = timezone.now().date()
        qs = AIUsageLog.objects.filter(created_at__date=today)
        agg = qs.aggregate(
            total=Sum("total_tokens"), cost=Sum("cost_usd"),
        )
        extra_context = extra_context or {}
        extra_context.update({
            "ai_today_requests": qs.count(),
            "ai_today_tokens": agg["total"] or 0,
            "ai_today_cost": agg["cost"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AIAuditLog)
class AIAuditLogAdmin(_ReadOnlyAdmin):
    list_display = ("created_at", "tenant", "feature_code", "user", "flagged", "flag_reason", "ip_address")
    list_filter = ("flagged", "feature_code", "tenant")
    search_fields = ("flag_reason", "redacted_prompt", "redacted_response")
    date_hierarchy = "created_at"


@admin.register(AICostTracking)
class AICostTrackingAdmin(_ReadOnlyAdmin):
    list_display = ("date", "tenant", "feature", "model", "requests", "failed_requests",
                    "total_tokens", "cost_usd")
    list_filter = ("date", "tenant", "feature", "model")
    date_hierarchy = "date"


@admin.register(AIFeedback)
class AIFeedbackAdmin(_ReadOnlyAdmin):
    list_display = ("created_at", "tenant", "usage", "user", "verdict", "rating")
    list_filter = ("verdict", "rating", "tenant")
    search_fields = ("comment",)
    date_hierarchy = "created_at"


# ---------------------------------------------------------------------------
# Student profiles & learning paths
# ---------------------------------------------------------------------------
@admin.register(AIStudentProfile)
class AIStudentProfileAdmin(EnhancedModelAdmin):
    list_display = ("student", "tenant", "risk_band", "predicted_score",
                    "engagement_score", "consistency_score", "last_active_at")
    list_filter = ("risk_band", "tenant")
    search_fields = ("student__user__email", "student__user__username")
    autocomplete_fields = ("tenant", "student")
    readonly_fields = ("created_at", "updated_at", "embedding_updated_at")


@admin.register(AILearningPath)
class AILearningPathAdmin(EnhancedModelAdmin):
    list_display = ("title", "student", "kind", "status", "completion_percent",
                    "adherence_percent", "target_date", "created_at")
    list_filter = ("kind", "status", "tenant")
    search_fields = ("title", "summary")
    autocomplete_fields = ("tenant", "student", "generated_by_model", "generated_by_prompt_version")
    readonly_fields = ("created_at", "updated_at")
