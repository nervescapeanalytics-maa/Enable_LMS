"""
Test version control — JSON snapshot + restore.

A snapshot includes the Test row, all its TestSection rows, and all its
Question rows (without per-attempt history). Snapshots are immutable.

Restore semantics:

    - Only fields stored in the snapshot are touched on the live rows.
    - Sections / questions present in the snapshot but absent from the live
      DB are recreated with the original UUIDs (preserving FK links from
      attempts/answers).
    - Sections / questions that exist live but are missing from the
      snapshot are soft-deleted (``is_deleted=True`` for Question;
      hard-delete for TestSection — they have no historical FKs).
"""
from __future__ import annotations

import logging
import uuid as uuid_lib
from typing import Optional

from django.db import transaction

from .models import Question, Test, TestSection, TestVersion
from .permissions import log_exam_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field lists
# ---------------------------------------------------------------------------
TEST_FIELDS = [
    'test_code', 'title', 'description', 'test_type', 'access_mode',
    'status', 'total_questions', 'total_marks', 'total_duration_minutes',
    'passing_percent', 'start_datetime', 'end_datetime', 'published_at',
    'subject_id', 'chapter_id', 'batch_id',
    'max_attempts', 'show_correct_answers',
]

SECTION_FIELDS = [
    'section_name', 'section_order', 'subject_id', 'total_questions',
    'mandatory_questions', 'max_marks', 'duration_minutes', 'instructions',
]

QUESTION_FIELDS = [
    'question_code', 'question_text', 'question_text_html', 'question_image',
    'question_type', 'difficulty',
    'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
    'correct_answer', 'correct_answer_value', 'numerical_tolerance',
    'answer_explanation', 'positive_marks', 'negative_marks', 'partial_marks',
    'question_order', 'tags', 'is_active', 'is_deleted',
    'subject_id', 'chapter_id', 'topic_id', 'section_id',
]


def _model_dict(obj, fields):
    out = {}
    for f in fields:
        try:
            v = getattr(obj, f, None)
        except Exception:
            v = None
        if hasattr(v, 'isoformat'):
            v = v.isoformat()
        elif isinstance(v, uuid_lib.UUID):
            v = str(v)
        elif v.__class__.__name__ == 'Decimal':
            v = str(v)
        out[f] = v
    return out


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
@transaction.atomic
def take_snapshot(test: Test, *, actor=None, label: str = '', note: str = '',
                  request=None) -> TestVersion:
    """Persist a TestVersion for ``test``."""
    sections = list(TestSection.objects.filter(test=test).order_by('section_order'))
    questions = list(Question.objects.filter(test=test).order_by('question_order'))

    snapshot = {
        'test': {'id': str(test.id), **_model_dict(test, TEST_FIELDS)},
        'sections': [
            {'id': str(s.id), **_model_dict(s, SECTION_FIELDS)} for s in sections
        ],
        'questions': [
            {'id': str(q.id), **_model_dict(q, QUESTION_FIELDS)} for q in questions
        ],
    }
    summary = {
        'sections': len(sections),
        'questions': len(questions),
        'total_marks': str(test.total_marks or 0),
    }

    last = TestVersion.objects.filter(test=test).order_by('-version_number').first()
    n = (last.version_number if last else 0) + 1
    actor_name = ''
    actor_id = None
    if actor is not None:
        actor_name = f"{getattr(actor, 'first_name', '') or ''} {getattr(actor, 'last_name', '') or ''}".strip()
        actor_id = getattr(actor, 'id', None)

    v = TestVersion.objects.create(
        tenant=test.tenant, test=test,
        version_number=n, label=label[:200], note=note,
        snapshot=snapshot, summary=summary,
        created_by_id=actor_id, created_by_name=actor_name[:200],
    )
    log_exam_event(
        request=request, actor=actor,
        action='TEST_VERSION_SNAPSHOT',
        resource_type='Test', resource_id=test.id, resource_name=test.test_code,
        description=f'Snapshot v{n} taken — {label or "manual"}',
        extra_meta={'version_number': n, 'summary': summary},
    )
    return v


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
def _set_fields(obj, data, fields):
    for f in fields:
        if f not in data:
            continue
        setattr(obj, f, data.get(f))


@transaction.atomic
def restore_version(version: TestVersion, *, actor=None, request=None) -> Test:
    """
    Roll the live Test back to ``version``.

    Returns the refreshed Test instance.
    """
    snap = version.snapshot or {}
    test_snap = snap.get('test') or {}
    sec_snap = snap.get('sections') or []
    q_snap = snap.get('questions') or []

    test = Test.objects.select_for_update().get(id=version.test_id)
    pre_summary = {
        'sections': TestSection.objects.filter(test=test).count(),
        'questions': Question.objects.filter(test=test).count(),
    }

    # 1) Apply Test fields.
    _set_fields(test, test_snap, TEST_FIELDS)
    test.save()

    # 2) Reconcile sections (delete-and-recreate is safe — no historical FKs).
    sec_ids_in_snap = {s['id'] for s in sec_snap}
    TestSection.objects.filter(test=test).exclude(id__in=sec_ids_in_snap).delete()
    for s in sec_snap:
        sid = s.get('id')
        defaults = {k: s.get(k) for k in SECTION_FIELDS if k in s}
        TestSection.objects.update_or_create(
            id=sid, defaults={'tenant': test.tenant, 'test': test, **defaults},
        )

    # 3) Reconcile questions (soft-delete missing — preserves answer FKs).
    q_ids_in_snap = {q['id'] for q in q_snap}
    Question.objects.filter(test=test).exclude(id__in=q_ids_in_snap).update(
        is_active=False, is_deleted=True,
    )
    for q in q_snap:
        qid = q.get('id')
        defaults = {k: q.get(k) for k in QUESTION_FIELDS if k in q}
        Question.objects.update_or_create(
            id=qid, defaults={'tenant': test.tenant, 'test': test, **defaults},
        )

    test.refresh_from_db()
    log_exam_event(
        request=request, actor=actor,
        action='TEST_VERSION_RESTORE',
        resource_type='Test', resource_id=test.id, resource_name=test.test_code,
        description=f'Restored to v{version.version_number}',
        old_values=pre_summary, new_values=version.summary,
        severity='WARNING',
        extra_meta={'restored_version': version.version_number},
    )
    return test


# ---------------------------------------------------------------------------
# Diff (compact, for UI)
# ---------------------------------------------------------------------------
def diff_versions(va: TestVersion, vb: TestVersion) -> dict:
    """
    Return a small structured diff of the two snapshots:

        {
          'test':     {field: [a, b], ...},
          'sections': {'added': [...], 'removed': [...], 'changed': [...]},
          'questions': {'added': [...], 'removed': [...], 'changed': [...]},
        }
    """
    a = va.snapshot or {}
    b = vb.snapshot or {}

    def diff_dict(da, db):
        return {k: [da.get(k), db.get(k)] for k in set(da) | set(db) if da.get(k) != db.get(k)}

    def diff_collection(la, lb, label_field):
        ma = {x['id']: x for x in la}
        mb = {x['id']: x for x in lb}
        added = [{'id': i, 'label': mb[i].get(label_field, '')} for i in mb.keys() - ma.keys()]
        removed = [{'id': i, 'label': ma[i].get(label_field, '')} for i in ma.keys() - mb.keys()]
        changed = []
        for i in ma.keys() & mb.keys():
            d = diff_dict(ma[i], mb[i])
            if d:
                changed.append({'id': i, 'label': mb[i].get(label_field, ''), 'fields': d})
        return {'added': added, 'removed': removed, 'changed': changed}

    return {
        'test': diff_dict(a.get('test') or {}, b.get('test') or {}),
        'sections': diff_collection(a.get('sections') or [], b.get('sections') or [], 'section_name'),
        'questions': diff_collection(a.get('questions') or [], b.get('questions') or [], 'question_code'),
    }
