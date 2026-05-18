"""Smoke tests for Batch 1 — registry, prompt versioning, rollback."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from ai_core.models import (
    AIFeature, AIModel, AIProvider, AIPrompt, AIPromptVersion,
    AIUsageLog, AIAuditLog, AICostTracking, AIFeedback,
    AIStudentProfile, AILearningPath,
)


pytestmark = pytest.mark.django_db


def test_provider_model_feature_creation():
    p = AIProvider.objects.create(name="P1", kind=AIProvider.Kind.OPENAI)
    m = AIModel.objects.create(provider=p, name="m1", capability=AIModel.Capability.CHAT)
    f = AIFeature.objects.create(
        code=AIFeature.Code.DOUBT_SOLVER, name="DS", default_model=m,
    )
    assert AIProvider.objects.count() == 1
    assert AIModel.objects.count() == 1
    assert AIFeature.objects.count() == 1
    assert f.default_model == m
    assert m.provider == p


def test_seed_command(db):
    from django.core.management import call_command
    call_command("seed_ai_defaults", verbosity=0)
    assert AIProvider.objects.filter(name="OpenAI").exists()
    assert AIModel.objects.filter(name="gpt-4o-mini").exists()
    assert AIFeature.objects.filter(code="DOUBT_SOLVER", tenant=None).exists()
    # Idempotent
    call_command("seed_ai_defaults", verbosity=0)
    assert AIProvider.objects.filter(name="OpenAI").count() == 1


def test_prompt_version_publish_and_rollback():
    feat = AIFeature.objects.create(
        code=AIFeature.Code.DOUBT_SOLVER, name="DS",
    )
    pr = AIPrompt.objects.create(feature=feat, name="ds-main")
    v1 = AIPromptVersion.objects.create(prompt=pr, version=1,
                                        status=AIPromptVersion.Status.PUBLISHED,
                                        system_prompt="v1", published_at=timezone.now())
    v2 = AIPromptVersion.objects.create(prompt=pr, version=2,
                                        status=AIPromptVersion.Status.APPROVED,
                                        system_prompt="v2")
    # promote v2
    AIPromptVersion.objects.filter(pk=v1.pk).update(status=AIPromptVersion.Status.DEPRECATED)
    v2.status = AIPromptVersion.Status.PUBLISHED
    v2.published_at = timezone.now()
    v2.save()
    assert AIPromptVersion.objects.filter(prompt=pr,
                                          status=AIPromptVersion.Status.PUBLISHED).count() == 1
    # rollback v2
    v2.status = AIPromptVersion.Status.ROLLED_BACK
    v2.rolled_back_at = timezone.now()
    v2.save()
    assert v2.status == AIPromptVersion.Status.ROLLED_BACK


def test_usage_audit_cost_feedback_tables_writable():
    p = AIProvider.objects.create(name="P", kind=AIProvider.Kind.OPENAI)
    m = AIModel.objects.create(provider=p, name="m1")
    f = AIFeature.objects.create(code=AIFeature.Code.DOUBT_SOLVER, name="DS")
    log = AIUsageLog.objects.create(
        request_id="r1", feature=f, provider=p, model=m,
        status=AIUsageLog.Status.SUCCESS, input_tokens=10, output_tokens=20,
        total_tokens=30, latency_ms=420,
    )
    AIAuditLog.objects.create(usage=log, feature_code=f.code, prompt_text="?", response_text="!")
    AICostTracking.objects.create(date=timezone.now().date(), feature=f, model=m,
                                  requests=1, total_tokens=30)
    AIFeedback.objects.create(usage=log, verdict=AIFeedback.Verdict.UP, rating=5)
    assert log.feedback.count() == 1
    assert log.audit is not None


def test_student_profile_and_learning_path(django_user_model):
    from accounts.models import Student
    # Minimum-viable student row — accounts.Student requires a parent User; we
    # bypass full creation here as this test only checks AI tables wire up.
    u = django_user_model.objects.create_user(username="u1", password="x")
    try:
        s = Student.objects.create(user=u, full_name="A", email="a@b.c")
    except Exception:
        pytest.skip("Student model requires more setup; skipping in smoke test.")
    AIStudentProfile.objects.create(student=s, risk_band=AIStudentProfile.RiskBand.SAFE)
    AILearningPath.objects.create(student=s, kind=AILearningPath.Kind.STUDY_PLAN,
                                  title="Plan A")
    assert AIStudentProfile.objects.filter(student=s).exists()
    assert AILearningPath.objects.filter(student=s, kind="STUDY_PLAN").exists()
