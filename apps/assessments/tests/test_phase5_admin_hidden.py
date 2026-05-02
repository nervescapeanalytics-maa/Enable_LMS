"""
Phase 5 — Feature 4: Verify TestAttempt and TestAttemptAnswer are NOT
registered with the Django admin site.
"""
from django.contrib import admin

from assessments.models import TestAttempt, TestAttemptAnswer


def test_test_attempt_not_in_admin():
    assert TestAttempt not in admin.site._registry


def test_test_attempt_answer_not_in_admin():
    assert TestAttemptAnswer not in admin.site._registry
