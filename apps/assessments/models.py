"""
LMS Enterprise - Assessments & Tests Models
Converted from legacy MS SQL tables: Test, Question, Question_Sub, Test_Pass,
Hold_Test, Hold_Test_Child, Test_Feedback, Test_Time_Manage, Test_Subject, offline_test_marks
"""
import uuid
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Test / Exam
# ---------------------------------------------------------------------------
class Test(models.Model):
    """Assessment / examination. Replaces legacy [Test] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tests')

    # Identity
    test_code = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    # Classification
    class TestType(models.TextChoices):
        PRACTICE = 'PRACTICE', 'Practice'
        MOCK_EXAM = 'MOCK_EXAM', 'Mock Exam'
        CHAPTER_TEST = 'CHAPTER_TEST', 'Chapter Test'
        UNIT_TEST = 'UNIT_TEST', 'Unit Test'
        WEEKLY = 'WEEKLY', 'Weekly Test'
        MONTHLY = 'MONTHLY', 'Monthly Test'
        FINAL = 'FINAL', 'Final Exam'
        SCHOLARSHIP = 'SCHOLARSHIP', 'Scholarship Test'
        DIAGNOSTIC = 'DIAGNOSTIC', 'Diagnostic'
        CUSTOM = 'CUSTOM', 'Custom'

    test_type = models.CharField(max_length=20, choices=TestType.choices, default=TestType.PRACTICE)

    class ExamTarget(models.TextChoices):
        JEE_MAINS = 'JEE_MAINS', 'JEE Mains'
        JEE_ADVANCED = 'JEE_ADVANCED', 'JEE Advanced'
        NEET = 'NEET', 'NEET'
        BOARDS = 'BOARDS', 'Boards'
        OLYMPIAD = 'OLYMPIAD', 'Olympiad'
        GENERAL = 'GENERAL', 'General'

    exam_target = models.CharField(max_length=15, choices=ExamTarget.choices, default=ExamTarget.GENERAL)

    class DifficultyLevel(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MEDIUM = 'MEDIUM', 'Medium'
        HARD = 'HARD', 'Hard'
        MIXED = 'MIXED', 'Mixed'

    difficulty_level = models.CharField(max_length=10, choices=DifficultyLevel.choices, default=DifficultyLevel.MEDIUM)

    # Academic Link
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('academics.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True)

    # Timing & Schedule
    total_duration_minutes = models.IntegerField(default=60)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    late_submission_allowed = models.BooleanField(default=False)
    late_submission_penalty_percent = models.IntegerField(default=0)
    buffer_time_minutes = models.IntegerField(default=0)
    show_timer = models.BooleanField(default=True)

    # Scoring
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    passing_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    passing_percent = models.DecimalField(max_digits=5, decimal_places=2, default=33.00)
    positive_marks_per_question = models.DecimalField(max_digits=5, decimal_places=2, default=4)
    negative_marks_per_question = models.DecimalField(max_digits=5, decimal_places=2, default=-1)
    partial_marking = models.BooleanField(default=False)

    # Access Rules
    max_attempts = models.IntegerField(default=1)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    allow_review = models.BooleanField(default=True)
    allow_backward = models.BooleanField(default=True)

    class AccessMode(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        BATCH_ONLY = 'BATCH_ONLY', 'Batch Only'
        PASSWORD = 'PASSWORD', 'Password Protected'
        SCHEDULED = 'SCHEDULED', 'Scheduled'

    access_mode = models.CharField(max_length=15, choices=AccessMode.choices, default=AccessMode.BATCH_ONLY)
    access_password = models.CharField(max_length=255, null=True, blank=True)

    # Results
    class ResultMode(models.TextChoices):
        IMMEDIATE = 'IMMEDIATE', 'Immediate'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        MANUAL = 'MANUAL', 'Manual Release'

    result_display_mode = models.CharField(max_length=15, choices=ResultMode.choices, default=ResultMode.IMMEDIATE)
    result_release_datetime = models.DateTimeField(null=True, blank=True)
    show_correct_answers = models.BooleanField(default=True)
    show_explanations = models.BooleanField(default=True)
    show_rank = models.BooleanField(default=True)
    show_percentile = models.BooleanField(default=True)

    # Proctoring
    enable_proctoring = models.BooleanField(default=False)
    prevent_tab_switch = models.BooleanField(default=True)
    max_tab_switches = models.IntegerField(default=3)
    prevent_copy_paste = models.BooleanField(default=True)
    prevent_screenshot = models.BooleanField(default=True)
    webcam_required = models.BooleanField(default=False)
    full_screen_required = models.BooleanField(default=False)

    # Lifecycle
    class TestStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        ARCHIVED = 'ARCHIVED', 'Archived'
        CANCELLED = 'CANCELLED', 'Cancelled'

    status = models.CharField(max_length=15, choices=TestStatus.choices, default=TestStatus.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.UUIDField(null=True, blank=True)

    created_by = models.UUIDField(null=True, blank=True)
    created_by_type = models.CharField(max_length=10, null=True, blank=True)
    teacher = models.ForeignKey('accounts.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='tests')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    # Total question count (denormalized)
    total_questions = models.IntegerField(default=0)

    # Extensions
    test_meta = models.JSONField(null=True, blank=True)
    ext_test_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_test_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_test_3 = models.JSONField(null=True, blank=True)
    ext_test_4 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ext_test_5 = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'tests'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'test_code'], name='uq_test_code_per_tenant'),
        ]
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_test_status'),
            models.Index(fields=['tenant', 'test_type'], name='idx_test_type'),
            models.Index(fields=['tenant', 'start_datetime'], name='idx_test_schedule'),
        ]

    def __str__(self):
        return f"{self.test_code} - {self.title}"


# ---------------------------------------------------------------------------
# Test Section (for multi-subject tests like JEE)
# ---------------------------------------------------------------------------
class TestSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='sections')
    section_name = models.CharField(max_length=255)
    section_order = models.IntegerField(default=1)
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    mandatory_questions = models.IntegerField(default=0)
    max_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_minutes = models.IntegerField(null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'test_sections'
        ordering = ['section_order']


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------
class Question(models.Model):
    """Assessment question. Replaces legacy [Question] and [Question_Sub]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='questions')

    # Identity
    question_code = models.CharField(max_length=50, null=True, blank=True)

    # Content
    question_text = models.TextField()
    question_text_html = models.TextField(null=True, blank=True)
    question_image = models.URLField(max_length=500, null=True, blank=True)

    class QuestionType(models.TextChoices):
        MCQ_SINGLE = 'MCQ_SINGLE', 'Single Choice'
        MCQ_MULTI = 'MCQ_MULTI', 'Multiple Choice'
        NUMERICAL = 'NUMERICAL', 'Numerical Answer'
        TRUE_FALSE = 'TRUE_FALSE', 'True/False'
        FILL_BLANK = 'FILL_BLANK', 'Fill in the Blank'
        SUBJECTIVE = 'SUBJECTIVE', 'Subjective'
        MATRIX_MATCH = 'MATRIX_MATCH', 'Matrix Match'
        ASSERTION_REASON = 'ASSERTION_REASON', 'Assertion & Reason'
        COMPREHENSION = 'COMPREHENSION', 'Comprehension Based'

    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MCQ_SINGLE)

    class Difficulty(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MEDIUM = 'MEDIUM', 'Medium'
        HARD = 'HARD', 'Hard'

    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)

    # Options (for MCQ)
    option_a = models.TextField(null=True, blank=True)
    option_a_image = models.URLField(max_length=500, null=True, blank=True)
    option_b = models.TextField(null=True, blank=True)
    option_b_image = models.URLField(max_length=500, null=True, blank=True)
    option_c = models.TextField(null=True, blank=True)
    option_c_image = models.URLField(max_length=500, null=True, blank=True)
    option_d = models.TextField(null=True, blank=True)
    option_d_image = models.URLField(max_length=500, null=True, blank=True)
    option_e = models.TextField(null=True, blank=True)
    option_e_image = models.URLField(max_length=500, null=True, blank=True)

    # Answer
    correct_answer = models.CharField(max_length=100)
    correct_answer_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    numerical_tolerance = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    answer_explanation = models.TextField(null=True, blank=True)

    # Scoring
    positive_marks = models.DecimalField(max_digits=5, decimal_places=2, default=4)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=-1)
    partial_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Classification
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('academics.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('academics.Topic', on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Linked Tests
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name='questions')
    section = models.ForeignKey(TestSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question_order = models.IntegerField(default=1)

    # Parent question (for comprehension / paragraph-based)
    parent_question = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_questions'
    )

    # Stats (denormalized)
    total_attempts = models.IntegerField(default=0)
    correct_attempts = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_time_seconds = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Extensions
    question_meta = models.JSONField(null=True, blank=True)
    ext_question_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_question_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_question_3 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'questions'
        ordering = ['question_order']
        indexes = [
            models.Index(fields=['tenant', 'test'], name='idx_question_test'),
            models.Index(fields=['tenant', 'subject'], name='idx_question_subject'),
            models.Index(fields=['tenant', 'difficulty'], name='idx_question_difficulty'),
        ]

    def __str__(self):
        return f"Q{self.question_order}: {self.question_text[:60]}"


# ---------------------------------------------------------------------------
# Test Attempt (student taking a test)
# ---------------------------------------------------------------------------
class TestAttempt(models.Model):
    """Student test attempt. Replaces legacy [Test_Pass], [Hold_Test], [Test_Time_Manage]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='test_attempts')

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='test_attempts')
    attempt_number = models.IntegerField(default=1)

    # Timing
    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    remaining_time_seconds = models.IntegerField(null=True, blank=True)
    time_limit_reached = models.BooleanField(default=False)

    # Scoring
    total_questions = models.IntegerField(default=0)
    attempted = models.IntegerField(default=0)
    correct = models.IntegerField(default=0)
    incorrect = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    marked_for_review = models.IntegerField(default=0)

    raw_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Result(models.TextChoices):
        PASS = 'PASS', 'Pass'
        FAIL = 'FAIL', 'Fail'
        PENDING = 'PENDING', 'Pending Review'

    result = models.CharField(max_length=10, choices=Result.choices, null=True, blank=True)

    # Section-wise scores (JSON array)
    section_scores = models.JSONField(default=list, blank=True)

    # Status
    class AttemptStatus(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        AUTO_SUBMITTED = 'AUTO_SUBMITTED', 'Auto Submitted'
        EVALUATED = 'EVALUATED', 'Evaluated'
        CANCELLED = 'CANCELLED', 'Cancelled'

    status = models.CharField(max_length=15, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS)

    # Proctoring
    tab_switch_count = models.IntegerField(default=0)
    copy_paste_attempts = models.IntegerField(default=0)
    proctoring_violations = models.JSONField(default=list, blank=True)
    auto_terminated = models.BooleanField(default=False)
    termination_reason = models.CharField(max_length=500, null=True, blank=True)

    # Device
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device_id = models.UUIDField(null=True, blank=True)

    attempt_meta = models.JSONField(null=True, blank=True)
    ext_attempt_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_attempt_2 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'test_attempts'
        constraints = [
            models.UniqueConstraint(
                fields=['test', 'student', 'attempt_number'],
                name='uq_test_attempt'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'test', 'student'], name='idx_attempt_test_student'),
            models.Index(fields=['tenant', 'student', 'started_at'], name='idx_attempt_student_date'),
        ]


# ---------------------------------------------------------------------------
# Test Attempt Answer (per-question response)
# ---------------------------------------------------------------------------
class TestAttemptAnswer(models.Model):
    """Individual question answer in a test attempt. Replaces legacy [Hold_Test_Child]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    student_answer = models.CharField(max_length=500, null=True, blank=True)
    student_answer_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    student_answer_text = models.TextField(null=True, blank=True)

    class AnswerStatus(models.TextChoices):
        ANSWERED = 'ANSWERED', 'Answered'
        SKIPPED = 'SKIPPED', 'Skipped'
        MARKED_FOR_REVIEW = 'MARKED', 'Marked for Review'
        NOT_VISITED = 'NOT_VISITED', 'Not Visited'

    status = models.CharField(max_length=15, choices=AnswerStatus.choices, default=AnswerStatus.NOT_VISITED)

    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_spent_seconds = models.IntegerField(default=0)

    # Multi-visit tracking
    visit_count = models.IntegerField(default=0)
    answer_change_count = models.IntegerField(default=0)
    first_answered_at = models.DateTimeField(null=True, blank=True)
    last_answered_at = models.DateTimeField(null=True, blank=True)

    answer_meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'test_attempt_answers'
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question'],
                name='uq_attempt_question'
            ),
        ]


# ---------------------------------------------------------------------------
# Test Feedback
# ---------------------------------------------------------------------------
class TestFeedback(models.Model):
    """Student feedback for a test. Replaces legacy [Test_Feedback]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE)
    attempt = models.ForeignKey(TestAttempt, on_delete=models.SET_NULL, null=True, blank=True)

    overall_rating = models.IntegerField(default=0)
    difficulty_rating = models.IntegerField(default=0)
    clarity_rating = models.IntegerField(default=0)
    comments = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'test_feedbacks'


# ---------------------------------------------------------------------------
# Offline Test Marks
# ---------------------------------------------------------------------------
class OfflineTestMarks(models.Model):
    """Offline test marks. Replaces legacy [offline_test_marks]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='offline_marks')
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)

    test_name = models.CharField(max_length=500)
    test_date = models.DateField(null=True, blank=True)
    total_marks = models.DecimalField(max_digits=8, decimal_places=2)
    marks_obtained = models.DecimalField(max_digits=8, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    entered_by = models.UUIDField(null=True, blank=True)
    entered_at = models.DateTimeField(default=timezone.now)
    verified_by = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'offline_test_marks'
        verbose_name_plural = 'Offline test marks'
