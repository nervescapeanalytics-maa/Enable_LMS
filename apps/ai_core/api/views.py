"""DRF endpoints for AI features.

Each endpoint:
  1. Validates input via a serializer
  2. Delegates to the matching `ai_core.services` function
  3. Converts gateway exceptions to structured HTTP responses
"""
from __future__ import annotations

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..gateway import AIGatewayError
from ..models import AIFeedback, AIUsageLog
from ..compliance.export import export_user_ai_data, delete_user_ai_data
from ..services import (
    adaptive_learning as svc_adaptive,
    doubt_solver as svc_doubt,
    exam_result_planning as svc_exam,
    learning_path as svc_path,
    performance_insights as svc_perf,
    practice_quiz as svc_quiz,
    study_planner as svc_plan,
)
from . import serializers as ser

logger = logging.getLogger(__name__)


def _client_ip(request) -> str:
    xf = request.META.get("HTTP_X_FORWARDED_FOR")
    if xf:
        return xf.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _tenant_id(request):
    user = getattr(request, "user", None)
    return getattr(user, "tenant_id", None) if user else None


def _run(handler, request, serializer_cls):
    s = serializer_cls(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        data = handler(
            user=request.user if request.user.is_authenticated else None,
            tenant_id=_tenant_id(request),
            **s.validated_data,
        )
        return Response(data, status=status.HTTP_200_OK)
    except AIGatewayError as exc:
        return Response(exc.to_dict(), status=exc.http_status)
    except ValueError as exc:
        return Response({"error": "validation_error", "message": str(exc)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("ai_core api unexpected error")
        return Response({"error": "internal_error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class _BaseAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]


class DoubtSolveView(_BaseAIView):
    def post(self, request):
        return _run(svc_doubt.solve_doubt, request, ser.DoubtSolveSerializer)


class StudyPlannerView(_BaseAIView):
    def post(self, request):
        return _run(svc_plan.generate_plan, request, ser.StudyPlanSerializer)


class PracticeQuizView(_BaseAIView):
    def post(self, request):
        return _run(svc_quiz.generate_quiz, request, ser.PracticeQuizSerializer)


class PerformanceInsightsView(_BaseAIView):
    def post(self, request):
        return _run(svc_perf.analyze_performance, request, ser.PerformanceInsightsSerializer)


class LearningPathView(_BaseAIView):
    def post(self, request):
        return _run(svc_path.generate_learning_path, request, ser.LearningPathSerializer)


class AdaptiveLearningView(_BaseAIView):
    def post(self, request):
        return _run(svc_adaptive.next_step, request, ser.AdaptiveLearningSerializer)


class ExamResultPlanningView(_BaseAIView):
    def post(self, request):
        return _run(svc_exam.plan_from_result, request, ser.ExamResultPlanningSerializer)


class FeedbackView(_BaseAIView):
    """POST a thumbs-up/down + optional rating + comment for a usage row."""

    def post(self, request):
        s = ser.FeedbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        rid = s.validated_data["request_id"]
        try:
            usage = AIUsageLog.objects.get(request_id=rid)
        except AIUsageLog.DoesNotExist:
            return Response({"error": "usage_not_found"},
                            status=status.HTTP_404_NOT_FOUND)
        fb = AIFeedback.objects.create(
            tenant_id=getattr(usage, "tenant_id", None),
            usage=usage,
            user=request.user if request.user.is_authenticated else None,
            verdict=s.validated_data["verdict"],
            rating=s.validated_data.get("rating"),
            comment=s.validated_data.get("comment", ""),
        )
        return Response({"id": str(fb.id), "ok": True}, status=status.HTTP_201_CREATED)


class FeatureCatalogView(_BaseAIView):
    def get(self, request):
        from ..models import AIFeature
        tid = _tenant_id(request)
        qs = AIFeature.objects.filter(is_enabled=True)
        if tid:
            qs = qs.filter(tenant_id=tid) | qs.filter(tenant__isnull=True)
        seen = set()
        out = []
        for f in qs.order_by("code"):
            if f.code in seen:
                continue
            seen.add(f.code)
            out.append({
                "code": f.code,
                "name": f.name,
                "is_enabled": f.is_enabled,
                "rate_limit_per_minute": f.rate_limit_per_minute,
                "per_user_daily_quota": f.per_user_daily_quota,
            })
        return Response({"features": out})


class MyAIDataExportView(_BaseAIView):
    """GDPR / FERPA — caller exports all AI history about themselves."""

    def get(self, request):
        data = export_user_ai_data(request.user)
        return Response(data)


class MyAIDataDeleteView(_BaseAIView):
    """GDPR right-to-erasure — caller deletes their own AI history."""

    def delete(self, request):
        counts = delete_user_ai_data(request.user)
        return Response({"deleted": counts})

