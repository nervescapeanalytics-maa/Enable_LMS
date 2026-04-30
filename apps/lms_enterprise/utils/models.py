"""
LMS Enterprise - Base Model Mixins
Provides common fields and behaviors for all models.
"""
import uuid
from django.db import models
from django.utils import timezone


class UUIDPrimaryKeyMixin(models.Model):
    """Provides UUID as primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TenantMixin(models.Model):
    """Provides tenant_id for multi-tenancy with RLS."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """Provides created_at and updated_at timestamps."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Provides soft delete support."""
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class ExtensionFieldsMixin(models.Model):
    """Provides future extension columns for all models."""
    meta_data = models.JSONField(default=dict, blank=True)
    ext_string_1 = models.CharField(max_length=500, null=True, blank=True)
    ext_string_2 = models.CharField(max_length=500, null=True, blank=True)
    ext_text_1 = models.TextField(null=True, blank=True)
    ext_json_1 = models.JSONField(null=True, blank=True)
    ext_json_2 = models.JSONField(null=True, blank=True)
    ext_decimal_1 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ext_integer_1 = models.IntegerField(null=True, blank=True)
    ext_boolean_1 = models.BooleanField(null=True, blank=True)
    ext_timestamp_1 = models.DateTimeField(null=True, blank=True)
    ext_reference_1 = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True


class BaseModel(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, ExtensionFieldsMixin):
    """
    Standard base model for all tenant-scoped models.
    Provides: UUID PK, tenant_id, created_at, updated_at, extension fields.
    """

    class Meta:
        abstract = True
