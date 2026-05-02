"""
Exam authoring views (Phase 2).

These views replace the read-only `TestsView` and `QuestionsView` shipped in
`apps/core/admin_page_views.py` for the staff dashboard. Every view enforces
the role-based access rules from `assessments.permissions` and writes audit
events for state changes.

Routes (mounted under /staff/exams/ — see lms_enterprise.urls):
    /                            list tests
    new/                         create test (form)
    <uuid:test_id>/              detail (info + question list + sections)
    <uuid:test_id>/edit/         edit test
    <uuid:test_id>/publish/      publish (POST)
    <uuid:test_id>/unpublish/    revert to draft (POST)
    <uuid:test_id>/archive/      archive (POST)
    <uuid:test_id>/delete/       soft-delete (POST, full admin only)
    <uuid:test_id>/sections/new/        add section
    <uuid:test_id>/questions/new/       create question attached to this test
    questions/                   question bank
    questions/new/               create question (floating in bank)
    questions/<uuid:qid>/edit/   edit question
    questions/<uuid:qid>/delete/ soft-delete question (POST)
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

from assessments.models import (
    Test, TestSection, Question, TestAttempt,
)
from assessments.permissions import (
    EXAM_FEATURE_FLAGS,
    get_logged_in_admin,
    is_admin_full,
    can_manage_exams,
    log_exam_event,
    is_feature_enabled,
)
from assessments.views.forms import TestForm, QuestionForm, TestSectionForm
from system_config.models import FeatureFlag


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Common gating
# ---------------------------------------------------------------------------

def _gate(request):
    """Centralised gate. Returns (admin_user_or_None, redirect_or_None).

    Accepts three auth paths:
      1. Django superuser logged in via `/admin/` (overrides any stale legacy session).
      2. Legacy session-based ADMIN auth (`session['user_type'] == 'ADMIN'`).
      3. Otherwise, blocks TEACHER and unauthenticated callers.
    """
    # Path 1 — Django superuser/staff coming from /admin/ context.
    dj_user = getattr(request, 'user', None)
    if dj_user is not None and dj_user.is_authenticated and (
        dj_user.is_superuser or dj_user.is_staff
    ):
        from accounts.models import Admin
        admin_user = None
        email = getattr(dj_user, 'email', '') or ''
        if email:
            admin_user = Admin.objects.filter(email__iexact=email).first()
        if admin_user is None:
            admin_user = Admin.objects.order_by('created_at').first()
        if admin_user is not None:
            return admin_user, None

    # Path 2/3 — legacy session-based.
    if request.session.get('user_type') == 'TEACHER':
        return None, _forbidden(request, 'Teachers cannot access the exams module.')
    admin_user = get_logged_in_admin(request)
    if admin_user is None:
        return None, redirect('/login/?role=admin&next=' + request.get_full_path())
    if not can_manage_exams(admin_user):
        return None, _forbidden(request, 'Insufficient permissions.')
    return admin_user, None


def _forbidden(request, msg):
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'error': msg}, status=403)
    return render(request, '403.html', {'reason': msg}, status=403)


def _exam_ctx(request, admin_user, active_page='exams', page_title='Exams', breadcrumb_parent='Exams & Assessments'):
    """Lightweight context — mirrors `_admin_ctx` shape used by admin_base.html."""
    from accounts.models import Admin  # noqa
    from academics.models import Users
    from communication.models import SupportTicket
    from classes.models import ScheduledClass

    user_name = request.session.get('user_name') or 'Admin'
    initials = ''.join(w[0].upper() for w in user_name.split()[:2]) or 'A'

    try:
        live = ScheduledClass.objects.filter(status='LIVE').count()
    except Exception:
        live = 0
    try:
        open_tickets = SupportTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS', 'PENDING']).count()
    except Exception:
        open_tickets = 0

    return {
        'user_name': user_name,
        'user_type': request.session.get('user_type', 'ADMIN'),
        'user_id': request.session.get('user_id', ''),
        'user_email': request.session.get('user_email', ''),
        'user_initials': initials,
        'active_page': active_page,
        'page_title': page_title,
        'breadcrumb_parent': breadcrumb_parent,
        'breadcrumb_parent_url': '/staff/exams/',
        'breadcrumb_active': page_title,
        'sidebar_counts': {
            'students': Users.objects.filter(is_active=True).count(),
            'teachers': 0,
            'tests': Test.objects.filter(is_deleted=False).count(),
            'live_classes': live,
            'open_tickets': open_tickets,
        },
        'notifications': [],
        'notifications_count': 0,
        'is_admin_full': is_admin_full(admin_user),
        'admin_user_id': str(admin_user.id),
    }


# ---------------------------------------------------------------------------
# Test list / detail / create / edit
# ---------------------------------------------------------------------------

class ExamListView(View):
    template_name = 'exams/admin_exam_list.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir

        qs = Test.objects.filter(is_deleted=False)
        # status filter
        status_f = request.GET.get('status') or ''
        if status_f:
            qs = qs.filter(status=status_f)
        # text search
        q = (request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(test_code__icontains=q))
        type_f = request.GET.get('type') or ''
        if type_f:
            qs = qs.filter(test_type=type_f)

        tests = list(qs.select_related('subject', 'batch').order_by('-created_at')[:500])

        # attempts per test (single query)
        attempt_counts = dict(
            TestAttempt.objects.filter(test_id__in=[t.id for t in tests])
            .values_list('test_id').annotate(c=Count('id'))
            .values_list('test_id', 'c')
        )

        rows = []
        for t in tests:
            rows.append({
                'id': str(t.id),
                'title': t.title,
                'code': t.test_code or '',
                'type': t.get_test_type_display(),
                'subject': str(t.subject) if t.subject else '—',
                'batch': str(t.batch) if t.batch else '—',
                'duration': t.total_duration_minutes,
                'total_marks': t.total_marks,
                'total_questions': t.total_questions,
                'attempts': attempt_counts.get(t.id, 0),
                'status': t.status,
                'status_label': t.get_status_display(),
                'created': t.created_at.strftime('%d %b %Y'),
                'start': t.start_datetime.strftime('%d %b %Y %H:%M') if t.start_datetime else '',
            })

        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title='Exams')
        all_total = Test.objects.filter(is_deleted=False).count()
        ctx.update({
            'tests': rows,
            'filters': {'status': status_f, 'type': type_f, 'q': q},
            'status_choices': Test.TestStatus.choices,
            'type_choices': Test.TestType.choices,
            'count_total': all_total,
            'count_published': Test.objects.filter(is_deleted=False, status=Test.TestStatus.PUBLISHED).count(),
            'count_drafts': Test.objects.filter(is_deleted=False, status=Test.TestStatus.DRAFT).count(),
            'count_archived': Test.objects.filter(is_deleted=False, status=Test.TestStatus.ARCHIVED).count(),
        })
        return render(request, self.template_name, ctx)


class ExamCreateView(View):
    template_name = 'exams/admin_exam_form.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        form = TestForm(tenant=admin_user.tenant)
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title='Create Exam')
        ctx.update({'form': form, 'mode': 'create'})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        form = TestForm(request.POST, tenant=admin_user.tenant)
        if form.is_valid():
            test = form.save(commit=False)
            test.tenant = admin_user.tenant
            test.created_by = admin_user.id
            test.created_by_type = 'ADMIN'
            test.status = Test.TestStatus.DRAFT
            test.save()
            log_exam_event(
                request=request, actor=admin_user,
                action='CREATE', resource_type='Test',
                resource_id=test.id, resource_name=test.test_code or test.title,
                description=f'Created exam {test.test_code} - {test.title}',
                new_values={'title': test.title, 'status': test.status},
            )
            messages.success(request, f'Exam "{test.title}" created as draft.')
            return redirect(f'/staff/exams/{test.id}/')
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title='Create Exam')
        ctx.update({'form': form, 'mode': 'create'})
        return render(request, self.template_name, ctx)


class ExamEditView(View):
    template_name = 'exams/admin_exam_form.html'

    def get(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        form = TestForm(instance=test, tenant=admin_user.tenant)
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title=f'Edit: {test.title}')
        ctx.update({'form': form, 'test': test, 'mode': 'edit'})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        old_snapshot = {
            'title': test.title, 'status': test.status,
            'duration': test.total_duration_minutes, 'total_marks': str(test.total_marks),
        }
        form = TestForm(request.POST, instance=test, tenant=admin_user.tenant)
        if form.is_valid():
            form.save()
            log_exam_event(
                request=request, actor=admin_user,
                action='UPDATE', resource_type='Test',
                resource_id=test.id, resource_name=test.test_code or test.title,
                description=f'Updated exam {test.test_code}',
                old_values=old_snapshot,
                new_values={'title': test.title, 'status': test.status},
            )
            messages.success(request, 'Exam updated.')
            return redirect(f'/staff/exams/{test.id}/')
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title=f'Edit: {test.title}')
        ctx.update({'form': form, 'test': test, 'mode': 'edit'})
        return render(request, self.template_name, ctx)


class ExamDetailView(View):
    template_name = 'exams/admin_exam_detail.html'

    def get(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        sections = list(test.sections.all().order_by('section_order'))
        questions = list(
            Question.objects.filter(test=test, is_deleted=False)
            .select_related('subject', 'chapter', 'section')
            .order_by('question_order')
        )
        attempts = TestAttempt.objects.filter(test=test)
        attempt_stats = {
            'total': attempts.count(),
            'avg_score': float(attempts.aggregate(a=Avg('percentage'))['a'] or 0),
            'passed': attempts.filter(result='PASS').count(),
        }
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title=test.title)
        ctx.update({
            'test': test,
            'sections': sections,
            'questions': questions,
            'attempt_stats': attempt_stats,
            'can_publish': test.status == Test.TestStatus.DRAFT and questions and is_admin_full(admin_user),
            'can_unpublish': test.status == Test.TestStatus.PUBLISHED and is_admin_full(admin_user),
            'can_delete': is_admin_full(admin_user),
        })
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Lifecycle actions (POST-only, return redirect)
# ---------------------------------------------------------------------------

class ExamPublishView(View):
    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may publish exams.')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)

        # Validate publishability
        qcount = Question.objects.filter(test=test, is_deleted=False).count()
        if qcount == 0:
            messages.error(request, 'Cannot publish: exam has no questions.')
            return redirect(f'/staff/exams/{test.id}/')
        if test.total_duration_minutes <= 0:
            messages.error(request, 'Cannot publish: duration must be > 0.')
            return redirect(f'/staff/exams/{test.id}/')

        # Recompute total_marks from positive_marks of questions if zero
        if not test.total_marks or float(test.total_marks) <= 0:
            from django.db.models import Sum
            total = Question.objects.filter(test=test, is_deleted=False).aggregate(s=Sum('positive_marks'))['s'] or 0
            test.total_marks = total

        test.total_questions = qcount
        test.status = Test.TestStatus.PUBLISHED
        test.published_at = timezone.now()
        test.published_by = admin_user.id
        test.save()
        log_exam_event(
            request=request, actor=admin_user,
            action='UPDATE', resource_type='Test',
            resource_id=test.id, resource_name=test.test_code or test.title,
            description=f'Published exam {test.test_code}',
            new_values={'status': test.status, 'published_at': str(test.published_at)},
            severity='INFO',
        )
        messages.success(request, f'Exam "{test.title}" is now PUBLISHED.')
        return redirect(f'/staff/exams/{test.id}/')


class ExamUnpublishView(View):
    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may unpublish exams.')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        prev = test.status
        test.status = Test.TestStatus.DRAFT
        test.save()
        log_exam_event(
            request=request, actor=admin_user,
            action='UPDATE', resource_type='Test',
            resource_id=test.id, resource_name=test.test_code or test.title,
            description=f'Unpublished exam {test.test_code}',
            old_values={'status': prev}, new_values={'status': test.status},
            severity='WARNING',
        )
        messages.success(request, 'Exam reverted to DRAFT.')
        return redirect(f'/staff/exams/{test.id}/')


class ExamArchiveView(View):
    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        prev = test.status
        test.status = Test.TestStatus.ARCHIVED
        test.save()
        log_exam_event(
            request=request, actor=admin_user,
            action='UPDATE', resource_type='Test',
            resource_id=test.id, resource_name=test.test_code or test.title,
            description=f'Archived exam {test.test_code}',
            old_values={'status': prev}, new_values={'status': test.status},
        )
        messages.success(request, 'Exam archived.')
        return redirect(f'/staff/exams/{test.id}/')


class ExamDeleteView(View):
    """Soft-delete only. Hard-delete reserved for DB admin."""
    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may delete exams.')
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        test.is_deleted = True
        test.save()
        log_exam_event(
            request=request, actor=admin_user,
            action='DELETE', resource_type='Test',
            resource_id=test.id, resource_name=test.test_code or test.title,
            description=f'Soft-deleted exam {test.test_code}',
            severity='WARNING',
        )
        messages.success(request, 'Exam deleted.')
        return redirect('/staff/exams/')


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

class ExamSectionCreateView(View):
    template_name = 'exams/admin_section_form.html'

    def get(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        form = TestSectionForm(tenant=admin_user.tenant)
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title=f'Add Section — {test.title}')
        ctx.update({'form': form, 'test': test})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request, test_id):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        test = get_object_or_404(Test, id=test_id, is_deleted=False)
        form = TestSectionForm(request.POST, tenant=admin_user.tenant)
        if form.is_valid():
            sec = form.save(commit=False)
            sec.tenant = admin_user.tenant
            sec.test = test
            sec.save()
            log_exam_event(
                request=request, actor=admin_user,
                action='CREATE', resource_type='TestSection',
                resource_id=sec.id, resource_name=sec.section_name,
                description=f'Added section "{sec.section_name}" to exam {test.test_code}',
            )
            messages.success(request, f'Section "{sec.section_name}" added.')
            return redirect(f'/staff/exams/{test.id}/')
        ctx = _exam_ctx(request, admin_user, active_page='exams', page_title=f'Add Section — {test.title}')
        ctx.update({'form': form, 'test': test})
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

class QuestionListView(View):
    template_name = 'exams/admin_question_list.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        qs = Question.objects.filter(is_deleted=False)
        q = (request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(question_text__icontains=q) | Q(question_code__icontains=q))
        qtype = request.GET.get('type') or ''
        if qtype:
            qs = qs.filter(question_type=qtype)
        diff = request.GET.get('difficulty') or ''
        if diff:
            qs = qs.filter(difficulty=diff)
        questions = list(qs.select_related('subject', 'chapter', 'test').order_by('-created_at')[:500])

        ctx = _exam_ctx(request, admin_user, active_page='questions', page_title='Question Bank')
        ctx.update({
            'questions': questions,
            'filters': {'q': q, 'type': qtype, 'difficulty': diff},
            'type_choices': Question.QuestionType.choices,
            'difficulty_choices': Question.Difficulty.choices,
            'count_total': Question.objects.filter(is_deleted=False).count(),
            'count_active': Question.objects.filter(is_deleted=False, is_active=True).count(),
        })
        return render(request, self.template_name, ctx)


class QuestionCreateView(View):
    template_name = 'exams/admin_question_form.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        default_test = None
        test_id = request.GET.get('test')
        if test_id:
            default_test = Test.objects.filter(id=test_id, is_deleted=False).first()
        form = QuestionForm(tenant=admin_user.tenant, default_test=default_test)
        ctx = _exam_ctx(request, admin_user, active_page='questions', page_title='Create Question')
        ctx.update({'form': form, 'mode': 'create', 'default_test': default_test})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        form = QuestionForm(request.POST, tenant=admin_user.tenant)
        if form.is_valid():
            q = form.save(commit=False)
            q.tenant = admin_user.tenant
            q.is_active = True
            q.save()
            # Recompute test.total_questions
            if q.test_id:
                q.test.total_questions = Question.objects.filter(test=q.test, is_deleted=False).count()
                q.test.save(update_fields=['total_questions', 'updated_at'])
            log_exam_event(
                request=request, actor=admin_user,
                action='CREATE', resource_type='Question',
                resource_id=q.id, resource_name=q.question_code or '',
                description=f'Created question ({q.question_type}) attached to test={q.test_id}',
            )
            messages.success(request, 'Question created.')
            if q.test_id:
                return redirect(f'/staff/exams/{q.test_id}/')
            return redirect('/staff/exams/questions/')
        ctx = _exam_ctx(request, admin_user, active_page='questions', page_title='Create Question')
        ctx.update({'form': form, 'mode': 'create'})
        return render(request, self.template_name, ctx)


class QuestionEditView(View):
    template_name = 'exams/admin_question_form.html'

    def get(self, request, qid):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        question = get_object_or_404(Question, id=qid, is_deleted=False)
        form = QuestionForm(instance=question, tenant=admin_user.tenant)
        ctx = _exam_ctx(request, admin_user, active_page='questions', page_title='Edit Question')
        ctx.update({'form': form, 'question': question, 'mode': 'edit'})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request, qid):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        question = get_object_or_404(Question, id=qid, is_deleted=False)
        old_test_id = question.test_id
        form = QuestionForm(request.POST, instance=question, tenant=admin_user.tenant)
        if form.is_valid():
            q = form.save()
            # If test changed, recount both
            from assessments.models import Test as _T
            for tid in {old_test_id, q.test_id}:
                if tid:
                    cnt = Question.objects.filter(test_id=tid, is_deleted=False).count()
                    _T.objects.filter(id=tid).update(total_questions=cnt, updated_at=timezone.now())
            log_exam_event(
                request=request, actor=admin_user,
                action='UPDATE', resource_type='Question',
                resource_id=q.id, resource_name=q.question_code or '',
                description=f'Updated question ({q.question_type})',
            )
            messages.success(request, 'Question updated.')
            if q.test_id:
                return redirect(f'/staff/exams/{q.test_id}/')
            return redirect('/staff/exams/questions/')
        ctx = _exam_ctx(request, admin_user, active_page='questions', page_title='Edit Question')
        ctx.update({'form': form, 'question': question, 'mode': 'edit'})
        return render(request, self.template_name, ctx)


class QuestionDeleteView(View):
    @method_decorator(csrf_protect)
    def post(self, request, qid):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        question = get_object_or_404(Question, id=qid, is_deleted=False)
        old_test_id = question.test_id
        question.is_deleted = True
        question.save()
        if old_test_id:
            cnt = Question.objects.filter(test_id=old_test_id, is_deleted=False).count()
            Test.objects.filter(id=old_test_id).update(total_questions=cnt, updated_at=timezone.now())
        log_exam_event(
            request=request, actor=admin_user,
            action='DELETE', resource_type='Question',
            resource_id=question.id, resource_name=question.question_code or '',
            description='Soft-deleted question',
            severity='WARNING',
        )
        messages.success(request, 'Question deleted.')
        if old_test_id:
            return redirect(f'/staff/exams/{old_test_id}/')
        return redirect('/staff/exams/questions/')


# ---------------------------------------------------------------------------
# Feature flags admin (per requirement: admin can toggle flags from this module)
# ---------------------------------------------------------------------------

class ExamFeatureFlagsView(View):
    template_name = 'exams/admin_feature_flags.html'

    def get(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may toggle feature flags.')
        flags = list(FeatureFlag.objects.filter(flag_key__startswith='exam.', tenant__isnull=True)
                     .order_by('flag_key'))
        ctx = _exam_ctx(request, admin_user, active_page='exam-flags', page_title='Exam Feature Flags')
        ctx.update({'flags': flags})
        return render(request, self.template_name, ctx)

    @method_decorator(csrf_protect)
    def post(self, request):
        admin_user, redir = _gate(request)
        if redir:
            return redir
        if not is_admin_full(admin_user):
            return _forbidden(request, 'Only full admins may toggle feature flags.')
        flag_key = request.POST.get('flag_key', '')
        if not flag_key.startswith('exam.'):
            return JsonResponse({'error': 'Invalid flag'}, status=400)
        try:
            flag = FeatureFlag.objects.get(flag_key=flag_key, tenant__isnull=True)
        except FeatureFlag.DoesNotExist:
            return JsonResponse({'error': 'Flag not found'}, status=404)
        prev = flag.is_enabled
        flag.is_enabled = (request.POST.get('is_enabled') == '1')
        flag.save()
        log_exam_event(
            request=request, actor=admin_user,
            action='SETTINGS_CHANGE', resource_type='FeatureFlag',
            resource_id=flag.id, resource_name=flag.flag_key,
            description=f'Toggled {flag.flag_key} from {prev} to {flag.is_enabled}',
            old_values={'is_enabled': prev}, new_values={'is_enabled': flag.is_enabled},
            is_security_event=True,
        )
        return JsonResponse({'ok': True, 'is_enabled': flag.is_enabled})
