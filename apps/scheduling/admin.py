"""Scheduling - Django Admin Registration"""
from django.contrib import admin
from .models import RecurringRule, Enrollment, BlackoutDate, ClassAttendance


@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'teacher', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('title',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'title', 'description'),
        }),
        ('Schedule & assignment', {
            'fields': (
                'rrule', 'subject', 'teacher', 'batch', 'youtube_channel',
                'start_date', 'end_date', 'start_time', 'duration_mins',
                'effective_from', 'timezone',
            ),
        }),
        ('Status & metadata', {
            'fields': ('status', 'meta_data'),
        }),
        ('Rule lineage', {
            'fields': ('parent_rule', 'superseded_by', 'generated_until'),
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'recurring_rule', 'class_instance', 'method', 'is_active', 'enrolled_at')
    list_filter = ('method', 'is_active', 'tenant')
    readonly_fields = ('id', 'enrolled_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant'),
        }),
        ('Enrollment', {
            'fields': (
                'student', 'recurring_rule', 'class_instance', 'class_group',
                'method', 'is_active', 'enrolled_by', 'enrolled_at', 'unenrolled_at',
            ),
        }),
    )


@admin.register(BlackoutDate)
class BlackoutDateAdmin(admin.ModelAdmin):
    list_display = ('date', 'reason', 'tenant', 'created_at')
    list_filter = ('tenant',)
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'date', 'reason', 'applies_to_batches'),
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
        }),
    )


@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('class_instance', 'student', 'status', 'marked_by', 'marked_at')
    list_filter = ('status', 'tenant')
    readonly_fields = ('id', 'marked_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'class_instance', 'student', 'status', 'marked_by', 'remarks', 'marked_at'),
        }),
    )
