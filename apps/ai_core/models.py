"""
AI Governance + Operations — central data model.

Tables (per architectural spec):

    ai_features            Feature registry & policy (Doubt Solver, Quiz, ...)
    ai_providers           Provider registry (OpenAI, Anthropic, Azure, Local)
    ai_models              Model registry under each provider (gpt-4o, claude-3, ...)
    ai_prompts             Versioned prompt registry with rollback
    ai_usage_logs          Per-request usage + token + latency ledger
    ai_audit_logs          Compliance audit log (who, when, prompt, response, IP)
    ai_cost_tracking       Aggregated cost per tenant / feature / day
    ai_feedback            User feedback on AI responses
    ai_student_profiles    Per-student AI personalisation profile
    ai_learning_paths      AI-generated learning paths

Every business AI capability MUST route through this layer.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(TimestampedModel):
    """Tenant-scoped row. NULL tenant = global / platform-wide default."""
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
        db_index=True,
        help_text="NULL = platform-global default. Tenant rows override globals.",
    )

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# 1. Providers
# ---------------------------------------------------------------------------
class AIProvider(TimestampedModel):
    """
    LLM / AI vendor (OpenAI, Anthropic, Azure OpenAI, Google Gemini, Local Llama, etc.).

    API keys are stored encrypted (Fernet) via the `api_key_encrypted` column.
    Health, latency and circuit-breaker state live here.
    """

    class Kind(models.TextChoices):
        OPENAI = "OPENAI", "OpenAI"
        ANTHROPIC = "ANTHROPIC", "Anthropic"
        AZURE_OPENAI = "AZURE_OPENAI", "Azure OpenAI"
        GOOGLE = "GOOGLE", "Google Gemini"
        LOCAL = "LOCAL", "Local / Self-hosted"
        HUGGINGFACE = "HUGGINGFACE", "HuggingFace"
        OPENROUTER = "OPENROUTER", "OpenRouter"
        AWS_BEDROCK = "AWS_BEDROCK", "AWS Bedrock"
        WHISPER = "WHISPER", "Whisper (STT)"
        AZURE_SPEECH = "AZURE_SPEECH", "Azure Speech"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DEGRADED = "DEGRADED", "Degraded"
        OUTAGE = "OUTAGE", "Outage"
        DISABLED = "DISABLED", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    base_url = models.URLField(blank=True, default="")
    api_key_encrypted = models.TextField(blank=True, default="", help_text="Fernet-encrypted")
    extra_headers = models.JSONField(default=dict, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=30)

    priority = models.PositiveIntegerField(
        default=100, help_text="Lower wins in failover ordering."
    )
    weight = models.PositiveIntegerField(
        default=1, help_text="Used by weighted routing within same priority."
    )
    is_enabled = models.BooleanField(default=True, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    # Circuit breaker
    consecutive_failures = models.PositiveIntegerField(default=0)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    circuit_open_until = models.DateTimeField(null=True, blank=True)

    # Health metrics (rolling, updated by gateway)
    avg_latency_ms = models.FloatField(default=0.0)
    success_rate = models.FloatField(default=1.0, help_text="0..1 rolling window")

    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ai_providers"
        ordering = ("priority", "name")
        indexes = [
            models.Index(fields=["is_enabled", "status"]),
            models.Index(fields=["kind", "is_enabled"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} [{self.get_kind_display()}]"


# ---------------------------------------------------------------------------
# 2. Models
# ---------------------------------------------------------------------------
class AIModel(TimestampedModel):
    """
    A concrete model offered by a provider (gpt-4o, claude-3-5-sonnet, llama-3-70b,
    whisper-large-v3, text-embedding-3-large, etc.).
    """

    class Capability(models.TextChoices):
        CHAT = "CHAT", "Chat / Completion"
        EMBEDDING = "EMBEDDING", "Embeddings"
        STT = "STT", "Speech-to-Text"
        TTS = "TTS", "Text-to-Speech"
        VISION = "VISION", "Vision"
        IMAGE = "IMAGE", "Image generation"
        RERANK = "RERANK", "Reranker"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=120, help_text="Provider model id e.g. 'gpt-4o-mini'")
    display_name = models.CharField(max_length=120, blank=True, default="")
    capability = models.CharField(max_length=12, choices=Capability.choices, default=Capability.CHAT)

    context_window = models.PositiveIntegerField(default=8192)
    max_output_tokens = models.PositiveIntegerField(default=2048)

    # Cost ($ per 1K tokens). Stored in tenths of a cent (i.e. micro-dollars * 100).
    input_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    output_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    supports_streaming = models.BooleanField(default=True)
    supports_function_calling = models.BooleanField(default=False)
    supports_vision = models.BooleanField(default=False)

    is_enabled = models.BooleanField(default=True, db_index=True)
    is_default_for_capability = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ai_models"
        unique_together = (("provider", "name"),)
        ordering = ("provider__priority", "name")
        indexes = [
            models.Index(fields=["capability", "is_enabled"]),
            models.Index(fields=["is_default_for_capability"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.provider.name}/{self.name}"


# ---------------------------------------------------------------------------
# 3. Features
# ---------------------------------------------------------------------------
class AIFeature(TenantScopedModel):
    """
    A user-facing AI capability (Doubt Solver, Study Planner, Practice Quiz, etc.).

    Owns its enablement state, default model, prompt version, quotas and policies.
    """

    class Code(models.TextChoices):
        DOUBT_SOLVER = "DOUBT_SOLVER", "AI Doubt Solver"
        STUDY_PLANNER = "STUDY_PLANNER", "AI Study Planner"
        PRACTICE_QUIZ = "PRACTICE_QUIZ", "Practice Quiz Generator"
        PERFORMANCE_INSIGHTS = "PERFORMANCE_INSIGHTS", "Performance Insights"
        LEARNING_PATH = "LEARNING_PATH", "AI Learning Path"
        ADAPTIVE_LEARNING = "ADAPTIVE_LEARNING", "Adaptive Learning Engine"
        EXAM_RESULT_PLANNING = "EXAM_RESULT_PLANNING", "Exam Result Planning"
        CONTENT_SUMMARISER = "CONTENT_SUMMARISER", "Content Summariser"
        QUESTION_BANK = "QUESTION_BANK", "Question Bank AI"
        TUTOR_CHAT = "TUTOR_CHAT", "AI Tutor Chat"

    class ResponseStyle(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"
        EXAM_FOCUSED = "EXAM_FOCUSED", "Exam-focused"

    class HallucinationGuard(models.TextChoices):
        OFF = "OFF", "Off"
        BASIC = "BASIC", "Basic"
        STRICT = "STRICT", "Strict"
        CITATION_REQUIRED = "CITATION_REQUIRED", "Citation Required"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(max_length=32, choices=Code.choices, db_index=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True, default="")

    # Lifecycle
    is_enabled = models.BooleanField(default=False, db_index=True)
    is_beta = models.BooleanField(default=False)
    rollout_percent = models.PositiveSmallIntegerField(default=100, help_text="0-100")

    # Model routing
    default_model = models.ForeignKey(
        AIModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="features"
    )
    fallback_models = models.ManyToManyField(
        AIModel, blank=True, related_name="fallback_for_features",
        help_text="Ordered failover candidates."
    )

    # Prompt
    active_prompt_version = models.ForeignKey(
        "AIPromptVersion", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="active_for",
    )

    # Quotas & cost (governance)
    max_input_tokens = models.PositiveIntegerField(default=4000)
    max_output_tokens = models.PositiveIntegerField(default=1000)
    daily_request_budget = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    monthly_token_budget = models.PositiveBigIntegerField(default=0)
    monthly_cost_budget_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    per_user_daily_quota = models.PositiveIntegerField(default=0)
    rate_limit_per_minute = models.PositiveIntegerField(default=60)

    # Access control
    allowed_roles = models.JSONField(
        default=list, blank=True,
        help_text="List of role codes: STUDENT, TEACHER, ADMIN, SUPER_ADMIN.",
    )

    # Doubt Solver / chat specific
    input_modes = models.JSONField(
        default=list, blank=True, help_text="Subset of ['TEXT','VOICE','IMAGE']"
    )
    languages = models.JSONField(
        default=list, blank=True, help_text="ISO codes e.g. ['en','hi']"
    )
    audio_transcription_enabled = models.BooleanField(default=False)
    text_to_speech_enabled = models.BooleanField(default=False)
    conversation_memory_enabled = models.BooleanField(default=True)
    conversation_memory_turns = models.PositiveIntegerField(default=10)
    response_style = models.CharField(
        max_length=24, choices=ResponseStyle.choices, default=ResponseStyle.INTERMEDIATE
    )

    # Safety
    hallucination_guard = models.CharField(
        max_length=24, choices=HallucinationGuard.choices, default=HallucinationGuard.STRICT
    )
    toxicity_filter_enabled = models.BooleanField(default=True)
    prompt_injection_filter_enabled = models.BooleanField(default=True)
    pii_masking_enabled = models.BooleanField(default=True)
    exam_mode_block = models.BooleanField(
        default=True, help_text="Block this feature while student is in an exam."
    )
    teacher_escalation_enabled = models.BooleanField(default=True)

    # Free-form per-feature config
    config = models.JSONField(default=dict, blank=True)

    # Status
    last_health_at = models.DateTimeField(null=True, blank=True)
    last_health_ok = models.BooleanField(default=True)

    class Meta:
        db_table = "ai_features"
        unique_together = (("tenant", "code"),)
        ordering = ("tenant_id", "code")
        indexes = [
            models.Index(fields=["is_enabled", "code"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        tag = self.tenant.code if self.tenant_id else "GLOBAL"
        return f"{tag}:{self.get_code_display()}"


# ---------------------------------------------------------------------------
# 4. Prompts (registry + versioning + rollback)
# ---------------------------------------------------------------------------
class AIPrompt(TenantScopedModel):
    """
    Named, addressable prompt slot. Holds metadata; actual content lives in versions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.ForeignKey(
        AIFeature, on_delete=models.CASCADE, related_name="prompts", null=True, blank=True,
        help_text="Optional — leave NULL for shared / utility prompts.",
    )
    name = models.SlugField(max_length=160)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ai_prompts"
        unique_together = (("tenant", "name"),)
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class AIPromptVersion(TimestampedModel):
    """
    Immutable prompt version. Allows A/B testing, rollback, approval workflow.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"
        ROLLED_BACK = "ROLLED_BACK", "Rolled back"
        DEPRECATED = "DEPRECATED", "Deprecated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt = models.ForeignKey(AIPrompt, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    system_prompt = models.TextField(blank=True, default="")
    user_template = models.TextField(blank=True, default="", help_text="Jinja-style placeholders.")
    variables = models.JSONField(default=list, blank=True, help_text="Declared variable names.")
    parameters = models.JSONField(
        default=dict, blank=True,
        help_text="Per-version overrides: temperature, top_p, max_tokens, etc.",
    )

    # Approval / audit
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_prompt_versions_authored",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_prompt_versions_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    change_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ai_prompt_versions"
        unique_together = (("prompt", "version"),)
        ordering = ("prompt", "-version")
        indexes = [
            models.Index(fields=["prompt", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.prompt.name} v{self.version} [{self.status}]"


# ---------------------------------------------------------------------------
# 5. Usage logs (every gateway call)
# ---------------------------------------------------------------------------
class AIUsageLog(TenantScopedModel):
    """
    One row per AI gateway call. Powers analytics dashboards.
    """

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        TIMEOUT = "TIMEOUT", "Timeout"
        BLOCKED = "BLOCKED", "Blocked by policy"
        RATE_LIMITED = "RATE_LIMITED", "Rate limited"
        FALLBACK = "FALLBACK", "Served by fallback"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(max_length=64, unique=True, db_index=True)
    correlation_id = models.CharField(max_length=64, db_index=True, blank=True, default="")

    feature = models.ForeignKey(AIFeature, on_delete=models.SET_NULL, null=True, related_name="usage")
    provider = models.ForeignKey(AIProvider, on_delete=models.SET_NULL, null=True, related_name="usage")
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, related_name="usage")
    prompt_version = models.ForeignKey(
        AIPromptVersion, on_delete=models.SET_NULL, null=True, related_name="usage"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage",
    )
    user_role = models.CharField(max_length=32, blank=True, default="")
    actor_type = models.CharField(max_length=24, blank=True, default="", help_text="STUDENT/TEACHER/ADMIN/SYSTEM")
    actor_id = models.CharField(max_length=64, blank=True, default="")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)

    latency_ms = models.PositiveIntegerField(default=0)
    confidence_score = models.FloatField(null=True, blank=True)
    abuse_score = models.FloatField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ai_usage_logs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["feature", "created_at"]),
            models.Index(fields=["provider", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]


# ---------------------------------------------------------------------------
# 6. Audit logs (PII + prompt + response retention for compliance)
# ---------------------------------------------------------------------------
class AIAuditLog(TenantScopedModel):
    """
    Sensitive record of full prompt & response text for compliance review.

    Retention is governed via cleanup tasks (Batch 5).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usage = models.OneToOneField(
        AIUsageLog, on_delete=models.CASCADE, related_name="audit", null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_audit",
    )
    feature_code = models.CharField(max_length=32, db_index=True)
    model_name = models.CharField(max_length=120, blank=True, default="")
    provider_name = models.CharField(max_length=120, blank=True, default="")

    prompt_text = models.TextField(blank=True, default="")
    response_text = models.TextField(blank=True, default="")
    redacted_prompt = models.TextField(blank=True, default="")
    redacted_response = models.TextField(blank=True, default="")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True, default="")

    flagged = models.BooleanField(default=False, db_index=True)
    flag_reason = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "ai_audit_logs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["feature_code", "created_at"]),
            models.Index(fields=["flagged", "created_at"]),
        ]


# ---------------------------------------------------------------------------
# 7. Cost tracking (daily aggregate)
# ---------------------------------------------------------------------------
class AICostTracking(TenantScopedModel):
    """
    Daily roll-up of cost & tokens per (tenant, feature, model).
    Updated by gateway after each call (atomic upsert) OR by nightly task.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(db_index=True)
    feature = models.ForeignKey(AIFeature, on_delete=models.CASCADE, related_name="cost_rows", null=True)
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey(AIProvider, on_delete=models.SET_NULL, null=True, blank=True)
    requests = models.PositiveBigIntegerField(default=0)
    failed_requests = models.PositiveBigIntegerField(default=0)
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    total_tokens = models.PositiveBigIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=14, decimal_places=6, default=0)

    class Meta:
        db_table = "ai_cost_tracking"
        unique_together = (("tenant", "date", "feature", "model"),)
        ordering = ("-date",)
        indexes = [
            models.Index(fields=["tenant", "date"]),
            models.Index(fields=["date", "feature"]),
        ]


# ---------------------------------------------------------------------------
# 8. Feedback (thumbs up/down + rating + free text)
# ---------------------------------------------------------------------------
class AIFeedback(TenantScopedModel):
    class Verdict(models.TextChoices):
        UP = "UP", "Thumbs up"
        DOWN = "DOWN", "Thumbs down"
        NEUTRAL = "NEUTRAL", "Neutral"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usage = models.ForeignKey(AIUsageLog, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_feedback",
    )
    verdict = models.CharField(max_length=8, choices=Verdict.choices)
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1..5")
    comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ai_feedback"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["usage"]),
            models.Index(fields=["verdict", "created_at"]),
        ]


# ---------------------------------------------------------------------------
# 9. Student personalisation profile
# ---------------------------------------------------------------------------
class AIStudentProfile(TenantScopedModel):
    """
    Per-student AI personalisation state — feeds Adaptive Learning,
    Study Planner, Learning Path, Exam Result Planning.
    """

    class RiskBand(models.TextChoices):
        TOP = "TOP", "Top performer"
        SAFE = "SAFE", "Safe zone"
        MEDIUM = "MEDIUM", "Medium risk"
        HIGH = "HIGH", "High risk"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        "accounts.Student", on_delete=models.CASCADE, related_name="ai_profile",
    )

    # Skill model
    mastery_map = models.JSONField(default=dict, blank=True, help_text="topic_id -> mastery 0..1")
    weak_topics = models.JSONField(default=list, blank=True)
    strong_topics = models.JSONField(default=list, blank=True)
    learning_style = models.CharField(max_length=24, blank=True, default="")
    preferred_language = models.CharField(max_length=8, blank=True, default="en")

    # Behavioural signals
    avg_session_minutes = models.FloatField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    engagement_score = models.FloatField(default=0)
    consistency_score = models.FloatField(default=0)

    # Predictions
    predicted_score = models.FloatField(null=True, blank=True)
    prediction_confidence = models.FloatField(null=True, blank=True)
    risk_band = models.CharField(
        max_length=8, choices=RiskBand.choices, default=RiskBand.SAFE, db_index=True
    )

    # Embeddings reference (for vector DB integration later)
    embedding_ref = models.CharField(max_length=120, blank=True, default="")
    embedding_updated_at = models.DateTimeField(null=True, blank=True)

    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ai_student_profiles"
        indexes = [
            models.Index(fields=["tenant", "risk_band"]),
        ]


# ---------------------------------------------------------------------------
# 10. Learning paths
# ---------------------------------------------------------------------------
class AILearningPath(TenantScopedModel):
    """
    AI-generated learning path / plan for one student or cohort.
    """

    class Kind(models.TextChoices):
        STUDY_PLAN = "STUDY_PLAN", "Study plan"
        LEARNING_PATH = "LEARNING_PATH", "Learning path"
        ADAPTIVE = "ADAPTIVE", "Adaptive sequence"
        EXAM_PLAN = "EXAM_PLAN", "Exam result plan"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "accounts.Student", on_delete=models.CASCADE, related_name="ai_learning_paths",
        null=True, blank=True,
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True, default="")

    target_exam_id = models.CharField(max_length=64, blank=True, default="")
    target_date = models.DateField(null=True, blank=True)

    # Body of the plan: structured days/weeks/items
    plan = models.JSONField(default=dict, blank=True)
    # Adherence / progress
    completion_percent = models.FloatField(default=0)
    adherence_percent = models.FloatField(default=0)
    planned_minutes = models.PositiveIntegerField(default=0)
    actual_minutes = models.PositiveIntegerField(default=0)

    # Provenance
    generated_by_model = models.ForeignKey(
        AIModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_paths",
    )
    generated_by_prompt_version = models.ForeignKey(
        AIPromptVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_paths",
    )
    confidence = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "ai_learning_paths"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["tenant", "kind", "status"]),
            models.Index(fields=["student", "kind"]),
        ]
