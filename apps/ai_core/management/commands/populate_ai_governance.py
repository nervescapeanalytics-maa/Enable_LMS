"""
Populate AI Governance & Operations with realistic demo data.

Idempotent — re-running updates existing rows instead of duplicating.

Creates:
  * 5 providers (OpenAI, Anthropic, Azure OpenAI, Google, Local) with realistic
    config, health metrics and circuit state.
  * 10+ models tied to providers with proper costs & context windows.
  * 7 features (one per AIFeature.Code) wired to default + fallback models,
    realistic tenant budgets / rate limits / quotas.
  * Multiple prompt versions per feature (DRAFT, APPROVED, PUBLISHED rollout
    history) so the version timeline is visible.
  * 30 days of synthetic usage logs, paired audit rows + daily cost roll-ups.
  * 25 feedback rows (mix of UP/DOWN/NEUTRAL).
  * Optional: student profiles + learning paths if accounts.Student rows exist.

Usage:
    python manage.py populate_ai_governance              # default volume
    python manage.py populate_ai_governance --days 60    # more usage history
    python manage.py populate_ai_governance --reset      # wipe usage first
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ai_core.models import (
    AIAuditLog,
    AICostTracking,
    AIFeature,
    AIFeedback,
    AILearningPath,
    AIModel,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
    AIStudentProfile,
    AIUsageLog,
)


# ---------------------------------------------------------------------------
PROVIDER_SPECS = [
    dict(
        name="OpenAI", kind=AIProvider.Kind.OPENAI,
        base_url="https://api.openai.com/v1", priority=10, weight=2,
        is_enabled=True, status="ACTIVE",
        avg_latency_ms=420.0, success_rate=0.992, timeout_seconds=30,
    ),
    dict(
        name="Anthropic", kind=AIProvider.Kind.ANTHROPIC,
        base_url="https://api.anthropic.com/v1", priority=20, weight=1,
        is_enabled=True, status="ACTIVE",
        avg_latency_ms=560.0, success_rate=0.988, timeout_seconds=30,
    ),
    dict(
        name="Azure OpenAI", kind=AIProvider.Kind.AZURE_OPENAI,
        base_url="https://contoso.openai.azure.com", priority=15, weight=1,
        is_enabled=True, status="ACTIVE",
        avg_latency_ms=380.0, success_rate=0.995, timeout_seconds=30,
    ),
    dict(
        name="Google Gemini", kind=AIProvider.Kind.GOOGLE,
        base_url="https://generativelanguage.googleapis.com/v1beta",
        priority=30, weight=1, is_enabled=True, status="DEGRADED",
        avg_latency_ms=720.0, success_rate=0.951, timeout_seconds=30,
        consecutive_failures=2,
    ),
    dict(
        name="Local LLM (Ollama)", kind=AIProvider.Kind.LOCAL,
        base_url="http://localhost:11434/v1", priority=90, weight=1,
        is_enabled=False, status="DISABLED",
        avg_latency_ms=180.0, success_rate=1.0, timeout_seconds=60,
    ),
]


MODEL_SPECS = [
    # (provider, name, capability, ctx, max_out, in_$/1k, out_$/1k, default_for_cap)
    ("OpenAI",         "gpt-4o",                       AIModel.Capability.CHAT,      128_000, 4096, "0.0025",  "0.01",   False),
    ("OpenAI",         "gpt-4o-mini",                  AIModel.Capability.CHAT,      128_000, 4096, "0.00015", "0.0006", True),
    ("OpenAI",         "text-embedding-3-large",       AIModel.Capability.EMBEDDING, 8192,    0,    "0.00013", "0",      True),
    ("OpenAI",         "whisper-1",                    AIModel.Capability.STT,       0,       0,    "0.006",   "0",      True),
    ("OpenAI",         "tts-1",                        AIModel.Capability.TTS,       0,       0,    "0.015",   "0",      True),
    ("Anthropic",      "claude-3-5-sonnet-20241022",   AIModel.Capability.CHAT,      200_000, 8192, "0.003",   "0.015",  False),
    ("Anthropic",      "claude-3-5-haiku-20241022",    AIModel.Capability.CHAT,      200_000, 8192, "0.0008",  "0.004",  False),
    ("Azure OpenAI",   "gpt-4o-azure",                 AIModel.Capability.CHAT,      128_000, 4096, "0.0025",  "0.01",   False),
    ("Google Gemini",  "gemini-1.5-pro",               AIModel.Capability.CHAT,      1_000_000, 8192, "0.00125", "0.005", False),
    ("Google Gemini",  "gemini-1.5-flash",             AIModel.Capability.CHAT,      1_000_000, 8192, "0.000075", "0.0003", False),
    ("Local LLM (Ollama)", "llama-3.1-8b-instruct",    AIModel.Capability.CHAT,      8192,    2048, "0",        "0",      False),
]


# Feature → (default_model_name, fallback_model_names, budgets dict, prompt versions)
FEATURE_PLAN = {
    AIFeature.Code.DOUBT_SOLVER: dict(
        name="AI Doubt Solver",
        description="Real-time student doubt resolution via text, voice or image.",
        default="gpt-4o-mini",
        fallbacks=["claude-3-5-haiku-20241022", "gemini-1.5-flash"],
        rate_limit_per_minute=30,
        per_user_daily_quota=40,
        daily_request_budget=5_000,
        monthly_token_budget=20_000_000,
        monthly_cost_budget_usd="250.00",
        allowed_roles=["STUDENT", "TEACHER"],
        input_modes=["TEXT", "VOICE"],
        languages=["en", "hi"],
        exam_mode_block=True,
        prompt_versions=[
            ("v1 launch",  "DRAFT",
             "You are a patient tutor. Reply in 3 short bullets.",
             "Subject: {{subject}}\nQuestion: {{user_message}}"),
            ("v2 examples",  "PUBLISHED",
             "You are a friendly expert tutor for grades 6-12. Always give a worked example. Use simple language.",
             "Subject: {{subject}}\nTopic: {{topic}}\nGrade: {{grade}}\nQuestion: {{user_message}}\n\nReturn 1) direct answer  2) why  3) one worked example."),
        ],
    ),
    AIFeature.Code.STUDY_PLANNER: dict(
        name="AI Study Planner",
        description="Personalised exam-prep schedule based on goal, exam date and hours.",
        default="gpt-4o-mini",
        fallbacks=["claude-3-5-haiku-20241022"],
        rate_limit_per_minute=10,
        per_user_daily_quota=8,
        daily_request_budget=600,
        monthly_token_budget=6_000_000,
        monthly_cost_budget_usd="120.00",
        allowed_roles=["STUDENT", "TEACHER"],
        prompt_versions=[
            ("v1 planner", "PUBLISHED",
             "You are an expert exam coach. Always return a weekly schedule.",
             "Goal: {{goal}}\nExam date: {{exam_date}}\nLevel: {{current_level}}\nHours/day: {{hours_per_day}}\nSubjects: {{subjects}}"),
        ],
    ),
    AIFeature.Code.PRACTICE_QUIZ: dict(
        name="Practice Quiz Generator",
        description="Generates MCQ / coding / descriptive questions with answer keys.",
        default="gpt-4o-mini",
        fallbacks=["claude-3-5-haiku-20241022", "gemini-1.5-flash"],
        rate_limit_per_minute=20,
        per_user_daily_quota=15,
        daily_request_budget=1_500,
        monthly_token_budget=10_000_000,
        monthly_cost_budget_usd="200.00",
        allowed_roles=["TEACHER", "ADMIN"],
        exam_mode_block=True,
        prompt_versions=[
            ("v1 mcq", "DEPRECATED",
             "Return MCQs only.",
             "Subject: {{subject}}\nCount: {{count}}"),
            ("v2 mixed", "PUBLISHED",
             "You are an exam question setter. Output JSON only.",
             "Generate {{count}} {{difficulty}} questions on {{subject}} / {{topic}}.\nReturn JSON: {\"questions\":[{\"type\":\"MCQ\",\"q\":\"...\",\"options\":[...],\"answer\":\"...\",\"explanation\":\"...\"}]}"),
        ],
    ),
    AIFeature.Code.PERFORMANCE_INSIGHTS: dict(
        name="Performance Insights",
        description="Weak-area + strength + risk-band + predicted-score analysis.",
        default="gpt-4o-mini",
        fallbacks=["claude-3-5-haiku-20241022"],
        rate_limit_per_minute=15,
        per_user_daily_quota=10,
        daily_request_budget=800,
        monthly_token_budget=5_000_000,
        monthly_cost_budget_usd="100.00",
        allowed_roles=["STUDENT", "TEACHER", "ADMIN"],
        prompt_versions=[
            ("v1 insights", "PUBLISHED",
             "You are a learning analytics expert. Be concise and data-driven.",
             "Summary: {{student_summary}}\nPeriod: {{period}}"),
        ],
    ),
    AIFeature.Code.LEARNING_PATH: dict(
        name="AI Learning Path",
        description="Multi-week structured roadmap with weekly milestones.",
        default="gpt-4o",
        fallbacks=["claude-3-5-sonnet-20241022"],
        rate_limit_per_minute=6,
        per_user_daily_quota=4,
        daily_request_budget=300,
        monthly_token_budget=3_000_000,
        monthly_cost_budget_usd="150.00",
        allowed_roles=["STUDENT", "TEACHER"],
        prompt_versions=[
            ("v1 path", "PUBLISHED",
             "You are an experienced curriculum designer. Always output week-wise milestones.",
             "Target: {{target}}\nLevel: {{current_level}}\nWeeks: {{duration_weeks}}"),
        ],
    ),
    AIFeature.Code.ADAPTIVE_LEARNING: dict(
        name="Adaptive Learning Engine",
        description="Real-time difficulty calibration from mastery signals.",
        default="gpt-4o-mini",
        fallbacks=["gemini-1.5-flash"],
        rate_limit_per_minute=60,
        per_user_daily_quota=120,
        daily_request_budget=20_000,
        monthly_token_budget=15_000_000,
        monthly_cost_budget_usd="180.00",
        allowed_roles=["STUDENT"],
        prompt_versions=[
            ("v1 adaptive", "PUBLISHED",
             "You are an adaptive-learning agent. Recommend exactly one next task.",
             "Recent: {{recent_performance}}\nCurrent topic: {{current_topic}}"),
        ],
    ),
    AIFeature.Code.EXAM_RESULT_PLANNING: dict(
        name="Exam Result Planning",
        description="Post-exam improvement roadmap + weak-area remediation.",
        default="gpt-4o-mini",
        fallbacks=["claude-3-5-haiku-20241022"],
        rate_limit_per_minute=10,
        per_user_daily_quota=6,
        daily_request_budget=500,
        monthly_token_budget=4_000_000,
        monthly_cost_budget_usd="90.00",
        allowed_roles=["STUDENT", "TEACHER"],
        prompt_versions=[
            ("v1 result", "PUBLISHED",
             "You are an exam coach. Be specific about which chapters to revisit.",
             "Exam: {{exam_name}}\nScores: {{scores}}\nTarget: {{target_score}}\nWeak: {{weak_topics}}"),
        ],
    ),
}


# ---------------------------------------------------------------------------
class Command(BaseCommand):
    help = "Populate AI Governance & Operations with realistic demo data."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30,
                            help="How many days of usage history to synthesise.")
        parser.add_argument("--per-day", type=int, default=40,
                            help="Avg requests per day per feature.")
        parser.add_argument("--reset", action="store_true",
                            help="Wipe AIUsageLog/AIAuditLog/AICostTracking/AIFeedback first.")
        parser.add_argument("--no-students", action="store_true",
                            help="Skip student profile + learning path seeding.")

    @transaction.atomic
    def handle(self, *args, **opts):
        days = int(opts["days"])
        per_day = int(opts["per_day"])
        reset = bool(opts["reset"])

        if reset:
            AIFeedback.objects.all().delete()
            AIAuditLog.objects.all().delete()
            AIUsageLog.objects.all().delete()
            AICostTracking.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared usage/audit/cost/feedback tables."))

        provs   = self._seed_providers()
        models  = self._seed_models(provs)
        feats   = self._seed_features(models)
        self._seed_prompt_versions(feats)
        self._seed_usage(days=days, per_day=per_day, feats=feats, models=models, provs=provs)
        self._seed_feedback()
        if not opts["no_students"]:
            self._seed_student_profiles_and_paths(feats, models)

        self.stdout.write(self.style.SUCCESS(
            f"Populated AI Governance & Operations "
            f"({days}d × ~{per_day} req/day per feature)."
        ))

    # --- providers ---------------------------------------------------------
    def _seed_providers(self) -> dict[str, AIProvider]:
        out: dict[str, AIProvider] = {}
        for spec in PROVIDER_SPECS:
            obj, _ = AIProvider.objects.update_or_create(
                name=spec["name"], defaults=spec,
            )
            out[obj.name] = obj
            self.stdout.write(f"  provider  {obj.name:<22} status={obj.status}")
        return out

    # --- models ------------------------------------------------------------
    def _seed_models(self, provs: dict[str, AIProvider]) -> dict[str, AIModel]:
        out: dict[str, AIModel] = {}
        for (pname, name, cap, ctx, max_out, in_c, out_c, is_default) in MODEL_SPECS:
            obj, _ = AIModel.objects.update_or_create(
                provider=provs[pname], name=name,
                defaults=dict(
                    capability=cap, context_window=ctx, max_output_tokens=max_out,
                    input_cost_per_1k=Decimal(in_c), output_cost_per_1k=Decimal(out_c),
                    is_default_for_capability=is_default,
                    is_enabled=True,
                ),
            )
            out[name] = obj
        self.stdout.write(f"  models    {len(out)} total")
        return out

    # --- features ----------------------------------------------------------
    def _seed_features(self, models: dict[str, AIModel]) -> dict[str, AIFeature]:
        out: dict[str, AIFeature] = {}
        for code, plan in FEATURE_PLAN.items():
            default = models[plan["default"]]
            fallbacks = [models[n] for n in plan.get("fallbacks", []) if n in models]
            f, _ = AIFeature.objects.update_or_create(
                tenant=None, code=code,
                defaults=dict(
                    name=plan["name"],
                    description=plan["description"],
                    is_enabled=True,
                    default_model=default,
                    allowed_roles=plan.get("allowed_roles", []),
                    input_modes=plan.get("input_modes", ["TEXT"]),
                    languages=plan.get("languages", ["en"]),
                    rate_limit_per_minute=plan["rate_limit_per_minute"],
                    per_user_daily_quota=plan["per_user_daily_quota"],
                    daily_request_budget=plan["daily_request_budget"],
                    monthly_token_budget=plan["monthly_token_budget"],
                    monthly_cost_budget_usd=Decimal(plan["monthly_cost_budget_usd"]),
                    exam_mode_block=plan.get("exam_mode_block", False),
                    last_health_at=timezone.now(),
                    last_health_ok=True,
                ),
            )
            f.fallback_models.set(fallbacks)
            out[code] = f
        self.stdout.write(f"  features  {len(out)} total")
        return out

    # --- prompts -----------------------------------------------------------
    def _seed_prompt_versions(self, feats: dict[str, AIFeature]) -> None:
        for code, plan in FEATURE_PLAN.items():
            feature = feats[code]
            prompt, _ = AIPrompt.objects.update_or_create(
                tenant=None, name=f"{code.lower()}-main",
                defaults=dict(feature=feature, description=f"Main prompt for {feature.name}"),
            )
            latest_published: AIPromptVersion | None = None
            for i, (label, status, system_text, user_template) in enumerate(plan["prompt_versions"], start=1):
                pv, _ = AIPromptVersion.objects.update_or_create(
                    prompt=prompt, version=i,
                    defaults=dict(
                        status=status,
                        system_prompt=system_text,
                        user_template=user_template,
                        change_note=label,
                        published_at=timezone.now() if status == "PUBLISHED" else None,
                    ),
                )
                if status == "PUBLISHED":
                    latest_published = pv
            if latest_published:
                feature.active_prompt_version = latest_published
                feature.save(update_fields=["active_prompt_version"])
        self.stdout.write("  prompts   versions linked + active version set per feature")

    # --- usage logs --------------------------------------------------------
    def _seed_usage(self, *, days: int, per_day: int,
                    feats: dict[str, AIFeature], models: dict[str, AIModel],
                    provs: dict[str, AIProvider]) -> None:
        statuses = (
            (AIUsageLog.Status.SUCCESS, 0.94),
            (AIUsageLog.Status.FALLBACK, 0.03),
            (AIUsageLog.Status.RATE_LIMITED, 0.01),
            (AIUsageLog.Status.FAILED, 0.015),
            (AIUsageLog.Status.BLOCKED, 0.005),
        )

        usage_rows: list[AIUsageLog] = []
        audit_rows: list[AIAuditLog] = []
        cost_acc: dict[tuple, dict] = {}

        now = timezone.now()
        for day_offset in range(days):
            d = (now - timedelta(days=day_offset)).date()
            for code, feature in feats.items():
                # Vary daily volume to simulate realistic curves.
                day_volume = max(0, int(random.gauss(per_day, per_day * 0.3)))
                for _ in range(day_volume):
                    status = self._weighted_choice(statuses)
                    in_tok = random.randint(40, 800)
                    out_tok = random.randint(50, 1200) if status in (
                        AIUsageLog.Status.SUCCESS, AIUsageLog.Status.FALLBACK
                    ) else 0
                    model = feature.default_model
                    provider = model.provider
                    cost = Decimal(in_tok) / 1000 * model.input_cost_per_1k + \
                           Decimal(out_tok) / 1000 * model.output_cost_per_1k
                    latency = random.randint(150, 1800)
                    ts = timezone.make_aware(
                        timezone.datetime.combine(d, timezone.datetime.min.time())
                    ) + timedelta(minutes=random.randint(0, 1439))
                    rid = uuid.uuid4().hex
                    usage_rows.append(AIUsageLog(
                        request_id=rid, correlation_id="",
                        feature=feature, provider=provider, model=model,
                        prompt_version=feature.active_prompt_version,
                        user=None, user_role=random.choice(["STUDENT", "TEACHER"]),
                        status=status,
                        input_tokens=in_tok, output_tokens=out_tok,
                        total_tokens=in_tok + out_tok,
                        cost_usd=cost.quantize(Decimal("0.000001")),
                        latency_ms=latency, created_at=ts,
                    ))
                    audit_rows.append(AIAuditLog(
                        feature_code=code,
                        model_name=model.name, provider_name=provider.name,
                        prompt_text="[seed] system prompt + user message",
                        response_text="[seed] model response",
                        redacted_prompt="[seed] redacted prompt",
                        redacted_response="[seed] redacted response",
                        flagged=(status == AIUsageLog.Status.BLOCKED),
                        flag_reason="safety_blocked" if status == AIUsageLog.Status.BLOCKED else "",
                        created_at=ts,
                    ))
                    key = (None, d, feature.id, model.id)
                    bucket = cost_acc.setdefault(key, dict(
                        provider=provider, requests=0, failed_requests=0,
                        input_tokens=0, output_tokens=0, total_tokens=0,
                        cost_usd=Decimal("0"),
                    ))
                    bucket["requests"] += 1
                    if status in (AIUsageLog.Status.FAILED, AIUsageLog.Status.RATE_LIMITED,
                                  AIUsageLog.Status.BLOCKED):
                        bucket["failed_requests"] += 1
                    bucket["input_tokens"]  += in_tok
                    bucket["output_tokens"] += out_tok
                    bucket["total_tokens"]  += in_tok + out_tok
                    bucket["cost_usd"] += cost

        AIUsageLog.objects.bulk_create(usage_rows, batch_size=500)
        AIAuditLog.objects.bulk_create(audit_rows, batch_size=500)

        for (tenant_id, d, feature_id, model_id), b in cost_acc.items():
            AICostTracking.objects.update_or_create(
                tenant_id=tenant_id, date=d, feature_id=feature_id, model_id=model_id,
                defaults=dict(
                    provider=b["provider"],
                    requests=b["requests"],
                    failed_requests=b["failed_requests"],
                    input_tokens=b["input_tokens"],
                    output_tokens=b["output_tokens"],
                    total_tokens=b["total_tokens"],
                    cost_usd=b["cost_usd"].quantize(Decimal("0.000001")),
                ),
            )

        self.stdout.write(
            f"  usage     {len(usage_rows)} logs, {len(cost_acc)} cost-roll-up rows"
        )

    def _weighted_choice(self, choices):
        r = random.random()
        upto = 0.0
        for value, weight in choices:
            upto += weight
            if r < upto:
                return value
        return choices[-1][0]

    # --- feedback ----------------------------------------------------------
    def _seed_feedback(self) -> None:
        recent = list(AIUsageLog.objects.filter(
            status=AIUsageLog.Status.SUCCESS,
        ).order_by("-created_at")[:200])
        if not recent:
            return
        sample_size = min(25, len(recent))
        for row in random.sample(recent, sample_size):
            verdict = random.choices(
                [AIFeedback.Verdict.UP, AIFeedback.Verdict.DOWN, AIFeedback.Verdict.NEUTRAL],
                weights=[0.7, 0.15, 0.15], k=1,
            )[0]
            AIFeedback.objects.create(
                usage=row,
                verdict=verdict,
                rating=random.randint(3, 5) if verdict == AIFeedback.Verdict.UP else random.randint(1, 3),
                comment=random.choice([
                    "Very helpful, thanks!",
                    "Could use more examples.",
                    "Explanation was clear.",
                    "Slow but correct.",
                    "Loved the worked example.",
                    "",
                ]),
            )
        self.stdout.write(f"  feedback  {sample_size} rows")

    # --- student profiles + learning paths --------------------------------
    def _seed_student_profiles_and_paths(self, feats, models) -> None:
        try:
            from accounts.models import Student  # type: ignore
        except Exception:
            self.stdout.write("  students  skipped (accounts.Student not importable)")
            return

        students = list(Student.objects.all()[:25])
        if not students:
            self.stdout.write("  students  skipped (no Student rows)")
            return

        path_feature = feats[AIFeature.Code.LEARNING_PATH]
        model = path_feature.default_model

        prof_count = 0
        path_count = 0
        for s in students:
            mastery = {f"topic-{i}": round(random.uniform(0.2, 0.95), 2) for i in range(1, 6)}
            weak = [t for t, m in mastery.items() if m < 0.5]
            strong = [t for t, m in mastery.items() if m > 0.8]
            risk = random.choice([AIStudentProfile.RiskBand.TOP,
                                  AIStudentProfile.RiskBand.SAFE,
                                  AIStudentProfile.RiskBand.MEDIUM,
                                  AIStudentProfile.RiskBand.HIGH])
            AIStudentProfile.objects.update_or_create(
                student=s,
                defaults=dict(
                    mastery_map=mastery,
                    weak_topics=weak,
                    strong_topics=strong,
                    learning_style=random.choice(["visual", "auditory", "kinesthetic"]),
                    preferred_language="en",
                    avg_session_minutes=random.uniform(15, 75),
                    engagement_score=random.uniform(0.3, 0.95),
                    consistency_score=random.uniform(0.4, 0.95),
                    predicted_score=random.uniform(55, 92),
                    prediction_confidence=random.uniform(0.6, 0.95),
                    risk_band=risk,
                    last_active_at=timezone.now() - timedelta(days=random.randint(0, 7)),
                ),
            )
            prof_count += 1

            # 0..2 learning paths per student.
            for _ in range(random.randint(0, 2)):
                AILearningPath.objects.create(
                    student=s,
                    kind=random.choice([AILearningPath.Kind.LEARNING_PATH,
                                        AILearningPath.Kind.STUDY_PLAN,
                                        AILearningPath.Kind.EXAM_PLAN]),
                    status=random.choice([AILearningPath.Status.ACTIVE,
                                          AILearningPath.Status.DRAFT,
                                          AILearningPath.Status.COMPLETED]),
                    title=random.choice([
                        "JEE Physics Bootcamp", "NEET Biology Sprint",
                        "Math Class-10 Foundation", "English Grammar Roadmap",
                        "Chemistry Inorganic Recovery Plan",
                    ]),
                    summary="Auto-generated demo plan covering weak topics and revision.",
                    plan={
                        "weeks": [
                            {"week": w, "topics": random.sample(list(mastery.keys()), 2),
                             "hours": random.randint(5, 12)}
                            for w in range(1, 5)
                        ],
                    },
                    planned_minutes=random.randint(600, 1800),
                    actual_minutes=random.randint(200, 1500),
                    completion_percent=round(random.uniform(10, 95), 2),
                    adherence_percent=round(random.uniform(40, 98), 2),
                    generated_by_model=model,
                    generated_by_prompt_version=path_feature.active_prompt_version,
                    confidence=round(random.uniform(0.6, 0.95), 3),
                )
                path_count += 1
        self.stdout.write(f"  students  {prof_count} profiles, {path_count} learning paths")
