"""
Phase 4 admin views — under /staff/exams/* (import + versions) and the
new /staff/analytics/* group (reports, AI insights, alerts).

All views reuse the existing ``_gate`` / ``_exam_ctx`` helpers from
``admin_exam_views`` to inherit RBAC + sidebar context.
"""
from __future__ import annotations

import io
import logging

from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import (
    HttpResponse, HttpResponseRedirect, JsonResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from assessments.models import (
    Test, TestVersion, TestAttempt, Question, TestSection,
)
from assessments.permissions import (
    can_manage_exams, get_logged_in_admin, is_admin_full,
    log_exam_event, is_feature_enabled, get_exam_setting_int,
    EXAM_SETTINGS,
)
from assessments.views.admin_exam_views import _gate, _exam_ctx, _forbidden
from assessments import importers, versioning, insights, underperformers
from system_config.models import SystemSetting

logger = logging.getLogger(__name__)


# ===========================================================================
# QUESTION IMPORT  /staff/exams/import/
# ===========================================================================
class QuestionImportView(View):
    """Two-step CSV/XLSX import: upload → preview → confirm."""

    template_name = 'exams/admin_question_import.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_feature_enabled('exam.question_import',
                                  tenant=getattr(admin_user, 'tenant', None),
                                  user_type='ADMIN'):
            return _forbidden(request, 'Bulk import is disabled by feature flag.')

        ctx = _exam_ctx(request, admin_user, active_page='exam-import',
                        page_title='Bulk Import Questions')
        ctx['tests'] = Test.objects.filter(is_deleted=False).order_by('-created_at')[:200]
        return render(request, self.template_name, ctx)

    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_feature_enabled('exam.question_import',
                                  tenant=getattr(admin_user, 'tenant', None),
                                  user_type='ADMIN'):
            return _forbidden(request, 'Bulk import is disabled by feature flag.')

        action = request.POST.get('action') or 'preview'
        test_id = request.POST.get('test_id')
        if not test_id:
            messages.error(request, 'Pick a target test.')
            return redirect('staff-exam-import')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)

        f = request.FILES.get('file')
        if not f:
            messages.error(request, 'Upload a CSV or XLSX file.')
            return redirect('staff-exam-import')

        ext = (f.name.rsplit('.', 1)[-1] if '.' in f.name else '').lower()
        try:
            if ext == 'zip':
                # ZIP: extract images to MEDIA_ROOT and rewrite image columns
                # to /media/... URLs before validation/apply.
                rows = importers.parse_zip_with_assets(f)
            else:
                rows = importers.parse_rows(f, ext)
        except Exception as e:
            messages.error(request, f'Could not parse file: {e}')
            return redirect('staff-exam-import')

        cleaned, errors = importers.validate_rows(
            rows, test=test, tenant=test.tenant,
        )

        if action == 'apply':
            if errors:
                messages.error(request, 'Cannot apply — fix errors first.')
            else:
                result = importers.apply_rows(
                    cleaned, test=test, tenant=test.tenant,
                    actor=admin_user, request=request,
                )
                messages.success(
                    request,
                    f'Imported {result["total"]} ({result["created"]} new, '
                    f'{result["updated"]} updated).',
                )
                return redirect('staff-exam-detail', test_id=test.id)

        ctx = _exam_ctx(request, admin_user, active_page='exam-import',
                        page_title='Bulk Import — Preview')
        ctx.update({
            'test': test,
            'tests': Test.objects.filter(is_deleted=False).order_by('-created_at')[:200],
            'preview_rows': cleaned[:200],
            'preview_errors': errors[:200],
            'total_rows': len(rows),
            'cleaned_count': len(cleaned),
            'error_count': len(errors),
        })
        return render(request, self.template_name, ctx)


def question_import_template(request):
    admin_user, redir = _gate(request)
    if redir:
        return redir
    body = importers.template_csv()
    resp = HttpResponse(body, content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="questions_import_template.csv"'
    return resp


# ===========================================================================
# ZIP EXPORT  /staff/exams/export-zip/
# ===========================================================================
class ZipExportPickerView(View):
    """Lightweight picker: choose a Test and download a ZIP of its questions."""

    template_name = 'exams/admin_zip_export.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        ctx = _exam_ctx(request, admin_user, active_page='exam-import',
                        page_title='Export Test as ZIP')
        ctx['tests'] = Test.objects.filter(is_deleted=False).order_by('-created_at')[:300]
        return render(request, self.template_name, ctx)

    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test_id = request.POST.get('test_id')
        if not test_id:
            messages.error(request, 'Pick a test to export.')
            return redirect('staff-exam-export-zip-picker')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        try:
            blob = importers.export_test_zip(test)
        except Exception as e:  # noqa: BLE001
            logger.exception('ZIP export failed for test %s', test.id)
            messages.error(request, f'Export failed: {e}')
            return redirect('staff-exam-export-zip-picker')

        log_exam_event(
            request=request, actor=admin_user,
            action='TEST_EXPORT_ZIP',
            resource_type='Test', resource_id=test.id,
            resource_name=test.test_code,
            description=f'exported test {test.test_code} as ZIP ({len(blob)} bytes)',
        )

        safe = (test.test_code or 'test').replace('/', '_').replace(' ', '_')
        resp = HttpResponse(blob, content_type='application/zip')
        resp['Content-Disposition'] = f'attachment; filename="{safe}_questions.zip"'
        return resp


# ===========================================================================
# TEST VERSIONS  /staff/exams/<test_id>/versions/
# ===========================================================================
class TestVersionListView(View):
    template_name = 'exams/admin_test_versions.html'

    def get(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_feature_enabled('exam.test_versioning',
                                  tenant=getattr(admin_user, 'tenant', None),
                                  user_type='ADMIN'):
            return _forbidden(request, 'Versioning is disabled by feature flag.')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        versions = TestVersion.objects.filter(test=test).order_by('-version_number')

        ctx = _exam_ctx(request, admin_user, active_page='exam-versions',
                        page_title=f'Versions — {test.test_code}')
        ctx.update({'test': test, 'versions': versions})
        return render(request, self.template_name, ctx)


class TestVersionSnapshotView(View):
    """POST — take a new snapshot of the live test."""

    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        label = (request.POST.get('label') or '').strip()
        note = (request.POST.get('note') or '').strip()
        v = versioning.take_snapshot(
            test, actor=admin_user, label=label, note=note, request=request,
        )
        messages.success(request, f'Snapshot v{v.version_number} captured.')
        return redirect('staff-exam-versions', test_id=test.id)


class TestVersionRestoreView(View):
    """POST — restore live test from a chosen version (full admin only)."""

    def post(self, request, test_id, version_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may restore.')

        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        version = get_object_or_404(TestVersion, id=version_id, test=test)

        # Capture the live state first so the rollback itself is reversible.
        versioning.take_snapshot(
            test, actor=admin_user,
            label=f'Auto pre-restore (was v{TestVersion.objects.filter(test=test).count()})',
            note=f'Captured automatically before restoring to v{version.version_number}',
            request=request,
        )
        versioning.restore_version(version, actor=admin_user, request=request)
        messages.success(
            request, f'Test restored from v{version.version_number}.',
        )
        return redirect('staff-exam-versions', test_id=test.id)


class TestVersionDiffView(View):
    """GET — JSON diff between two versions (?a=<id>&b=<id>)."""

    def get(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        a_id = request.GET.get('a')
        b_id = request.GET.get('b')
        if not a_id or not b_id:
            return HttpResponseBadRequest('a and b query params required')
        va = get_object_or_404(TestVersion, id=a_id, test=test)
        vb = get_object_or_404(TestVersion, id=b_id, test=test)
        return JsonResponse({
            'a': {'id': str(va.id), 'version': va.version_number},
            'b': {'id': str(vb.id), 'version': vb.version_number},
            'diff': versioning.diff_versions(va, vb),
        })


# ===========================================================================
# AI INSIGHTS  /staff/analytics/ai/
# ===========================================================================
class AIInsightsView(View):
    template_name = 'exams/admin_ai_insights.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        tenant = getattr(admin_user, 'tenant', None)

        # All evaluated attempts grouped by student → list of percents
        qs = (TestAttempt.objects
              .filter(status__in=('EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'))
              .select_related('student')
              .order_by('student_id', 'submitted_at'))
        if tenant is not None:
            qs = qs.filter(tenant=tenant)

        from collections import defaultdict
        by_student: dict = defaultdict(list)
        student_obj: dict = {}
        for a in qs:
            by_student[a.student_id].append(a.percentage)
            student_obj[a.student_id] = a.student

        rows = []
        for sid, percents in by_student.items():
            ins = insights.insights_for_attempts(percents, tenant=tenant)
            if not ins.get('ok'):
                continue
            student = student_obj[sid]
            rows.append({
                'student': student,
                'samples': ins['samples'],
                'last': ins.get('last'),
                'avg': ins.get('avg'),
                'predicted_next_pct': ins.get('predicted_next_pct'),
                'risk_band': ins.get('risk_band'),
                'predicted_rank_band': ins.get('predicted_rank_band'),
                'narrative': ins.get('narrative'),
            })
        rows.sort(key=lambda r: (r['risk_band'] != 'RED',
                                 r['risk_band'] != 'AMBER',
                                 r['predicted_next_pct']))

        ctx = _exam_ctx(request, admin_user, active_page='ai-insights',
                        page_title='AI Insights')
        ctx.update({
            'rows': rows[:300],
            'rule_enabled': is_feature_enabled(
                'exam.ai_prediction_rule', tenant=tenant, user_type='ADMIN'),
            'llm_enabled': is_feature_enabled(
                'exam.ai_prediction_llm', tenant=tenant, user_type='ADMIN'),
            'red_zone': get_exam_setting_int('exam.alert_red_zone_percent',
                                             tenant=tenant, default=35),
            'amber_zone': get_exam_setting_int('exam.alert_amber_zone_percent',
                                               tenant=tenant, default=50),
        })
        return render(request, self.template_name, ctx)


# ===========================================================================
# UNDERPERFORMER ALERTS  /staff/analytics/underperformers/
# ===========================================================================
class UnderperformerListView(View):
    template_name = 'exams/admin_underperformers.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        tenant = getattr(admin_user, 'tenant', None)
        items = underperformers.find_underperformers(tenant=tenant)
        ctx = _exam_ctx(request, admin_user, active_page='underperformers',
                        page_title='Underperformer Alerts')
        ctx.update({
            'items': items,
            'fail_pct': get_exam_setting_int('exam.fail_threshold_percent', tenant=tenant, default=35),
            'need': get_exam_setting_int('exam.underperformer_fail_count', tenant=tenant, default=3),
            'window': get_exam_setting_int('exam.underperformer_window_size', tenant=tenant, default=5),
            'enabled': is_feature_enabled('exam.underperformer_alerts',
                                          tenant=tenant, user_type='ADMIN'),
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        tenant = getattr(admin_user, 'tenant', None)
        result = underperformers.scan_and_raise(tenant=tenant, request=request)
        messages.success(
            request,
            f'Scan complete. Found {result["found"]}, raised {result["raised"]} new alerts.',
        )
        return redirect('staff-underperformers')


# ===========================================================================
# REPORTS  /staff/analytics/exam-reports/
# ===========================================================================
class ExamReportsView(View):
    """Tabular performance report with red/amber flagging per student."""

    template_name = 'exams/admin_exam_reports.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        tenant = getattr(admin_user, 'tenant', None)
        red = get_exam_setting_int('exam.alert_red_zone_percent', tenant=tenant, default=35)
        amber = get_exam_setting_int('exam.alert_amber_zone_percent', tenant=tenant, default=50)

        qs = (TestAttempt.objects
              .filter(status__in=('EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'))
              .select_related('student', 'test'))
        if tenant is not None:
            qs = qs.filter(tenant=tenant)

        # filters
        test_f = request.GET.get('test') or ''
        if test_f:
            qs = qs.filter(test_id=test_f)

        attempts = list(qs.order_by('-submitted_at')[:1000])
        for a in attempts:
            p = float(a.percentage or 0)
            a.flag = 'RED' if p < red else ('AMBER' if p < amber else 'GREEN')

        # Aggregate per-test stats
        agg = (qs.values('test_id', 'test__test_code', 'test__title')
                 .annotate(n=Count('id'), avg=Avg('percentage'))
                 .order_by('-n'))

        ctx = _exam_ctx(request, admin_user, active_page='exam-reports',
                        page_title='Exam Reports')
        ctx.update({
            'attempts': attempts,
            'agg': agg,
            'red_zone': red,
            'amber_zone': amber,
            'tests': Test.objects.filter(is_deleted=False).order_by('-created_at')[:200],
            'selected_test': test_f,
        })
        return render(request, self.template_name, ctx)


def export_exam_report_csv(request):
    """CSV export of all evaluated attempts (RBAC-protected)."""
    admin_user, redir = _gate(request)
    if redir:
        return redir
    import csv
    tenant = getattr(admin_user, 'tenant', None)
    qs = (TestAttempt.objects
          .filter(status__in=('EVALUATED', 'SUBMITTED', 'AUTO_SUBMITTED'))
          .select_related('student', 'test')
          .order_by('-submitted_at'))
    if tenant is not None:
        qs = qs.filter(tenant=tenant)

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="exam_report.csv"'
    w = csv.writer(resp)
    w.writerow(['student_code', 'student_name', 'test_code', 'test_title',
                'attempt_no', 'submitted_at', 'percentage', 'result'])
    for a in qs[:5000]:
        s = a.student
        w.writerow([
            getattr(s, 'student_code', ''),
            f"{getattr(s, 'first_name', '')} {getattr(s, 'last_name', '')}".strip(),
            a.test.test_code, a.test.title,
            a.attempt_number,
            a.submitted_at.isoformat() if a.submitted_at else '',
            str(a.percentage or 0), a.result or '',
        ])
    return resp


# ===========================================================================
# THRESHOLD SETTINGS  /staff/analytics/thresholds/
# ===========================================================================
class ExamThresholdsView(View):
    """Edit the configurable thresholds (full admin only)."""

    template_name = 'exams/admin_exam_thresholds.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may edit thresholds.')
        rows = []
        for key, default, vtype, desc in EXAM_SETTINGS:
            row = SystemSetting.objects.filter(setting_key=key, tenant__isnull=True).first()
            rows.append({
                'key': key, 'desc': desc, 'value': row.setting_value if row else default,
                'default': default,
            })
        ctx = _exam_ctx(request, admin_user, active_page='exam-thresholds',
                        page_title='Exam Thresholds')
        ctx['rows'] = rows
        return render(request, self.template_name, ctx)

    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may edit thresholds.')
        old: dict = {}
        new: dict = {}
        for key, default, vtype, desc in EXAM_SETTINGS:
            new_val = (request.POST.get(key) or '').strip()
            if not new_val:
                continue
            row, _ = SystemSetting.objects.get_or_create(
                tenant=None, setting_key=key,
                defaults={'value_type': vtype, 'category': 'exams', 'description': desc},
            )
            old[key] = row.setting_value
            row.setting_value = new_val
            row.save(update_fields=['setting_value'])
            new[key] = new_val
        log_exam_event(
            request=request, actor=admin_user,
            action='THRESHOLDS_UPDATED', resource_type='SystemSetting',
            description='Exam thresholds updated', old_values=old, new_values=new,
        )
        messages.success(request, 'Thresholds saved.')
        return redirect('staff-exam-thresholds')
