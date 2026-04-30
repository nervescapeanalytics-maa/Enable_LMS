from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from accounts.models import Student, StudentPromotion, BatchPromotion
from promotions.models import StudentPromotionProxy, BatchPromotionProxy
from core.admin_utils import EnhancedModelAdmin, export_as_csv


# ═══════════════════════════════════════════════════════════════════
# BATCH PROMOTION — Promote entire class at once
# ═══════════════════════════════════════════════════════════════════
@admin.register(BatchPromotionProxy)
class BatchPromotionAdmin(EnhancedModelAdmin):
    list_display = (
        'from_class_badge', 'arrow_display', 'to_class_badge',
        'students_promoted', 'from_session', 'to_session', 'promoted_at',
    )
    list_filter = ('from_class', 'to_class', 'from_session', 'to_session')
    readonly_fields = ('id', 'promoted_at', 'students_promoted')
    ordering = ['-promoted_at']
    actions = [export_as_csv, 'promote_class_9_to_10', 'promote_class_10_to_11', 'promote_class_11_to_12',
               'promote_class_12_to_passout', 'rollback_selected_batch_promotions']
    list_per_page = 50

    fieldsets = (
        ('Promotion Details', {
            'fields': ('id', 'tenant', 'from_class', 'to_class', 'from_session', 'to_session', 'students_promoted'),
        }),
        ('Meta', {
            'fields': ('promoted_by', 'promoted_at', 'remarks'),
        }),
    )

    change_list_template = 'admin/promotions/batch_change_list.html'

    def from_class_badge(self, obj):
        return format_html(
            '<span style="background:#fef3c7;color:#92400e;padding:4px 14px;border-radius:8px;font-size:0.82rem;font-weight:700;">Class {}</span>',
            obj.from_class
        )
    from_class_badge.short_description = 'From Class'

    def arrow_display(self, obj):
        return format_html('<span style="font-size:1.4rem;color:#3b82f6;">→</span>')
    arrow_display.short_description = ''

    def to_class_badge(self, obj):
        return format_html(
            '<span style="background:#dcfce7;color:#166534;padding:4px 14px;border-radius:8px;font-size:0.82rem;font-weight:700;">Class {}</span>',
            obj.to_class
        )
    to_class_badge.short_description = 'To Class'

    def _do_batch_promote(self, request, from_cls, to_cls):
        from academics.models import AcademicSession
        current_session = AcademicSession.objects.filter(is_current=True).first()
        next_session = None
        if current_session:
            next_session = AcademicSession.objects.filter(
                tenant=current_session.tenant,
                start_date__gt=current_session.start_date,
            ).order_by('start_date').first()
        students = Student.objects.filter(student_class=from_cls, status='ACTIVE')
        count = students.count()
        if count == 0:
            self.message_user(request, f"⚠️ No active students found in Class {from_cls}.")
            return
        tenant = students.first().tenant
        # Create individual promotion records
        promo_records = []
        for s in students:
            promo_records.append(StudentPromotion(
                tenant=s.tenant,
                student=s,
                from_class=from_cls,
                to_class=to_cls,
                from_session=current_session,
                to_session=next_session,
                promoted_by=request.session.get('user_id'),
                remarks=f"Batch promotion: Class {from_cls} → {to_cls}",
            ))
        StudentPromotion.objects.bulk_create(promo_records)
        # Update all students at once
        students.update(student_class=to_cls, updated_at=timezone.now())
        # Create batch promotion record
        BatchPromotion.objects.create(
            tenant=tenant,
            from_class=from_cls,
            to_class=to_cls,
            from_session=current_session,
            to_session=next_session,
            students_promoted=count,
            promoted_by=request.session.get('user_id'),
            remarks=f"Batch promotion via admin action",
        )
        self.message_user(request, f"✅ {count} student(s) promoted from Class {from_cls} → Class {to_cls}.")

    def promote_class_9_to_10(self, request, queryset):
        self._do_batch_promote(request, '9', '10')
    promote_class_9_to_10.short_description = "🎓 Promote ALL Class 9 → Class 10"

    def promote_class_10_to_11(self, request, queryset):
        self._do_batch_promote(request, '10', '11')
    promote_class_10_to_11.short_description = "🎓 Promote ALL Class 10 → Class 11"

    def promote_class_11_to_12(self, request, queryset):
        self._do_batch_promote(request, '11', '12')
    promote_class_11_to_12.short_description = "🎓 Promote ALL Class 11 → Class 12"

    def promote_class_12_to_passout(self, request, queryset):
        self._do_batch_promote(request, '12', 'PASS')
    promote_class_12_to_passout.short_description = "🎓 Promote ALL Class 12 → Class 12 Passout"

    def rollback_selected_batch_promotions(self, request, queryset):
        """Rollback selected batch promotions: revert students back to original class."""
        total_reverted = 0
        for bp in queryset:
            # Find all individual promotion records matching this batch
            promos = StudentPromotion.objects.filter(
                tenant=bp.tenant,
                from_class=bp.from_class,
                to_class=bp.to_class,
                from_session=bp.from_session,
                to_session=bp.to_session,
                remarks__icontains='Batch promotion',
            )
            student_ids = list(promos.values_list('student_id', flat=True))
            if student_ids:
                # Revert students back to from_class
                reverted = Student.objects.filter(
                    id__in=student_ids, student_class=bp.to_class
                ).update(student_class=bp.from_class, updated_at=timezone.now())
                total_reverted += reverted
                # Delete individual promotion records
                promos.delete()
            # Delete the batch promotion record
            bp.delete()
        self.message_user(
            request,
            f"⏪ Rollback complete: {total_reverted} student(s) reverted to their original class. "
            f"{queryset.count()} batch promotion(s) removed."
        )
    rollback_selected_batch_promotions.short_description = "⏪ Rollback selected batch promotions"


# ═══════════════════════════════════════════════════════════════════
# STUDENT PROMOTION — Individual promotion history
# ═══════════════════════════════════════════════════════════════════
@admin.register(StudentPromotionProxy)
class StudentPromotionAdmin(EnhancedModelAdmin):
    list_display = (
        'student_display', 'from_class_badge', 'arrow_display', 'to_class_badge',
        'from_session', 'to_session', 'promoted_at',
    )
    list_filter = ('from_class', 'to_class', 'from_session', 'to_session', 'promoted_at')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_code', 'student__email')
    readonly_fields = ('id', 'promoted_at')
    list_per_page = 50
    ordering = ['-promoted_at']
    actions = [export_as_csv, 'rollback_selected_promotions']
    fieldsets = (
        ('Promotion Details', {
            'fields': ('id', 'tenant', 'student', 'from_class', 'to_class', 'from_session', 'to_session'),
        }),
        ('Meta', {
            'fields': ('promoted_by', 'promoted_at', 'remarks'),
        }),
    )

    def student_display(self, obj):
        s = obj.student
        initials = f"{s.first_name[0]}{s.last_name[0]}" if s.first_name and s.last_name else '?'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);'
            'display:flex;align-items:center;justify-content:center;font-size:0.65rem;color:#fff;font-weight:700;">{}</div>'
            '<span style="font-weight:600;color:#1e293b;">{} ({})</span></div>',
            initials, s.full_name, s.student_code
        )
    student_display.short_description = 'Student'

    def from_class_badge(self, obj):
        return format_html(
            '<span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:8px;font-size:0.78rem;font-weight:700;">Class {}</span>',
            obj.from_class
        )
    from_class_badge.short_description = 'From'

    def arrow_display(self, obj):
        return format_html('<span style="font-size:1.2rem;color:#3b82f6;">→</span>')
    arrow_display.short_description = ''

    def to_class_badge(self, obj):
        return format_html(
            '<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:8px;font-size:0.78rem;font-weight:700;">Class {}</span>',
            obj.to_class
        )
    to_class_badge.short_description = 'To'

    def rollback_selected_promotions(self, request, queryset):
        """Rollback selected individual student promotions."""
        reverted = 0
        for promo in queryset:
            student = promo.student
            # Only revert if student is currently in the 'to_class'
            if student.student_class == promo.to_class:
                student.student_class = promo.from_class
                student.updated_at = timezone.now()
                student.save(update_fields=['student_class', 'updated_at'])
                reverted += 1
            promo.delete()
        self.message_user(
            request,
            f"⏪ Rolled back {reverted} student(s) to their original class. "
            f"{queryset.count()} promotion record(s) removed."
        )
    rollback_selected_promotions.short_description = "⏪ Rollback selected promotions (revert student class)"
