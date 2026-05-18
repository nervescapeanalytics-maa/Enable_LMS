"""DRF serializers for the AI feature endpoints."""
from __future__ import annotations

from rest_framework import serializers


class DoubtSolveSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=2, max_length=4000)
    subject = serializers.CharField(required=False, allow_blank=True, default="")
    topic = serializers.CharField(required=False, allow_blank=True, default="")
    grade = serializers.CharField(required=False, allow_blank=True, default="")


class StudyPlanSerializer(serializers.Serializer):
    goal = serializers.CharField(min_length=2, max_length=400)
    exam_date = serializers.CharField(required=False, allow_blank=True, default="")
    current_level = serializers.CharField(required=False, allow_blank=True, default="")
    subjects = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    hours_per_day = serializers.IntegerField(required=False, default=2, min_value=1, max_value=18)


class PracticeQuizSerializer(serializers.Serializer):
    subject = serializers.CharField(min_length=1, max_length=120)
    topic = serializers.CharField(required=False, allow_blank=True, default="")
    difficulty = serializers.ChoiceField(
        choices=["easy", "medium", "hard"], default="medium", required=False,
    )
    count = serializers.IntegerField(required=False, default=5, min_value=1, max_value=25)
    question_types = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class PerformanceInsightsSerializer(serializers.Serializer):
    student_summary = serializers.DictField()
    period = serializers.CharField(required=False, allow_blank=True, default="last 30 days")


class LearningPathSerializer(serializers.Serializer):
    target = serializers.CharField(min_length=2, max_length=400)
    current_level = serializers.CharField(required=False, allow_blank=True, default="")
    duration_weeks = serializers.IntegerField(required=False, default=4, min_value=1, max_value=52)
    persist = serializers.BooleanField(required=False, default=False)


class AdaptiveLearningSerializer(serializers.Serializer):
    recent_performance = serializers.DictField()
    current_topic = serializers.CharField(required=False, allow_blank=True, default="")


class ExamResultPlanningSerializer(serializers.Serializer):
    exam_name = serializers.CharField(min_length=1, max_length=120)
    scores = serializers.DictField()
    target_score = serializers.FloatField(required=False, allow_null=True, default=None)
    weak_topics = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class FeedbackSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=64)
    verdict = serializers.ChoiceField(choices=["UP", "DOWN", "NEUTRAL"])
    rating = serializers.IntegerField(required=False, min_value=1, max_value=5, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
