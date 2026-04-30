"""
LMS Enterprise - Account Models
All user types: Student, Teacher, Admin, Parent
With full session, device, and profile tracking.
"""
import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


# ---------------------------------------------------------------------------
# Base User (Abstract)
# ---------------------------------------------------------------------------
class BaseUser(models.Model):
    """Abstract base model for all user types."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='%(class)s_users', db_index=True,
    )

    # Authentication
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=255)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)

    # MFA
    mfa_enabled = models.BooleanField(default=False)

    class MFAMethod(models.TextChoices):
        TOTP = 'TOTP', 'TOTP Authenticator'
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'

    mfa_method = models.CharField(max_length=10, choices=MFAMethod.choices, null=True, blank=True)
    mfa_secret = models.TextField(null=True, blank=True, help_text="Encrypted")
    mfa_backup_codes = models.JSONField(null=True, blank=True, help_text="Encrypted backup codes")
    mfa_enforced_by_admin = models.BooleanField(default=False)

    # Profile
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)

    # Status
    class UserStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Verification'

    status = models.CharField(max_length=25, choices=UserStatus.choices, default=UserStatus.PENDING_VERIFICATION)
    status_reason = models.TextField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.UUIDField(null=True, blank=True)

    # Verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # Future Extension Columns
    meta_data = models.JSONField(default=dict, blank=True)
    ext_string_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_string_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_text_1 = models.TextField(null=True, blank=True)
    ext_json_1 = models.JSONField(null=True, blank=True)
    ext_decimal_1 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        abstract = True

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)
        self.password_changed_at = timezone.now()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.email})"


# ---------------------------------------------------------------------------
# Student Model
# ---------------------------------------------------------------------------
class Student(BaseUser):
    """Student user model - enrolled learner."""

    # Student-specific ID
    student_code = models.CharField(max_length=50, help_text="e.g. 'STU2026001'")
    enrollment_number = models.CharField(max_length=100, null=True, blank=True)

    # Academic
    class ClassLevel(models.TextChoices):
        CLASS_9 = '9', 'Class 9'
        CLASS_10 = '10', 'Class 10'
        CLASS_11 = '11', 'Class 11'
        CLASS_12 = '12', 'Class 12'
        PASSOUT = 'PASS', 'Class 12 Passout'

    student_class = models.CharField(
        max_length=5, choices=ClassLevel.choices, db_column='class_level'
    )

    class ExamTarget(models.TextChoices):
        JEE = 'JEE', 'JEE'
        NEET = 'NEET', 'NEET'
        BOTH = 'BOTH', 'Both'

    exam_target = models.CharField(max_length=10, choices=ExamTarget.choices)

    class Stream(models.TextChoices):
        PCM = 'PCM', 'Physics Chemistry Mathematics'
        PCB = 'PCB', 'Physics Chemistry Biology'
        PCMB = 'PCMB', 'Physics Chemistry Math Biology'

    stream = models.CharField(max_length=10, choices=Stream.choices, null=True, blank=True)
    school_name = models.CharField(
        'School Name', max_length=300, null=True, blank=True,
    )

    class Board(models.TextChoices):
        CBSE = 'CBSE', 'CBSE'
        ICSE = 'ICSE', 'ICSE'
        STATE_BOARD = 'STATE_BOARD', 'State Board'
        IB = 'IB', 'IB'
        OTHER = 'OTHER', 'Other'

    board = models.CharField(max_length=20, choices=Board.choices, null=True, blank=True)

    class Medium(models.TextChoices):
        ENGLISH = 'ENGLISH', 'English'
        HINDI = 'HINDI', 'Hindi'
        REGIONAL = 'REGIONAL', 'Regional'

    medium = models.CharField(max_length=20, choices=Medium.choices, default=Medium.ENGLISH)

    # Location
    address_line_1 = models.CharField(max_length=500, null=True, blank=True)
    address_line_2 = models.CharField(max_length=500, null=True, blank=True)
    city = models.CharField('City / Village', max_length=100)
    district = models.CharField('District', max_length=100, null=True, blank=True)
    state = models.CharField('State', max_length=100)
    pin_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    geo_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    geo_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Personal
    date_of_birth = models.DateField(null=True, blank=True)

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'
        PREFER_NOT = 'PREFER_NOT_TO_SAY', 'Prefer not to say'

    gender = models.CharField(max_length=20, choices=Gender.choices, null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    aadhaar_last_four = models.CharField(max_length=4, null=True, blank=True)
    physically_handicapped = models.BooleanField(
        default=False,
        help_text='Mark Yes if the student has a physical disability.'
    )

    # Academic history / extra flags (surfaced on the list page)
    tps = models.BooleanField(
        default=False, verbose_name='TPS',
        help_text='Tribal / Priority Scheme flag (Yes/No).'
    )
    previous_class_marks = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='Previous Class Marks',
        help_text='Total marks obtained in the previous academic year.'
    )

    # Parent/Guardian
    parent_name = models.CharField(
        'Father / Guardian Name', max_length=200, null=True, blank=True,
        help_text="Father or guardian's full name.",
    )

    class ParentRelation(models.TextChoices):
        FATHER = 'FATHER', 'Father'
        MOTHER = 'MOTHER', 'Mother'
        GUARDIAN = 'GUARDIAN', 'Guardian'

    parent_relation = models.CharField(max_length=15, choices=ParentRelation.choices, null=True, blank=True)
    parent_phone = models.CharField(
        'Father / Guardian Phone', max_length=20, null=True, blank=True,
    )
    parent_email = models.EmailField(null=True, blank=True)
    parent_occupation = models.CharField(max_length=200, null=True, blank=True)

    # Admission
    admission_date = models.DateField(null=True, blank=True)

    class AdmissionSource(models.TextChoices):
        DIRECT = 'DIRECT', 'Direct'
        REFERRAL = 'REFERRAL', 'Referral'
        ONLINE = 'ONLINE', 'Online'
        WALK_IN = 'WALK_IN', 'Walk-in'
        PARTNER = 'PARTNER', 'Partner'

    admission_source = models.CharField(max_length=15, choices=AdmissionSource.choices, null=True, blank=True)
    referred_by = models.UUIDField(null=True, blank=True)
    counselor_id = models.UUIDField(null=True, blank=True)

    # Subscription
    class SubscriptionType(models.TextChoices):
        FREE = 'FREE', 'Free'
        BASIC = 'BASIC', 'Basic'
        PREMIUM = 'PREMIUM', 'Premium'
        SCHOLARSHIP = 'SCHOLARSHIP', 'Scholarship'

    subscription_type = models.CharField(max_length=15, choices=SubscriptionType.choices, default=SubscriptionType.FREE)
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)

    class FeeStatus(models.TextChoices):
        PAID = 'PAID', 'Paid'
        PARTIAL = 'PARTIAL', 'Partial'
        PENDING = 'PENDING', 'Pending'
        WAIVED = 'WAIVED', 'Waived'

    fee_status = models.CharField(max_length=10, choices=FeeStatus.choices, default=FeeStatus.PENDING)

    # Communication Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    notification_email = models.BooleanField(default=True)
    notification_sms = models.BooleanField(default=True)
    notification_push = models.BooleanField(default=True)
    notification_whatsapp = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    # Profile Edit Control
    profile_editable_by_self = models.BooleanField(default=False)
    profile_last_edited_by = models.UUIDField(null=True, blank=True)
    profile_last_edited_at = models.DateTimeField(null=True, blank=True)

    # Batch relation
    batch = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='primary_students'
    )

    # Category relation — groups students for reporting / content scoping.
    category = models.ForeignKey(
        'academics.Category', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='students',
        help_text='Student category (e.g. JEE, NEET, Foundation).'
    )

    # Student-specific extensions
    academic_json = models.JSONField(null=True, blank=True, help_text="Marks, grades, previous scores")
    family_json = models.JSONField(null=True, blank=True, help_text="Extended family details")
    ext_student_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_student_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_student_3 = models.JSONField(null=True, blank=True)

    # Canonical mapping for any non-canonical gender input (e.g. lowercase
    # `male`, single-letter `M`, etc.) — applied on save so DB always holds
    # one of Gender.choices values, which keeps the admin's get_FOO_display()
    # rendering correctly. Importers, REST APIs, fixtures and bulk inserts
    # that bypass save() must call Student.canonicalize_gender() themselves.
    _GENDER_NORMALIZE = {
        'M': 'MALE', 'MALE': 'MALE', 'BOY': 'MALE',
        'F': 'FEMALE', 'FEMALE': 'FEMALE', 'GIRL': 'FEMALE',
        'O': 'OTHER', 'OTHER': 'OTHER',
        'PNTS': 'PREFER_NOT_TO_SAY',
        'PREFER NOT TO SAY': 'PREFER_NOT_TO_SAY',
        'PREFER_NOT_TO_SAY': 'PREFER_NOT_TO_SAY',
    }

    @classmethod
    def canonicalize_gender(cls, value):
        if value in (None, ''):
            return None
        key = str(value).strip().upper()
        return cls._GENDER_NORMALIZE.get(key, value if value in cls.Gender.values else None)

    def save(self, *args, **kwargs):
        # Auto-set password to phone number on first creation (or if password missing).
        # Phone is both the username and default password for student login.
        if not self.password_hash and self.phone:
            self.set_password(self.phone)
        # Canonicalize gender to one of Gender.choices values so admin/UI
        # always shows the proper label rather than '-'.
        if self.gender:
            self.gender = self.canonicalize_gender(self.gender) or self.gender
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'students'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'student_code'],
                name='uq_student_code_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                name='uq_student_email_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'phone'],
                name='uq_student_phone_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'student_code'], name='idx_student_code'),
            models.Index(fields=['tenant', 'email'], name='idx_student_email'),
            models.Index(fields=['tenant', 'phone'], name='idx_student_phone'),
            models.Index(fields=['tenant', 'student_class', 'exam_target'], name='idx_student_class_exam'),
            models.Index(fields=['tenant', 'status'], name='idx_student_status'),
            models.Index(fields=['tenant', 'state', 'city'], name='idx_student_location'),
            models.Index(fields=['tenant', 'batch'], name='idx_student_batch'),
        ]


# ---------------------------------------------------------------------------
# Teacher Model
# ---------------------------------------------------------------------------
class Teacher(BaseUser):
    """Teacher user model - subject matter expert."""

    # Teacher-specific ID
    teacher_code = models.CharField(max_length=50, help_text="e.g. 'TCH001'")
    employee_id = models.CharField(max_length=100, null=True, blank=True)

    # Professional
    subjects = models.JSONField(
        default=list, blank=True,
        help_text="List of subjects: PHYSICS, CHEMISTRY, MATHEMATICS, BIOLOGY"
    )
    specialization = models.JSONField(default=list, blank=True, help_text="e.g. ['Mechanics', 'Thermodynamics']")
    qualification = models.CharField(max_length=255, null=True, blank=True)
    highest_degree = models.CharField(max_length=255, null=True, blank=True)
    experience_years = models.IntegerField(null=True, blank=True)
    experience_details = models.TextField(null=True, blank=True)
    certifications = models.JSONField(default=list, blank=True)

    # Work
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        CONTRACT = 'CONTRACT', 'Contract'
        VISITING = 'VISITING', 'Visiting'

    employment_type = models.CharField(max_length=15, choices=EmploymentType.choices, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    reporting_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reportees'
    )

    # YouTube Configuration
    personal_youtube_channel_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_channel_verified = models.BooleanField(default=False)
    youtube_oauth_token = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_refresh_token = models.TextField(null=True, blank=True, help_text="Encrypted")
    youtube_token_expiry = models.DateTimeField(null=True, blank=True)
    can_create_streams = models.BooleanField(default=False)

    # Permissions
    can_edit_student_profile = models.BooleanField(default=True)
    can_override_attendance = models.BooleanField(default=True)
    can_override_scores = models.BooleanField(default=True)
    max_batches_allowed = models.IntegerField(null=True, blank=True)

    # Contact
    personal_email = models.EmailField(null=True, blank=True)
    personal_phone = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    teacher_city = models.CharField(max_length=100, null=True, blank=True, db_column='city')
    teacher_state = models.CharField(max_length=100, null=True, blank=True, db_column='state')
    teacher_district = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='District',
        help_text='District where the teacher works (used in the Teacher Code prefix).'
    )

    # Banking (for payroll) - Encrypted fields
    bank_name = models.CharField(max_length=200, null=True, blank=True)
    bank_account = models.TextField(null=True, blank=True, help_text="Encrypted")
    ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    pan_number = models.TextField(null=True, blank=True, help_text="Encrypted")

    # Teacher-specific extensions
    expertise_json = models.JSONField(null=True, blank=True)
    availability_json = models.JSONField(null=True, blank=True, help_text="Schedule preferences")
    ext_teacher_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_teacher_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_teacher_3 = models.JSONField(null=True, blank=True)

    # ── Auto-generated teacher_code ────────────────────────────────────
    @staticmethod
    def _code_prefix(value, length=3):
        """Return UPPERCASE alpha prefix of `value` padded to `length` with 'X'."""
        if not value:
            return 'X' * length
        clean = ''.join(ch for ch in str(value).upper() if ch.isalpha())
        return (clean + 'X' * length)[:length]

    def _generate_teacher_code(self):
        """Format: <3-letter state><3-letter district><4-digit serial>.

        Example: Andhra Pradesh / Kurnool / 42 -> 'APKKUR0042'
        Falls back to 'XXX' segments when state/district are blank so the
        code stays unique and valid.
        """
        state_code = self._code_prefix(self.teacher_state)
        district_code = self._code_prefix(self.teacher_district)
        qs = Teacher.objects.filter(tenant=self.tenant)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        serial = qs.count() + 1
        return f"{state_code}{district_code}{serial:04d}"

    def save(self, *args, **kwargs):
        if not self.teacher_code:
            self.teacher_code = self._generate_teacher_code()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'school_teacher'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'teacher_code'],
                name='uq_teacher_code_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                name='uq_teacher_email_per_tenant'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'phone'],
                name='uq_teacher_phone_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'teacher_code'], name='idx_teacher_code'),
            models.Index(fields=['tenant', 'email'], name='idx_teacher_email'),
            models.Index(fields=['tenant', 'status'], name='idx_teacher_status'),
        ]


# ---------------------------------------------------------------------------
# Admin Model
# ---------------------------------------------------------------------------
class Admin(BaseUser):
    """Admin user model - system/tenant/branch administrator."""

    admin_code = models.CharField(max_length=50, null=True, blank=True)

    class AdminType(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        TENANT_ADMIN = 'TENANT_ADMIN', 'Tenant Admin'
        DEPARTMENT_ADMIN = 'DEPARTMENT_ADMIN', 'Department Admin'
        BRANCH_ADMIN = 'BRANCH_ADMIN', 'Branch Admin'
        ACADEMIC_ADMIN = 'ACADEMIC_ADMIN', 'Academic Admin'
        FINANCE_ADMIN = 'FINANCE_ADMIN', 'Finance Admin'
        SUPPORT_ADMIN = 'SUPPORT_ADMIN', 'Support Admin'

    admin_type = models.CharField(max_length=20, choices=AdminType.choices)

    # Access Control
    role = models.ForeignKey(
        'accounts.Role', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='admins'
    )
    staff_role = models.ForeignKey(
        'accounts.StaffRole', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff_admins',
        help_text='Staff panel access role'
    )
    permissions_override = models.JSONField(default=list, blank=True, help_text="Direct permission overrides")
    managed_branches = models.JSONField(default=list, blank=True)

    # Security
    require_ip_whitelist = models.BooleanField(default=False)
    allowed_ips = models.JSONField(default=list, blank=True)
    session_timeout_minutes = models.IntegerField(default=240)

    # Preferences
    class Theme(models.TextChoices):
        LIGHT = 'LIGHT', 'Light'
        DARK = 'DARK', 'Dark'
        SYSTEM = 'SYSTEM', 'System'
        CUSTOM = 'CUSTOM', 'Custom'

    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.LIGHT)
    accent_color = models.CharField(max_length=7, null=True, blank=True)
    dashboard_layout = models.JSONField(null=True, blank=True)
    default_view = models.CharField(max_length=100, null=True, blank=True)
    admin_timezone = models.CharField(max_length=50, default='Asia/Kolkata', db_column='timezone')
    admin_date_format = models.CharField(max_length=20, null=True, blank=True, db_column='date_format')

    class TimeFormat(models.TextChoices):
        H12 = '12H', '12 Hour'
        H24 = '24H', '24 Hour'

    time_format = models.CharField(max_length=5, choices=TimeFormat.choices, default=TimeFormat.H12)

    # Activity
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    failed_login_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Admin-specific extensions
    admin_config = models.JSONField(null=True, blank=True)
    ext_admin_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_admin_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_admin_3 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'admins'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'admin_type'], name='idx_admin_type'),
            models.Index(fields=['tenant', 'email'], name='idx_admin_email'),
            models.Index(fields=['tenant', 'status'], name='idx_admin_status'),
        ]


# ---------------------------------------------------------------------------
# Parent Model
# ---------------------------------------------------------------------------
class Parent(BaseUser):
    """Parent/Guardian user model - optional portal access."""

    parent_code = models.CharField(max_length=50, null=True, blank=True)
    primary_student = models.ForeignKey(
        'accounts.Student', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='primary_parent'
    )

    class Relationship(models.TextChoices):
        FATHER = 'FATHER', 'Father'
        MOTHER = 'MOTHER', 'Mother'
        GUARDIAN = 'GUARDIAN', 'Guardian'
        OTHER = 'OTHER', 'Other'

    relationship = models.CharField(max_length=15, choices=Relationship.choices, null=True, blank=True)

    # Permissions
    can_view_attendance = models.BooleanField(default=True)
    can_view_results = models.BooleanField(default=True)
    can_view_fee_details = models.BooleanField(default=True)
    can_communicate_teacher = models.BooleanField(default=True)
    receive_notifications = models.BooleanField(default=True)

    # Extensions
    ext_parent_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_parent_2 = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'parents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'email'], name='idx_parent_email'),
        ]


class ParentStudent(models.Model):
    """Many-to-many relationship between Parents and Students."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='student_links')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parent_links')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'parent_students'
        constraints = [
            models.UniqueConstraint(fields=['parent', 'student'], name='uq_parent_student'),
        ]


# ---------------------------------------------------------------------------
# Role & Permission Models
# ---------------------------------------------------------------------------
class Role(models.Model):
    """Role model for RBAC."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='roles',
        help_text="Null for system-level roles"
    )

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    class RoleType(models.TextChoices):
        SYSTEM = 'SYSTEM', 'System'
        TENANT_DEFAULT = 'TENANT_DEFAULT', 'Tenant Default'
        CUSTOM = 'CUSTOM', 'Custom'

    role_type = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.CUSTOM)

    class AppliesTo(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        TEACHING_ASSISTANT = 'TEACHING_ASSISTANT', 'Teaching Assistant'
        STUDENT = 'STUDENT', 'Student'
        PARENT = 'PARENT', 'Parent'
        ALL = 'ALL', 'All'

    applies_to = models.CharField(max_length=20, choices=AppliesTo.choices, default=AppliesTo.ALL)

    level = models.IntegerField(default=0, help_text="Role hierarchy level")
    parent_role = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='child_roles'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.UUIDField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Extension
    role_meta = models.JSONField(null=True, blank=True)
    ext_role_1 = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'roles'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='uq_role_code_per_tenant'
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Permission(models.Model):
    """Permission model for fine-grained access control."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(max_length=100, unique=True, help_text="e.g. 'student:profile:edit'")
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    module = models.CharField(max_length=50, help_text="e.g. 'student', 'teacher', 'class'")
    category = models.CharField(max_length=50, help_text="e.g. 'profile', 'attendance'")

    resource = models.CharField(max_length=50)

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        EXECUTE = 'EXECUTE', 'Execute'
        APPROVE = 'APPROVE', 'Approve'
        EXPORT = 'EXPORT', 'Export'

    action = models.CharField(max_length=10, choices=Action.choices)

    class Scope(models.TextChoices):
        OWN = 'OWN', 'Own'
        BATCH = 'BATCH', 'Batch'
        BRANCH = 'BRANCH', 'Branch'
        TENANT = 'TENANT', 'Tenant'
        GLOBAL = 'GLOBAL', 'Global'

    scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.OWN)

    requires = models.JSONField(default=list, blank=True, help_text="Required permission codes")
    is_active = models.BooleanField(default=True)

    permission_meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['module', 'category', 'action']

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Many-to-many between Role and Permission."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'role_permissions'
        constraints = [
            models.UniqueConstraint(fields=['role', 'permission'], name='uq_role_permission'),
        ]


# ---------------------------------------------------------------------------
# Password Change Request Model
# ---------------------------------------------------------------------------
class PasswordChangeRequest(models.Model):
    """Tracks password change/reset requests."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    user_id = models.UUIDField()

    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'
        ADMIN = 'ADMIN', 'Admin'
        PARENT = 'PARENT', 'Parent'

    user_type = models.CharField(max_length=10, choices=UserType.choices)

    class Method(models.TextChoices):
        SELF_CHANGE = 'SELF_CHANGE', 'Self Change'
        OTP_PHONE = 'OTP_PHONE', 'OTP via Phone'
        OTP_EMAIL = 'OTP_EMAIL', 'OTP via Email'
        ADMIN_RESET = 'ADMIN_RESET', 'Admin Reset'
        TICKET_REQUEST = 'TICKET_REQUEST', 'Ticket Request'

    method = models.CharField(max_length=20, choices=Method.choices)

    # OTP
    otp_code = models.CharField(max_length=255, null=True, blank=True, help_text="Hashed OTP")
    otp_sent_to = models.CharField(max_length=255, null=True, blank=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    otp_verified = models.BooleanField(default=False)

    # Token
    reset_token = models.CharField(max_length=500, unique=True, null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Status
    class RequestStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        OTP_SENT = 'OTP_SENT', 'OTP Sent'
        OTP_VERIFIED = 'OTP_VERIFIED', 'OTP Verified'
        COMPLETED = 'COMPLETED', 'Completed'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'

    status = models.CharField(max_length=15, choices=RequestStatus.choices, default=RequestStatus.PENDING)

    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_from_ip = models.GenericIPAddressField(null=True, blank=True)
    completed_from_device = models.ForeignKey(
        'sessions_tracking.UserDevice', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # Related ticket
    ticket = models.ForeignKey(
        'communication.SupportTicket', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    # Extension
    request_meta = models.JSONField(null=True, blank=True)
    ext_pwd_1 = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'password_change_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'user_type', 'status'], name='idx_pwd_req_user'),
            models.Index(fields=['reset_token'], name='idx_pwd_req_token'),
        ]


# ---------------------------------------------------------------------------
# Staff Role — Super Admin / Operator / Admin for staff panel access
# ---------------------------------------------------------------------------
class StaffRole(models.Model):
    """Defines staff-level roles with hierarchical permissions for admins/operators."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='staff_roles',
    )

    class StaffLevel(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        OPERATOR = 'OPERATOR', 'Operator'

    level = models.CharField(max_length=15, choices=StaffLevel.choices, default=StaffLevel.OPERATOR)
    name = models.CharField(max_length=200, help_text='Display name, e.g. "Academic Operator"')
    description = models.TextField(null=True, blank=True)

    # Granular permissions
    can_manage_students = models.BooleanField(default=True)
    can_manage_teachers = models.BooleanField(default=True)
    can_manage_exams = models.BooleanField(default=False)
    can_manage_attendance = models.BooleanField(default=True)
    can_manage_content = models.BooleanField(default=False)
    can_manage_finance = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_manage_integrations = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    can_export_data = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    can_view_audit = models.BooleanField(default=True)
    can_manage_website = models.BooleanField(default=False)
    can_manage_ai = models.BooleanField(default=False)

    # Scope restrictions
    allowed_centers = models.JSONField(default=list, blank=True, help_text='Restrict to specific center IDs')
    allowed_batches = models.JSONField(default=list, blank=True, help_text='Restrict to specific batch IDs')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'staff_roles'
        ordering = ['level', 'name']

    def __str__(self):
        return f"{self.get_level_display()} — {self.name}"


# -----------------------------------------------------------------------
# Scoped User ↔ Role Assignment
# -----------------------------------------------------------------------
class UserRoleAssignment(models.Model):
    """
    Assigns a Role to any user type within a specific scope.
    Supports temporary roles via valid_from / valid_until.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='user_role_assignments',
    )

    # Polymorphic user reference
    user_id = models.UUIDField(db_index=True)

    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'
        ADMIN = 'ADMIN', 'Admin'
        PARENT = 'PARENT', 'Parent'

    user_type = models.CharField(max_length=10, choices=UserType.choices)

    role = models.ForeignKey(
        'accounts.Role', on_delete=models.CASCADE,
        related_name='user_assignments',
    )

    # Scope
    class ScopeType(models.TextChoices):
        GLOBAL = 'GLOBAL', 'Global'
        TENANT = 'TENANT', 'Tenant'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        COURSE = 'COURSE', 'Course'
        BATCH = 'BATCH', 'Batch'

    scope_type = models.CharField(
        max_length=15, choices=ScopeType.choices, default=ScopeType.TENANT,
    )
    scope_id = models.UUIDField(
        null=True, blank=True,
        help_text="ID of the scoped entity (department, course, batch). Null for GLOBAL/TENANT.",
    )

    # Temporary roles
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    assigned_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_role_assignments'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user_id', 'user_type', 'role', 'scope_type', 'scope_id'],
                name='uq_user_role_scope',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'user_id', 'user_type'], name='idx_ura_user'),
            models.Index(fields=['tenant', 'role'], name='idx_ura_role'),
            models.Index(fields=['scope_type', 'scope_id'], name='idx_ura_scope'),
        ]

    def __str__(self):
        return f"{self.user_type}:{self.user_id} → {self.role.code} ({self.scope_type})"

    @property
    def is_expired(self):
        if self.valid_until and timezone.now() > self.valid_until:
            return True
        return False

    @property
    def is_effective(self):
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return self.is_active


# -----------------------------------------------------------------------
# ABAC Policy
# -----------------------------------------------------------------------
class ABACPolicy(models.Model):
    """
    Attribute-Based Access Control policy.
    Evaluated alongside RBAC permissions for fine-grained control.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='abac_policies',
    )

    code = models.CharField(max_length=100, unique=True, help_text="e.g. 'enrollment_active_only'")
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    # What resource & action this policy applies to
    resource = models.CharField(max_length=50, help_text="e.g. 'COURSE', 'GRADE', 'USER'")
    action = models.CharField(max_length=20, help_text="e.g. 'VIEW', 'EDIT', 'DELETE'")

    # JSON conditions (evaluated at runtime)
    conditions = models.JSONField(
        default=dict, blank=True,
        help_text=(
            'JSON condition tree. Example: '
            '{"all": [{"attr": "user.status", "op": "eq", "value": "ACTIVE"}, '
            '{"attr": "enrollment.status", "op": "in", "value": ["ENROLLED","ACTIVE"]}]}'
        ),
    )

    class Effect(models.TextChoices):
        ALLOW = 'ALLOW', 'Allow'
        DENY = 'DENY', 'Deny'

    effect = models.CharField(max_length=5, choices=Effect.choices, default=Effect.ALLOW)
    priority = models.IntegerField(default=0, help_text="Higher = evaluated first. Deny wins on tie.")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'abac_policies'
        ordering = ['-priority', 'code']
        verbose_name = 'ABAC Policy'
        verbose_name_plural = 'ABAC Policies'

    def __str__(self):
        return f"[{self.effect}] {self.code} — {self.resource}:{self.action}"


# -----------------------------------------------------------------------
# Access Audit Log (lightweight, append-only)
# -----------------------------------------------------------------------
class AccessLog(models.Model):
    """
    Immutable log of every access decision.
    Kept separate from the general AuditLog for performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    action = models.CharField(max_length=50)
    resource = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, null=True, blank=True)

    class Decision(models.TextChoices):
        ALLOW = 'ALLOW', 'Allow'
        DENY = 'DENY', 'Deny'

    decision = models.CharField(max_length=5, choices=Decision.choices)
    reason = models.CharField(max_length=500, null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device_id = models.UUIDField(null=True, blank=True)

    context = models.JSONField(null=True, blank=True, help_text="Snapshot of evaluated attributes")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'access_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant_id', 'user_id', 'timestamp'], name='idx_access_user_ts'),
            models.Index(fields=['tenant_id', 'action', 'resource'], name='idx_access_action'),
        ]

    def __str__(self):
        return f"{self.decision} {self.user_type}:{self.user_id} → {self.resource}:{self.action}"


# ═══════════════════════════════════════════════════════════════════════════════
# USER GROUPS — Group-based role assignment
# ═══════════════════════════════════════════════════════════════════════════════

class UserGroup(models.Model):
    """Groups for assigning roles to multiple users at once."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='user_groups'
    )

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    class GroupType(models.TextChoices):
        DEPARTMENT = 'DEPARTMENT', 'Department'
        BATCH = 'BATCH', 'Batch'
        CUSTOM = 'CUSTOM', 'Custom'
        SYSTEM = 'SYSTEM', 'System'

    group_type = models.CharField(
        max_length=20, choices=GroupType.choices, default=GroupType.CUSTOM
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'user_groups'
        ordering = ['group_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'], name='uq_user_group_code'
            ),
        ]
        verbose_name = 'User Group'
        verbose_name_plural = 'User Groups'

    def __str__(self):
        return f"{self.name} ({self.code})"


class GroupMembership(models.Model):
    """Membership of users in groups."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    group = models.ForeignKey(
        UserGroup, on_delete=models.CASCADE, related_name='memberships'
    )

    user_id = models.UUIDField(db_index=True)

    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'
        ADMIN = 'ADMIN', 'Admin'
        PARENT = 'PARENT', 'Parent'

    user_type = models.CharField(max_length=10, choices=UserType.choices)

    added_by = models.UUIDField(null=True, blank=True)
    added_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'group_memberships'
        constraints = [
            models.UniqueConstraint(fields=['group', 'user_id', 'user_type'], name='uq_group_membership'),
        ]
        verbose_name = 'Group Membership'
        verbose_name_plural = 'Group Memberships'

    def __str__(self):
        return f"{self.user_type}:{str(self.user_id)[:8]} → {self.group.name}"


class GroupRoleAssignment(models.Model):
    """Assign a Role to an entire Group — all members inherit the role."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    group = models.ForeignKey(
        UserGroup, on_delete=models.CASCADE, related_name='role_assignments'
    )
    role = models.ForeignKey(
        'accounts.Role', on_delete=models.CASCADE,
        related_name='group_assignments'
    )

    class ScopeType(models.TextChoices):
        GLOBAL = 'GLOBAL', 'Global'
        TENANT = 'TENANT', 'Tenant'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        COURSE = 'COURSE', 'Course'
        BATCH = 'BATCH', 'Batch'

    scope_type = models.CharField(
        max_length=15, choices=ScopeType.choices, default=ScopeType.TENANT
    )
    scope_id = models.UUIDField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    assigned_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'group_role_assignments'
        constraints = [
            models.UniqueConstraint(fields=['group', 'role', 'scope_type', 'scope_id'], name='uq_group_role_assignment'),
        ]
        verbose_name = 'Group Role Assignment'
        verbose_name_plural = 'Group Role Assignments'

    def __str__(self):
        return f"{self.group.name} → {self.role.name} ({self.scope_type})"


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT SECURITY
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityPolicy(models.Model):
    """Account security policies — password, MFA, session, lockout rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='security_policies'
    )

    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    # ── Password Policy ──
    min_password_length = models.IntegerField(default=8)
    require_uppercase = models.BooleanField(default=True)
    require_lowercase = models.BooleanField(default=True)
    require_digits = models.BooleanField(default=True)
    require_special_chars = models.BooleanField(default=True)
    password_expiry_days = models.IntegerField(default=90)
    password_history_count = models.IntegerField(default=5)
    prevent_common_passwords = models.BooleanField(default=True)

    # ── MFA Policy ──
    mfa_required = models.BooleanField(default=False)
    mfa_required_for_admins = models.BooleanField(default=True)
    allowed_mfa_methods = models.JSONField(
        default=list, blank=True,
        help_text='e.g. ["TOTP","SMS","EMAIL"]'
    )

    # ── Session Policy ──
    max_concurrent_sessions = models.IntegerField(default=3)
    session_timeout_minutes = models.IntegerField(default=480)
    idle_timeout_minutes = models.IntegerField(default=30)

    # ── Lockout Policy ──
    max_failed_attempts = models.IntegerField(default=5)
    lockout_duration_minutes = models.IntegerField(default=30)
    progressive_lockout = models.BooleanField(
        default=True,
        help_text='Each subsequent lockout doubles duration'
    )

    # ── IP & Device Policy ──
    ip_whitelist_enabled = models.BooleanField(default=False)
    ip_whitelist = models.JSONField(default=list, blank=True)
    geo_restriction_enabled = models.BooleanField(default=False)
    allowed_countries = models.JSONField(default=list, blank=True)
    device_trust_enabled = models.BooleanField(default=False)

    class AppliesTo(models.TextChoices):
        ALL = 'ALL', 'All Users'
        ADMIN = 'ADMIN', 'Admins Only'
        TEACHER = 'TEACHER', 'Teachers Only'
        STUDENT = 'STUDENT', 'Students Only'

    applies_to = models.CharField(
        max_length=20, choices=AppliesTo.choices, default=AppliesTo.ALL
    )

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text='Higher = evaluated first')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_policies'
        ordering = ['-priority', 'name']
        verbose_name = 'Security Policy'
        verbose_name_plural = 'Security Policies'

    def __str__(self):
        return self.name


class LoginAttemptLog(models.Model):
    """Track every login attempt for security monitoring."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True
    )

    user_id = models.UUIDField(null=True, blank=True)
    user_type = models.CharField(max_length=20, null=True, blank=True)
    username_attempted = models.CharField(max_length=255)

    class AttemptResult(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED_PASSWORD = 'FAILED_PASSWORD', 'Failed — Wrong Password'
        FAILED_NOT_FOUND = 'FAILED_NOT_FOUND', 'Failed — User Not Found'
        FAILED_LOCKED = 'FAILED_LOCKED', 'Failed — Account Locked'
        FAILED_SUSPENDED = 'FAILED_SUSPENDED', 'Failed — Account Suspended'
        FAILED_MFA = 'FAILED_MFA', 'Failed — MFA Failed'
        FAILED_IP_BLOCKED = 'FAILED_IP_BLOCKED', 'Failed — IP Blocked'

    result = models.CharField(max_length=25, choices=AttemptResult.choices)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    geo_location = models.JSONField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=255, null=True, blank=True)

    risk_score = models.IntegerField(
        default=0, help_text='0-100, higher = riskier'
    )
    risk_factors = models.JSONField(default=list, blank=True)

    attempted_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'login_attempt_logs'
        ordering = ['-attempted_at']
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
        indexes = [
            models.Index(
                fields=['user_id', 'attempted_at'], name='idx_logatt_user_time'
            ),
            models.Index(
                fields=['ip_address', 'attempted_at'], name='idx_logatt_ip_time'
            ),
            models.Index(
                fields=['result', 'attempted_at'], name='idx_logatt_result_time'
            ),
        ]

    def __str__(self):
        return f"{self.result}: {self.username_attempted} @ {self.attempted_at}"


class TrustedDevice(models.Model):
    """Trusted devices — MFA can be skipped on trusted devices."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    device_name = models.CharField(max_length=200)
    device_fingerprint = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os_name = models.CharField(
        max_length=100, null=True, blank=True, db_column='os'
    )

    trusted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'trusted_devices'
        ordering = ['-trusted_at']
        verbose_name = 'Trusted Device'
        verbose_name_plural = 'Trusted Devices'

    def __str__(self):
        return f"{self.device_name} ({self.user_type}:{str(self.user_id)[:8]})"


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS & BEHAVIOR MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

class BehaviorEvent(models.Model):
    """Tracks user behavior events for analytics and anomaly detection."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True
    )

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    class EventCategory(models.TextChoices):
        AUTH = 'AUTH', 'Authentication'
        NAVIGATION = 'NAVIGATION', 'Navigation'
        DATA_ACCESS = 'DATA_ACCESS', 'Data Access'
        DATA_MODIFICATION = 'DATA_MODIFICATION', 'Data Modification'
        EXPORT = 'EXPORT', 'Data Export'
        COMMUNICATION = 'COMMUNICATION', 'Communication'
        ASSESSMENT = 'ASSESSMENT', 'Assessment'
        ATTENDANCE = 'ATTENDANCE', 'Attendance'
        ADMIN_ACTION = 'ADMIN_ACTION', 'Admin Action'
        SYSTEM = 'SYSTEM', 'System'

    event_category = models.CharField(
        max_length=20, choices=EventCategory.choices
    )
    event_action = models.CharField(max_length=100)
    event_detail = models.JSONField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.UUIDField(null=True, blank=True)

    is_anomalous = models.BooleanField(default=False)
    anomaly_score = models.FloatField(default=0.0)

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'behavior_events'
        ordering = ['-occurred_at']
        verbose_name = 'Behavior Event'
        verbose_name_plural = 'Behavior Events'
        indexes = [
            models.Index(
                fields=['user_id', 'event_category', 'occurred_at'],
                name='idx_behavior_user_cat',
            ),
            models.Index(
                fields=['is_anomalous', 'occurred_at'],
                name='idx_behavior_anomaly',
            ),
        ]

    def __str__(self):
        return (
            f"{self.event_category}:{self.event_action} "
            f"by {self.user_type}:{str(self.user_id)[:8]}"
        )


class AnomalyDetectionRule(models.Model):
    """Rules for detecting anomalous user behaviour."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    class RuleType(models.TextChoices):
        THRESHOLD = 'THRESHOLD', 'Threshold-based'
        PATTERN = 'PATTERN', 'Pattern-based'
        TIME_BASED = 'TIME_BASED', 'Time-based'
        GEO_BASED = 'GEO_BASED', 'Geo-based'
        BEHAVIORAL = 'BEHAVIORAL', 'Behavioral'

    rule_type = models.CharField(max_length=15, choices=RuleType.choices)

    target_event_category = models.CharField(
        max_length=20, null=True, blank=True
    )
    conditions = models.JSONField(
        default=dict, blank=True,
        help_text='Rule conditions in JSON format'
    )
    threshold_value = models.FloatField(null=True, blank=True)
    time_window_minutes = models.IntegerField(null=True, blank=True)

    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )

    auto_block = models.BooleanField(default=False)
    auto_notify = models.BooleanField(default=True)
    notification_channels = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'anomaly_detection_rules'
        ordering = ['-severity', 'name']
        verbose_name = 'Anomaly Detection Rule'
        verbose_name_plural = 'Anomaly Detection Rules'

    def __str__(self):
        return f"[{self.severity}] {self.name}"


class AnomalyAlert(models.Model):
    """Alerts generated by anomaly detection rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True
    )

    rule = models.ForeignKey(
        AnomalyDetectionRule, on_delete=models.CASCADE,
        related_name='alerts', null=True, blank=True
    )

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    class AlertStatus(models.TextChoices):
        NEW = 'NEW', 'New'
        INVESTIGATING = 'INVESTIGATING', 'Investigating'
        CONFIRMED = 'CONFIRMED', 'Confirmed Threat'
        FALSE_POSITIVE = 'FALSE_POSITIVE', 'False Positive'
        RESOLVED = 'RESOLVED', 'Resolved'

    status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.NEW
    )

    class AlertSeverity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    severity = models.CharField(
        max_length=10, choices=AlertSeverity.choices, default=AlertSeverity.MEDIUM
    )

    title = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)

    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.UUIDField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.UUIDField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)

    auto_action_taken = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'anomaly_alerts'
        ordering = ['-detected_at']
        verbose_name = 'Anomaly Alert'
        verbose_name_plural = 'Anomaly Alerts'
        indexes = [
            models.Index(
                fields=['status', 'severity', 'detected_at'],
                name='idx_anomaly_status',
            ),
            models.Index(
                fields=['user_id', 'detected_at'],
                name='idx_anomaly_user',
            ),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE & DATA GOVERNANCE
# ═══════════════════════════════════════════════════════════════════════════════

class ComplianceRule(models.Model):
    """Compliance rules and regulations tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    class RegulationType(models.TextChoices):
        GDPR = 'GDPR', 'GDPR'
        FERPA = 'FERPA', 'FERPA'
        COPPA = 'COPPA', 'COPPA'
        IT_ACT = 'IT_ACT', 'IT Act (India)'
        DPDP = 'DPDP', 'DPDP Act (India)'
        INTERNAL = 'INTERNAL', 'Internal Policy'
        CUSTOM = 'CUSTOM', 'Custom'

    regulation_type = models.CharField(
        max_length=15, choices=RegulationType.choices
    )

    applicable_data_types = models.JSONField(default=list, blank=True)
    applicable_user_types = models.JSONField(default=list, blank=True)

    # Requirements
    data_retention_days = models.IntegerField(null=True, blank=True)
    requires_consent = models.BooleanField(default=False)
    requires_encryption = models.BooleanField(default=False)
    requires_anonymization = models.BooleanField(default=False)
    requires_audit_trail = models.BooleanField(default=True)

    # Enforcement
    auto_enforce = models.BooleanField(default=False)
    enforcement_action = models.CharField(max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compliance_rules'
        ordering = ['regulation_type', 'name']
        verbose_name = 'Compliance Rule'
        verbose_name_plural = 'Compliance Rules'

    def __str__(self):
        return f"[{self.regulation_type}] {self.name}"


class ConsentRecord(models.Model):
    """Tracks user consent for data processing activities."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)

    consent_type = models.CharField(
        max_length=50,
        help_text='e.g., data_processing, marketing, analytics'
    )
    consent_text = models.TextField()
    version = models.CharField(max_length=20)

    is_granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    collection_method = models.CharField(
        max_length=50,
        help_text='e.g., web_form, api, admin_override'
    )

    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'consent_records'
        ordering = ['-granted_at']
        verbose_name = 'Consent Record'
        verbose_name_plural = 'Consent Records'

    def __str__(self):
        status = 'Granted' if self.is_granted else 'Revoked'
        return f"{self.consent_type} ({status}) — {self.user_type}:{str(self.user_id)[:8]}"


class DataAccessRequest(models.Model):
    """Data Subject Access Requests (DSAR) — GDPR/regulatory compliance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    user_id = models.UUIDField(db_index=True)
    user_type = models.CharField(max_length=10)
    requester_email = models.EmailField()

    class RequestType(models.TextChoices):
        ACCESS = 'ACCESS', 'Data Access'
        RECTIFICATION = 'RECTIFICATION', 'Data Rectification'
        ERASURE = 'ERASURE', 'Data Erasure (Right to be Forgotten)'
        PORTABILITY = 'PORTABILITY', 'Data Portability'
        RESTRICTION = 'RESTRICTION', 'Restrict Processing'
        OBJECTION = 'OBJECTION', 'Object to Processing'

    request_type = models.CharField(
        max_length=15, choices=RequestType.choices
    )
    description = models.TextField()
    data_categories = models.JSONField(default=list, blank=True)

    class RequestStatus(models.TextChoices):
        RECEIVED = 'RECEIVED', 'Received'
        IDENTITY_VERIFICATION = 'IDENTITY_VERIFICATION', 'Identity Verification'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
        APPEALED = 'APPEALED', 'Appealed'

    status = models.CharField(
        max_length=25, choices=RequestStatus.choices,
        default=RequestStatus.RECEIVED
    )

    requested_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(
        null=True, blank=True, help_text='Regulatory deadline'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    assigned_to = models.UUIDField(null=True, blank=True)
    response_notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'data_access_requests'
        ordering = ['-requested_at']
        verbose_name = 'Data Access Request'
        verbose_name_plural = 'Data Access Requests'

    def __str__(self):
        return f"[{self.request_type}] {self.requester_email} ({self.status})"


# ═══════════════════════════════════════════════════════════════════════════════
# PROXY MODELS — Audit models grouped under User Account section
# ═══════════════════════════════════════════════════════════════════════════════

from audit.models import (               # noqa: E402
    AuditLog as _AuditLog,
    AuditPurgePolicy as _AuditPurgePolicy,
    BackupPolicy as _BackupPolicy,
    BackupHistory as _BackupHistory,
)


class AuditEntry(_AuditLog):
    """Proxy: Audit log entries — shown under User Account section."""
    class Meta:
        proxy = True
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'


class RetentionPolicy(_AuditPurgePolicy):
    """Proxy: Data retention policies — shown under User Account section."""
    class Meta:
        proxy = True
        verbose_name = 'Data Retention Policy'
        verbose_name_plural = 'Data Retention Policies'


class BackupPolicyProxy(_BackupPolicy):
    """Proxy: Backup policies — shown under User Account section."""
    class Meta:
        proxy = True
        verbose_name = 'Backup Policy'
        verbose_name_plural = 'Backup Policies'


class BackupRecord(_BackupHistory):
    """Proxy: Backup history — shown under User Account section."""
    class Meta:
        proxy = True
        verbose_name = 'Backup Record'
        verbose_name_plural = 'Backup Records'


# ---------------------------------------------------------------------------
# Student Promotion — Academic Session Promotion
# ---------------------------------------------------------------------------
class StudentPromotion(models.Model):
    """Tracks student promotions from one class to the next academic session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='student_promotions', db_index=True,
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='promotions',
    )
    from_class = models.CharField(max_length=5, choices=Student.ClassLevel.choices)
    to_class = models.CharField(max_length=5, choices=Student.ClassLevel.choices)
    from_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='promotions_from',
    )
    to_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='promotions_to',
    )
    promoted_by = models.UUIDField(null=True, blank=True, help_text="Admin user who promoted")
    promoted_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'student_promotions'
        ordering = ['-promoted_at']
        verbose_name = 'Student Promotion'
        verbose_name_plural = 'Student Promotions'
        indexes = [
            models.Index(fields=['tenant', 'student'], name='idx_promo_student'),
            models.Index(fields=['tenant', 'from_session'], name='idx_promo_from_session'),
        ]

    def __str__(self):
        return f"{self.student} : Class {self.from_class} → Class {self.to_class}"


# ---------------------------------------------------------------------------
# Batch Promotion — Promote entire class at once
# ---------------------------------------------------------------------------
class BatchPromotion(models.Model):
    """Tracks batch-level promotions: all students of one class promoted together."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='batch_promotions', db_index=True,
    )
    from_class = models.CharField(max_length=5, choices=Student.ClassLevel.choices)
    to_class = models.CharField(max_length=5, choices=Student.ClassLevel.choices)
    from_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='batch_promotions_from',
    )
    to_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='batch_promotions_to',
    )
    students_promoted = models.IntegerField(default=0, help_text="Number of students promoted")
    promoted_by = models.UUIDField(null=True, blank=True, help_text="Admin user who promoted")
    promoted_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'batch_promotions'
        ordering = ['-promoted_at']
        verbose_name = 'Batch Promotion'
        verbose_name_plural = 'Batch Promotions'

    def __str__(self):
        return f"Class {self.from_class} → Class {self.to_class} ({self.students_promoted} students)"


# ═══════════════════════════════════════════════════════════════════
# STAFF ROLE PERMISSIONS  (per-model RBAC for the Django admin panel)
# ═══════════════════════════════════════════════════════════════════
class StaffRolePermission(models.Model):
    """Per-(StaffRole, model) view/add/change/delete/export permissions.

    Used by the admin panel matrix UI to give non-technical superusers a
    point-and-click way to grant or revoke section access for custom roles.
    Absence of a row = no access. Superusers always bypass these checks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        StaffRole, on_delete=models.CASCADE,
        related_name='model_permissions',
    )
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)

    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_change = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_role_permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'app_label', 'model_name'],
                name='uq_staff_role_perm',
            ),
        ]
        ordering = ['app_label', 'model_name']

    def __str__(self):
        return f"{self.role.name} → {self.app_label}.{self.model_name}"


class UserStaffRole(models.Model):
    """Links a Django auth User to a StaffRole.

    Superusers bypass all permission checks; non-superusers assigned to a
    StaffRole are restricted to the (model, action) combinations granted via
    StaffRolePermission. Users with no UserStaffRole and no superuser flag
    fall back to the legacy admin behaviour (admin checks `is_staff`).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'auth.User', on_delete=models.CASCADE,
        related_name='staff_role_link',
    )
    role = models.ForeignKey(
        StaffRole, on_delete=models.PROTECT,
        related_name='user_links',
    )
    is_active = models.BooleanField(default=True)
    assigned_by = models.UUIDField(null=True, blank=True)
    assigned_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'user_staff_roles'
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"
