"""
Exam authoring forms (Phase 2).

These are Django forms used by admin/staff to create and edit Tests, Sections
and Questions. Validation here guarantees that the data layer (Test, Question)
never receives bad input. The views layer delegates all field-level checks to
these forms and only handles RBAC + audit.
"""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from assessments.models import Test, Question, TestSection
from academics.models import Subject, Chapter, Topic, Batch


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestForm(forms.ModelForm):
    """Create / edit a Test (exam definition)."""

    class Meta:
        model = Test
        fields = [
            # Identity
            'test_code', 'title', 'description', 'instructions',
            # Classification
            'test_type', 'exam_target', 'difficulty_level',
            # Academic Link
            'subject', 'chapter', 'batch',
            # Timing
            'total_duration_minutes', 'start_datetime', 'end_datetime',
            'late_submission_allowed', 'late_submission_penalty_percent',
            'buffer_time_minutes', 'show_timer',
            # Scoring
            'total_marks', 'passing_marks', 'passing_percent',
            'positive_marks_per_question', 'negative_marks_per_question',
            'partial_marking',
            # Access rules
            'max_attempts', 'shuffle_questions', 'shuffle_options',
            'allow_review', 'allow_backward', 'access_mode', 'access_password',
            # Results
            'result_display_mode', 'result_release_datetime',
            'show_correct_answers', 'show_explanations',
            'show_rank', 'show_percentile',
            # Proctoring
            'enable_proctoring', 'prevent_tab_switch', 'max_tab_switches',
            'prevent_copy_paste', 'prevent_screenshot',
            'webcam_required', 'full_screen_required',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 4}),
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'result_release_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'access_password': forms.PasswordInput(render_value=True),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        # Scope FK querysets to tenant if provided
        if tenant is not None:
            self.fields['subject'].queryset = Subject.objects.filter(tenant=tenant)
            self.fields['chapter'].queryset = Chapter.objects.filter(tenant=tenant)
            self.fields['batch'].queryset = Batch.objects.filter(tenant=tenant)
        # Empty labels
        for fname in ('subject', 'chapter', 'batch'):
            self.fields[fname].empty_label = '— None —'
            self.fields[fname].required = False
        # Slim-down required toggles
        self.fields['description'].required = False
        self.fields['instructions'].required = False
        self.fields['access_password'].required = False
        self.fields['start_datetime'].required = False
        self.fields['end_datetime'].required = False
        self.fields['result_release_datetime'].required = False

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_datetime')
        end = cleaned.get('end_datetime')
        if start and end and end <= start:
            self.add_error('end_datetime', 'End must be after start.')

        access_mode = cleaned.get('access_mode')
        password = cleaned.get('access_password')
        if access_mode == Test.AccessMode.PASSWORD and not password:
            self.add_error('access_password', 'Password is required for password-protected access mode.')

        passing_percent = cleaned.get('passing_percent')
        if passing_percent is not None and not (0 <= passing_percent <= 100):
            self.add_error('passing_percent', 'Must be between 0 and 100.')

        duration = cleaned.get('total_duration_minutes')
        if duration is not None and duration <= 0:
            self.add_error('total_duration_minutes', 'Duration must be positive.')

        max_attempts = cleaned.get('max_attempts')
        if max_attempts is not None and max_attempts < 1:
            self.add_error('max_attempts', 'At least 1 attempt is required.')

        return cleaned


# ---------------------------------------------------------------------------
# TestSection
# ---------------------------------------------------------------------------

class TestSectionForm(forms.ModelForm):
    class Meta:
        model = TestSection
        fields = [
            'section_name', 'section_order', 'subject',
            'total_questions', 'mandatory_questions',
            'max_marks', 'duration_minutes', 'instructions',
        ]
        widgets = {'instructions': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is not None:
            self.fields['subject'].queryset = Subject.objects.filter(tenant=tenant)
        self.fields['subject'].empty_label = '— None —'
        self.fields['subject'].required = False
        self.fields['duration_minutes'].required = False
        self.fields['instructions'].required = False


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class QuestionForm(forms.ModelForm):
    """Create / edit a Question, attached to a Test (or floating in the bank)."""

    class Meta:
        model = Question
        fields = [
            'question_code', 'question_text', 'question_image',
            'question_type', 'difficulty',
            'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
            'correct_answer', 'correct_answer_value', 'numerical_tolerance',
            'answer_explanation',
            'positive_marks', 'negative_marks', 'partial_marks',
            'subject', 'chapter', 'topic', 'tags',
            'test', 'section', 'question_order',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
            'option_a': forms.Textarea(attrs={'rows': 1}),
            'option_b': forms.Textarea(attrs={'rows': 1}),
            'option_c': forms.Textarea(attrs={'rows': 1}),
            'option_d': forms.Textarea(attrs={'rows': 1}),
            'option_e': forms.Textarea(attrs={'rows': 1}),
            'answer_explanation': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.TextInput(attrs={'placeholder': 'comma,separated,tags'}),
        }

    def __init__(self, *args, tenant=None, default_test=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        if tenant is not None:
            self.fields['subject'].queryset = Subject.objects.filter(tenant=tenant)
            self.fields['chapter'].queryset = Chapter.objects.filter(tenant=tenant)
            self.fields['topic'].queryset = Topic.objects.filter(tenant=tenant)
            self.fields['test'].queryset = Test.objects.filter(tenant=tenant, is_deleted=False)
            self.fields['section'].queryset = TestSection.objects.filter(tenant=tenant)
        for fname in ('subject', 'chapter', 'topic', 'test', 'section'):
            self.fields[fname].empty_label = '— None —'
            self.fields[fname].required = False
        for fname in ('question_code', 'question_image', 'option_a', 'option_b',
                      'option_c', 'option_d', 'option_e', 'correct_answer_value',
                      'numerical_tolerance', 'answer_explanation', 'partial_marks'):
            self.fields[fname].required = False
        if default_test is not None:
            self.fields['test'].initial = default_test
            self.fields['section'].queryset = TestSection.objects.filter(test=default_test)

    def clean_tags(self):
        raw = self.cleaned_data.get('tags', [])
        # Accept either a comma-separated string OR an actual list
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(',') if t.strip()]
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        return []

    def clean(self):
        cleaned = super().clean()
        qtype = cleaned.get('question_type')
        correct = (cleaned.get('correct_answer') or '').strip()

        # MCQ_SINGLE: must have at least 2 options + correct must be one of the option letters
        if qtype == Question.QuestionType.MCQ_SINGLE:
            opts = {k: cleaned.get(f'option_{k.lower()}') for k in ['A', 'B', 'C', 'D', 'E']}
            filled = [k for k, v in opts.items() if v]
            if len(filled) < 2:
                self.add_error('option_b', 'At least 2 options are required for single-choice questions.')
            if correct.upper() not in filled:
                self.add_error('correct_answer',
                               f'Correct answer must be one of: {", ".join(filled) or "A,B,C,D"}.')

        elif qtype == Question.QuestionType.MCQ_MULTI:
            opts = {k: cleaned.get(f'option_{k.lower()}') for k in ['A', 'B', 'C', 'D', 'E']}
            filled = [k for k, v in opts.items() if v]
            if len(filled) < 2:
                self.add_error('option_b', 'At least 2 options are required for multi-choice questions.')
            answer_letters = {x.strip().upper() for x in correct.split(',') if x.strip()}
            if not answer_letters:
                self.add_error('correct_answer', 'Provide one or more correct option letters, e.g. "A,C".')
            elif not answer_letters.issubset(set(filled)):
                self.add_error('correct_answer',
                               f'Correct answers must be a subset of: {", ".join(filled)}.')

        elif qtype == Question.QuestionType.TRUE_FALSE:
            if correct.upper() not in ('TRUE', 'FALSE', 'T', 'F'):
                self.add_error('correct_answer', 'Correct answer must be TRUE or FALSE.')

        elif qtype == Question.QuestionType.NUMERICAL:
            if cleaned.get('correct_answer_value') is None and not correct:
                self.add_error('correct_answer_value', 'Numerical answer value is required.')

        elif qtype in (Question.QuestionType.FILL_BLANK, Question.QuestionType.SUBJECTIVE):
            if not correct:
                # subjective: store a model answer or rubric
                self.add_error('correct_answer',
                               'Provide a model answer / rubric for this question type.')

        positive = cleaned.get('positive_marks')
        if positive is not None and positive < 0:
            self.add_error('positive_marks', 'Positive marks cannot be negative.')

        return cleaned
