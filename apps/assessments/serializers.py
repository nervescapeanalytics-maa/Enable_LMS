"""Assessments - Serializers"""
from rest_framework import serializers
from assessments.models import (
    Test, TestSection, Question, TestAttempt,
    TestAttemptAnswer, TestFeedback, OfflineTestMarks,
)


class TestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = [
            'id', 'tenant', 'test_code', 'title', 'test_type', 'status',
            'total_marks', 'total_questions', 'total_duration_minutes',
            'start_datetime', 'end_datetime', 'created_at',
        ]
        read_only_fields = ('id', 'created_at')


class TestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class TestSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSection
        fields = '__all__'
        read_only_fields = ('id',)


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class TestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttempt
        fields = '__all__'
        read_only_fields = ('id',)


class TestAttemptAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttemptAnswer
        fields = '__all__'
        read_only_fields = ('id',)


class TestFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestFeedback
        fields = '__all__'
        read_only_fields = ('id',)


class OfflineTestMarksSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineTestMarks
        fields = '__all__'
        read_only_fields = ('id',)
