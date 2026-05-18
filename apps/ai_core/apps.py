from django.apps import AppConfig


class AiCoreConfig(AppConfig):
    """
    AI Governance + AI Operations.

    Central registry for AI features, providers, models, prompts, usage,
    audit, cost, feedback and learner personalisation. Every AI capability
    in the LMS routes through this layer.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_core"
    verbose_name = "AI Governance & Operations"
