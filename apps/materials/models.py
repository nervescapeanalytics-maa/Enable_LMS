"""
LMS Enterprise - Study Materials Models
Replaces legacy: ebook, video_link, question_paper, teacher_training_video,
photo_category, photo_gallery, scholarships, scholarships_link
"""
import uuid
from django.db import models
from django.utils import timezone


class StudyMaterial(models.Model):
    """Study material (ebook, video, question paper, notes).
    Replaces legacy [ebook], [video_link], [question_paper], [teacher_training_video]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='study_materials')

    # Identity
    material_code = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)

    class MaterialType(models.TextChoices):
        EBOOK = 'EBOOK', 'E-Book / PDF'
        VIDEO = 'VIDEO', 'Video'
        QUESTION_PAPER = 'QUESTION_PAPER', 'Question Paper'
        NOTES = 'NOTES', 'Notes'
        ASSIGNMENT = 'ASSIGNMENT', 'Assignment'
        REFERENCE = 'REFERENCE', 'Reference Material'
        SOLUTION = 'SOLUTION', 'Solution'
        TRAINING_VIDEO = 'TRAINING_VIDEO', 'Training Video'
        PRESENTATION = 'PRESENTATION', 'Presentation'

    material_type = models.CharField(max_length=20, choices=MaterialType.choices, default=MaterialType.EBOOK)

    # File
    file_url = models.URLField(max_length=1000, null=True, blank=True)
    file_name = models.CharField(max_length=500, null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    file_mime_type = models.CharField(max_length=100, null=True, blank=True)
    file_hash = models.CharField(max_length=128, null=True, blank=True)

    # Video fields
    video_url = models.URLField(max_length=1000, null=True, blank=True)
    video_embed_url = models.URLField(max_length=1000, null=True, blank=True)
    video_duration_seconds = models.IntegerField(null=True, blank=True)
    youtube_video_id = models.CharField(max_length=50, null=True, blank=True)

    # Classification
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('academics.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('academics.Topic', on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)

    class TargetAudience(models.TextChoices):
        STUDENT = 'STUDENT', 'Students'
        TEACHER = 'TEACHER', 'Teachers'
        ALL = 'ALL', 'All'

    target_audience = models.CharField(max_length=10, choices=TargetAudience.choices, default=TargetAudience.STUDENT)

    class DifficultyLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', 'Beginner'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
        ADVANCED = 'ADVANCED', 'Advanced'

    difficulty_level = models.CharField(max_length=15, choices=DifficultyLevel.choices, null=True, blank=True)

    # Access
    is_free = models.BooleanField(default=False)
    is_downloadable = models.BooleanField(default=True)
    requires_enrollment = models.BooleanField(default=True)
    allowed_batches = models.JSONField(default=list, blank=True)

    # Upload info
    uploaded_by_id = models.UUIDField(null=True, blank=True)
    uploaded_by_type = models.CharField(max_length=10, null=True, blank=True)
    uploaded_by_name = models.CharField(max_length=200, null=True, blank=True)

    # Stats
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    rating_count = models.IntegerField(default=0)

    # Status
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Extensions
    material_meta = models.JSONField(null=True, blank=True)
    ext_material_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_material_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_material_3 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'study_materials'
        indexes = [
            models.Index(fields=['tenant', 'material_type'], name='idx_material_type'),
            models.Index(fields=['tenant', 'subject'], name='idx_material_subject'),
            models.Index(fields=['tenant', 'is_published'], name='idx_material_published'),
        ]

    def __str__(self):
        return f"{self.material_type}: {self.title}"


class MaterialAccess(models.Model):
    """Tracks material access by students."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE, related_name='accesses')
    user_id = models.UUIDField()
    user_type = models.CharField(max_length=10)

    class AccessAction(models.TextChoices):
        VIEW = 'VIEW', 'Viewed'
        DOWNLOAD = 'DOWNLOAD', 'Downloaded'
        BOOKMARK = 'BOOKMARK', 'Bookmarked'

    action = models.CharField(max_length=10, choices=AccessAction.choices)
    accessed_at = models.DateTimeField(default=timezone.now)
    duration_seconds = models.IntegerField(null=True, blank=True)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'material_accesses'
        verbose_name_plural = 'Material accesses'
        indexes = [
            models.Index(fields=['tenant', 'material', 'user_id'], name='idx_maccess_material_user'),
        ]


class PhotoGallery(models.Model):
    """Photo gallery. Replaces legacy [photo_category] + [photo_gallery]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='gallery_items')

    class CategoryChoice(models.TextChoices):
        CLASSROOM = 'Classroom', 'Classroom'
        EVENTS = 'Events', 'Events'
        ACHIEVEMENTS = 'Achievements', 'Achievements'
        CAMPUS_LIFE = 'Campus Life', 'Campus Life'
        PROGRAMS = 'Programs', 'Programs'
        INFRASTRUCTURE = 'Infrastructure', 'Infrastructure'

    category = models.CharField(max_length=255, choices=CategoryChoice.choices)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    image_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    uploaded_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'photo_gallery'
        ordering = ['category', 'sort_order']
        verbose_name_plural = 'Photo galleries'


class Scholarship(models.Model):
    """Scholarship info. Replaces legacy [scholarships] + [scholarships_link]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='scholarships')

    class Stream(models.TextChoices):
        ENGINEERING = 'ENGINEERING', 'Engineering'
        MEDICAL = 'MEDICAL', 'Medical'
        BOTH = 'BOTH', 'Both'

    name = models.CharField(max_length=500, default='', blank=True, help_text='Scholarship name')
    title = models.CharField(max_length=500, help_text='Legacy field, use name instead')
    description = models.TextField(null=True, blank=True)
    eligibility = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    apply_url = models.URLField(max_length=1000, null=True, blank=True)
    documents_required = models.JSONField(default=list, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True, help_text='FontAwesome icon class')
    stream = models.CharField(max_length=20, choices=Stream.choices, default=Stream.ENGINEERING)

    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'scholarships'
        ordering = ['stream', 'sort_order', 'name']


class TopperStudent(models.Model):
    """Topper showcase. Replaces legacy [topper_student]."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='toppers')

    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, null=True, blank=True)
    student_name = models.CharField(max_length=200)
    photo_url = models.URLField(max_length=1000, null=True, blank=True)
    exam_name = models.CharField(max_length=200)
    year = models.IntegerField()
    rank = models.IntegerField(null=True, blank=True)
    score = models.CharField(max_length=100, null=True, blank=True)
    testimonial = models.TextField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'topper_students'
        ordering = ['sort_order']
