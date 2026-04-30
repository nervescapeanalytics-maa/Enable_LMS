"""
LMS Enterprise - Academic Models
Subjects, Chapters, Topics, Batches, and related models.
Incorporates legacy MS SQL structures (Category, Groups, Session, Subject, Chapter, etc.)
converted to PostgreSQL-compatible Django models.
"""
import uuid
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Session (Academic Year)
# ---------------------------------------------------------------------------
class AcademicSession(models.Model):
    """Academic session/year - replaces legacy [session] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='academic_sessions')

    session_name = models.CharField(max_length=500, help_text="e.g. '2026-2027'")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'session'
        ordering = ['-start_date']
        verbose_name = 'Academic Session'
        verbose_name_plural = 'Academic Sessions'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'session_name'],
                name='uq_session_name_per_tenant'
            ),
        ]

    def __str__(self):
        return self.session_name


# ---------------------------------------------------------------------------
# Group / Category (Batch Classification)
# ---------------------------------------------------------------------------
class Group(models.Model):
    """Student group - replaces legacy [groups] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='groups')

    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'groups'
        ordering = ['name']
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'
        indexes = [
            models.Index(fields=['tenant', 'name'], name='idx_group_name'),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Test/Content category - replaces legacy [Category] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='categories')

    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='Active')
    show_in_student = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'category'
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['tenant', 'name'], name='idx_category_name'),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------
class Subject(models.Model):
    """Subject model - replaces legacy [Subject] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='subjects')

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, null=True, blank=True, help_text="e.g. PHY, CHE, MAT, BIO")
    description = models.TextField(null=True, blank=True)
    icon_url = models.URLField(max_length=500, null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)

    class SubjectType(models.TextChoices):
        PHYSICS = 'PHYSICS', 'Physics'
        CHEMISTRY = 'CHEMISTRY', 'Chemistry'
        MATHEMATICS = 'MATHEMATICS', 'Mathematics'
        BIOLOGY = 'BIOLOGY', 'Biology'
        OTHER = 'OTHER', 'Other'

    subject_type = models.CharField(max_length=20, choices=SubjectType.choices, null=True, blank=True)
    status = models.CharField(max_length=20, default='Active')
    display_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'subject'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['tenant', 'name'], name='idx_subject_name'),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Subject Section
# ---------------------------------------------------------------------------
class SubjectSection(models.Model):
    """Subject section - replaces legacy [Subject_Section] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='subject_sections')

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=5, default='Yes')

    created_at = models.DateTimeField(default=timezone.now)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'subject_sections'
        verbose_name = 'Subject Section'
        verbose_name_plural = 'Subject Sections'
        ordering = ['name']


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------
class Chapter(models.Model):
    """Chapter model - replaces legacy [chapter] table."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='chapters')

    session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='chapters')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='chapters')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')

    name = models.CharField(max_length=500)
    code = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    status = models.BooleanField(default=True)

    # Academic details
    class_level = models.CharField(max_length=5, null=True, blank=True, help_text="9, 10, 11, 12")
    weightage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_hours = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'chapter'
        ordering = ['subject', 'display_order', 'name']
        indexes = [
            models.Index(fields=['tenant', 'subject'], name='idx_chapter_subject'),
        ]

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


# ---------------------------------------------------------------------------
# Topic
# ---------------------------------------------------------------------------
class Topic(models.Model):
    """Topic within a chapter."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='topics')

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='topics')

    name = models.CharField(max_length=500)
    code = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    status = models.BooleanField(default=True)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'topics'
        ordering = ['chapter', 'display_order']
        indexes = [
            models.Index(fields=['tenant', 'chapter'], name='idx_topic_chapter'),
        ]

    def __str__(self):
        return f"{self.chapter.name} - {self.name}"


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------
class Batch(models.Model):
    """Student batch model for grouping."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='batches')

    code = models.CharField(max_length=50, help_text="e.g. 'JEE-2026-A'")
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')

    class_level = models.CharField(max_length=5, null=True, blank=True)

    class ExamTarget(models.TextChoices):
        JEE = 'JEE', 'JEE'
        NEET = 'NEET', 'NEET'
        BOTH = 'BOTH', 'Both'

    exam_target = models.CharField(max_length=10, choices=ExamTarget.choices, null=True, blank=True)

    max_students = models.IntegerField(default=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class BatchStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        COMPLETED = 'COMPLETED', 'Completed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    status = models.CharField(max_length=15, choices=BatchStatus.choices, default=BatchStatus.ACTIVE)

    # Relations
    teachers = models.ManyToManyField('accounts.Teacher', through='BatchTeacher', related_name='teaching_batches')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_data = models.JSONField(default=dict, blank=True)
    ext_string_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_json_1 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'batches'
        ordering = ['-created_at']
        verbose_name_plural = 'Batches'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='uq_batch_code_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_batch_status'),
            models.Index(fields=['tenant', 'exam_target'], name='idx_batch_exam'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Users(models.Model):
    """
    Primary student/user table — maps to legacy SQL Server 'users' table.
    Contains student profile data + batch enrollment in a single table.
    """

    # ── Primary key & tenant ──
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='users')

    # ── Legacy integer PK from SQL Server ──
    uid = models.IntegerField(null=True, blank=True, unique=True)

    # ── Student profile fields (from legacy SQL Server users table) ──
    name = models.CharField(max_length=50, null=True, blank=True)
    father_name = models.CharField('Father/Guardian Name', max_length=100, null=True, blank=True)
    dob = models.DateField('Date of Birth', null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True, choices=[('Male', 'Male'), ('Female', 'Female'), ('Others', 'Others')])
    phone = models.CharField('Phone (User/Password)', max_length=50, null=True, blank=True)
    phone1 = models.CharField('Father/Guardian Phone', max_length=10, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    userid = models.CharField(max_length=20, null=True, blank=True)
    photo = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    handicapped = models.CharField(max_length=100, null=True, blank=True, choices=[('Yes', 'Yes'), ('No', 'No')])
    other_school = models.CharField(max_length=200, null=True, blank=True)
    city_name = models.CharField('City/Village', max_length=500, null=True, blank=True)
    previous_class_marks = models.CharField('Previous Year Total Marks', max_length=100, null=True, blank=True)
    tps = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)

    # ── Legacy FK IDs (integer keys from SQL Server — not Django ForeignKeys) ──
    session_id = models.IntegerField(null=True, blank=True)
    cid = models.IntegerField(null=True, blank=True)
    school_id = models.IntegerField('School', null=True, blank=True)
    state_id = models.IntegerField('State', null=True, blank=True)
    city_id = models.IntegerField('District Name', null=True, blank=True)

    # ── Enrollment fields ──
    student_id = models.UUIDField(null=True, blank=True)
    enrolled_at = models.DateTimeField(default=timezone.now)
    enrolled_by = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    @property
    def full_name(self):
        return self.name or ''

    def __str__(self):
        return f"{self.name or 'User'} — {self.batch}" if self.batch_id else (self.name or str(self.id))


class BatchTeacher(models.Model):
    """Many-to-many between Batch and Teacher."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='batch_teachers')
    teacher = models.ForeignKey('accounts.Teacher', on_delete=models.CASCADE, related_name='teacher_batches')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'batch_teachers'
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        constraints = [
            models.UniqueConstraint(fields=['batch', 'teacher', 'subject'], name='uq_batch_teacher_subject'),
        ]


# ---------------------------------------------------------------------------
# Language Master (from legacy)
# ---------------------------------------------------------------------------
class Language(models.Model):
    """Language master - replaces legacy [language_master]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'languages'

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Location Models (from legacy State, City tables)
# ---------------------------------------------------------------------------
class State(models.Model):
    """Indian states - replaces legacy [State]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'state'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_state_name'),
        ]

    def __str__(self):
        return self.name


class City(models.Model):
    """Cities - replaces legacy [City]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')

    class Meta:
        db_table = 'city'
        ordering = ['name']
        verbose_name = 'City'
        verbose_name_plural = 'Cities'

    def __str__(self):
        return f"{self.name}, {self.state.name}"


# ---------------------------------------------------------------------------
# Religion (from legacy)
# ---------------------------------------------------------------------------
class Religion(models.Model):
    """Religion master - replaces legacy [religion]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=5, default='Yes')

    class Meta:
        db_table = 'religions'
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# School (from legacy)
# ---------------------------------------------------------------------------
class School(models.Model):
    """School/Institution - replaces legacy [school]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='schools', null=True, blank=True)

    name = models.CharField(max_length=300)
    religion = models.ForeignKey(Religion, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    city_name = models.CharField(max_length=100, null=True, blank=True)

    class SchoolType(models.TextChoices):
        GOVERNMENT = 'GOV', 'Government'
        PRIVATE = 'PVT', 'Private'
        AIDED = 'AIDED', 'Aided'

    school_type = models.CharField(max_length=10, choices=SchoolType.choices, null=True, blank=True)
    status = models.CharField(max_length=5, default='Yes')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'school'
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Backward-compatibility aliases (for legacy SQL Server source names)
# ---------------------------------------------------------------------------
Session = AcademicSession
Groups = Group
BatchStudent = Users
