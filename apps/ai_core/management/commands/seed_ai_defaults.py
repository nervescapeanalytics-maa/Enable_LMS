"""
Seed default AI providers, models and features.

Idempotent — safe to re-run. Does NOT publish or enable features; admins must
opt-in via /admin/ai_core/aifeature/. Does NOT store any API keys.

Usage:
    python manage.py seed_ai_defaults
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from ai_core.models import AIFeature, AIModel, AIProvider


PROVIDERS = [
    dict(name="OpenAI", kind=AIProvider.Kind.OPENAI, base_url="https://api.openai.com/v1",
         priority=10, weight=1),
    dict(name="Anthropic", kind=AIProvider.Kind.ANTHROPIC, base_url="https://api.anthropic.com/v1",
         priority=20, weight=1),
    dict(name="Azure OpenAI", kind=AIProvider.Kind.AZURE_OPENAI, base_url="",
         priority=15, weight=1),
    dict(name="Google Gemini", kind=AIProvider.Kind.GOOGLE,
         base_url="https://generativelanguage.googleapis.com/v1beta",
         priority=30, weight=1),
    dict(name="Local LLM", kind=AIProvider.Kind.LOCAL, base_url="http://localhost:11434/v1",
         priority=90, weight=1, is_enabled=False),
]

# (provider_name, model_name, capability, ctx, max_out, in_cost, out_cost, default_for_cap)
MODELS = [
    # OpenAI
    ("OpenAI", "gpt-4o", AIModel.Capability.CHAT, 128_000, 4096, "0.0025", "0.01", False),
    ("OpenAI", "gpt-4o-mini", AIModel.Capability.CHAT, 128_000, 4096, "0.00015", "0.0006", True),
    ("OpenAI", "text-embedding-3-large", AIModel.Capability.EMBEDDING, 8192, 0, "0.00013", "0", True),
    ("OpenAI", "whisper-1", AIModel.Capability.STT, 0, 0, "0.006", "0", True),
    ("OpenAI", "tts-1", AIModel.Capability.TTS, 0, 0, "0.015", "0", True),
    # Anthropic
    ("Anthropic", "claude-3-5-sonnet-20241022", AIModel.Capability.CHAT, 200_000, 8192, "0.003", "0.015", False),
    ("Anthropic", "claude-3-5-haiku-20241022", AIModel.Capability.CHAT, 200_000, 8192, "0.0008", "0.004", False),
    # Gemini
    ("Google Gemini", "gemini-1.5-pro", AIModel.Capability.CHAT, 1_000_000, 8192, "0.00125", "0.005", False),
    ("Google Gemini", "gemini-1.5-flash", AIModel.Capability.CHAT, 1_000_000, 8192, "0.000075", "0.0003", False),
    # Local
    ("Local LLM", "llama-3.1-8b-instruct", AIModel.Capability.CHAT, 8192, 2048, "0", "0", False),
]

FEATURES = [
    dict(code=AIFeature.Code.DOUBT_SOLVER, name="AI Doubt Solver",
         description="Real-time student doubt resolution via text / voice / image.",
         allowed_roles=["STUDENT", "TEACHER"], input_modes=["TEXT"], languages=["en", "hi"],
         conversation_memory_enabled=True, teacher_escalation_enabled=True,
         exam_mode_block=True),
    dict(code=AIFeature.Code.STUDY_PLANNER, name="AI Study Planner",
         description="Generates personalised study plans based on syllabus, exam date, performance.",
         allowed_roles=["STUDENT", "TEACHER"], exam_mode_block=False),
    dict(code=AIFeature.Code.PRACTICE_QUIZ, name="Practice Quiz Generator",
         description="Generates MCQ / coding / descriptive questions with auto-evaluation.",
         allowed_roles=["TEACHER", "ADMIN"], exam_mode_block=True),
    dict(code=AIFeature.Code.PERFORMANCE_INSIGHTS, name="Performance Insights",
         description="Weak-area, strength, risk-band, predicted-score analytics.",
         allowed_roles=["STUDENT", "TEACHER", "ADMIN"], exam_mode_block=False),
    dict(code=AIFeature.Code.LEARNING_PATH, name="AI Learning Path",
         description="Recommendation engine over previous learning + skill gaps.",
         allowed_roles=["STUDENT", "TEACHER"], exam_mode_block=False),
    dict(code=AIFeature.Code.ADAPTIVE_LEARNING, name="Adaptive Learning Engine",
         description="Continuous difficulty adjustment from mastery signals.",
         allowed_roles=["STUDENT"], exam_mode_block=False),
    dict(code=AIFeature.Code.EXAM_RESULT_PLANNING, name="Exam Result Planning",
         description="Improvement roadmap + target marks + revision schedule.",
         allowed_roles=["STUDENT", "TEACHER"], exam_mode_block=False),
]


class Command(BaseCommand):
    help = "Seed default AI providers / models / global feature rows."

    @transaction.atomic
    def handle(self, *args, **opts):
        # Providers
        prov_map = {}
        for spec in PROVIDERS:
            obj, created = AIProvider.objects.get_or_create(
                name=spec["name"], defaults=spec,
            )
            prov_map[obj.name] = obj
            self.stdout.write(("+ " if created else "= ") + f"provider {obj.name}")

        # Models
        for (prov_name, name, cap, ctx, max_out, in_c, out_c, is_default) in MODELS:
            obj, created = AIModel.objects.get_or_create(
                provider=prov_map[prov_name], name=name,
                defaults=dict(
                    capability=cap, context_window=ctx, max_output_tokens=max_out,
                    input_cost_per_1k=Decimal(in_c), output_cost_per_1k=Decimal(out_c),
                    is_default_for_capability=is_default,
                ),
            )
            self.stdout.write(("+ " if created else "= ") + f"model {prov_name}/{name}")

        # Features (tenant=NULL = global defaults)
        default_model = AIModel.objects.filter(name="gpt-4o-mini").first()
        for spec in FEATURES:
            obj, created = AIFeature.objects.get_or_create(
                tenant=None, code=spec["code"],
                defaults=dict(default_model=default_model, **spec),
            )
            self.stdout.write(("+ " if created else "= ") + f"feature GLOBAL:{obj.code}")

        self.stdout.write(self.style.SUCCESS("AI defaults seeded."))
