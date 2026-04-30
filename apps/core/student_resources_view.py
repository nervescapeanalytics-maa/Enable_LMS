"""
Student E-Books & Resources — server-rendered Django view.

Replaces the React SPA's /student/dashboard/resources route which renders
hardcoded NCERT demo data.

Routes:
    /student/resources/                   All published study materials
    /student/resources/?subject=physics   Filtered by subject
    /student/resources/?type=EBOOK        Filtered by material type
    /student/resources/<id>/view/         Open file for viewing
    /student/resources/<id>/download/     Download file (logs MaterialAccess)

Data source: materials.StudyMaterial table (admin: /admin/materials/studymaterial/)
Auth: session['user_type'] == 'STUDENT'
"""
from __future__ import annotations

import logging

from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import Student
from academics.models import Subject
from materials.models import MaterialAccess, StudyMaterial
from core.student_exam_views import _require_student, _student_batch_ids

logger = logging.getLogger(__name__)


def _visible_materials_qs(student: Student):
    """Return StudyMaterial queryset visible to this student.

    Visibility rules:
      - tenant match
      - is_published=True, is_active=True, is_deleted=False
      - target_audience IN ('STUDENT', 'ALL')
      - allowed_batches empty (= all) OR student's batch in allowed_batches
    """
    batch_ids = _student_batch_ids(student)
    batch_id_strs = [str(b) for b in batch_ids]

    qs = StudyMaterial.objects.filter(
        tenant=student.tenant,
        is_published=True,
        is_active=True,
        is_deleted=False,
        target_audience__in=['STUDENT', 'ALL'],
    ).select_related('subject', 'chapter')

    # Batch filter: allowed_batches empty → visible to all; otherwise must include student's batch
    batch_q = Q(allowed_batches=[]) | Q(allowed_batches__isnull=True)
    for bid in batch_id_strs:
        batch_q |= Q(allowed_batches__contains=[bid])
    qs = qs.filter(batch_q)

    return qs.distinct().order_by('-published_at', '-created_at')


def _format_size(bytes_val):
    if not bytes_val:
        return ''
    if bytes_val < 1024:
        return f'{bytes_val} B'
    if bytes_val < 1024 * 1024:
        return f'{bytes_val / 1024:.1f} KB'
    if bytes_val < 1024 * 1024 * 1024:
        return f'{bytes_val / (1024 * 1024):.1f} MB'
    return f'{bytes_val / (1024 * 1024 * 1024):.2f} GB'


def _serialize_material(m: StudyMaterial):
    return {
        'id': str(m.id),
        'title': m.title,
        'description': m.description or '',
        'material_code': m.material_code or '',
        'material_type': m.material_type,
        'material_type_label': m.get_material_type_display(),
        'subject_name': m.subject.name if m.subject else '',
        'chapter_name': m.chapter.name if m.chapter else '',
        'thumbnail_url': m.thumbnail_url or '',
        'file_url': m.file_url or m.video_url or '',
        'file_name': m.file_name or '',
        'file_size': _format_size(m.file_size_bytes),
        'is_downloadable': m.is_downloadable,
        'view_count': m.view_count,
        'download_count': m.download_count,
        'difficulty': m.get_difficulty_level_display() if m.difficulty_level else '',
        'uploaded_by_name': m.uploaded_by_name or '',
        'published_at': m.published_at,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class ResourceListView(View):
    """E-Books & Resources list."""
    template_name = 'student/resources.html'

    def get(self, request):
        if request.session.get('user_type') != 'STUDENT':
            return redirect('/login/?role=student')

        student = _require_student(request)
        if student is None:
            return redirect('/login/?role=student')

        qs = _visible_materials_qs(student)

        # Filters
        subject_filter = request.GET.get('subject', '').strip()
        type_filter = request.GET.get('type', '').strip().upper()
        search = request.GET.get('q', '').strip()

        if subject_filter:
            qs = qs.filter(subject__name__iexact=subject_filter)
        if type_filter and type_filter in dict(StudyMaterial.MaterialType.choices):
            qs = qs.filter(material_type=type_filter)
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(material_code__icontains=search)
            )

        materials = [_serialize_material(m) for m in qs[:200]]

        # Build subject filter options from accessible subjects
        subject_names = sorted({m['subject_name'] for m in materials if m['subject_name']})

        # Stats
        total_count = len(materials)
        type_counts = {}
        for m in materials:
            t = m['material_type']
            type_counts[t] = type_counts.get(t, 0) + 1

        user_name = (
            f"{student.first_name} {student.last_name}".strip()
            or student.phone_number or 'Student'
        )

        return render(request, self.template_name, {
            'materials': materials,
            'total_count': total_count,
            'type_counts': type_counts,
            'subjects': subject_names,
            'subject_filter': subject_filter,
            'type_filter': type_filter,
            'search': search,
            'material_types': StudyMaterial.MaterialType.choices,
            'user_name': user_name,
        })


class ResourceViewAction(View):
    """Log VIEW action and redirect to file URL."""

    def get(self, request, material_id):
        if request.session.get('user_type') != 'STUDENT':
            return redirect('/login/?role=student')

        student = _require_student(request)
        if student is None:
            return redirect('/login/?role=student')

        material = get_object_or_404(
            StudyMaterial,
            id=material_id, tenant=student.tenant,
            is_published=True, is_deleted=False,
        )

        # Log access
        try:
            MaterialAccess.objects.create(
                tenant=student.tenant,
                material=material,
                user_id=student.id,
                user_type='STUDENT',
                action='VIEW',
            )
            StudyMaterial.objects.filter(id=material.id).update(
                view_count=material.view_count + 1
            )
        except Exception as exc:
            logger.warning('material view log failed: %s', exc)

        url = material.file_url or material.video_url or material.video_embed_url
        if not url:
            return redirect('/student/resources/')
        return HttpResponseRedirect(url)


class ResourceDownloadAction(View):
    """Log DOWNLOAD action and redirect to file URL."""

    def get(self, request, material_id):
        if request.session.get('user_type') != 'STUDENT':
            return redirect('/login/?role=student')

        student = _require_student(request)
        if student is None:
            return redirect('/login/?role=student')

        material = get_object_or_404(
            StudyMaterial,
            id=material_id, tenant=student.tenant,
            is_published=True, is_deleted=False,
        )

        if not material.is_downloadable:
            return redirect('/student/resources/')

        try:
            MaterialAccess.objects.create(
                tenant=student.tenant,
                material=material,
                user_id=student.id,
                user_type='STUDENT',
                action='DOWNLOAD',
            )
            StudyMaterial.objects.filter(id=material.id).update(
                download_count=material.download_count + 1
            )
        except Exception as exc:
            logger.warning('material download log failed: %s', exc)

        url = material.file_url or material.video_url
        if not url:
            return redirect('/student/resources/')
        return HttpResponseRedirect(url)
