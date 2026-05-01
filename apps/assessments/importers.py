"""
Question bulk import — CSV / XLSX.

Public API:
    parse_rows(file, ext)             -> list[dict]
    validate_rows(rows, *, test, tenant) -> (cleaned, errors)
    apply_rows(rows, *, test, tenant, actor=None, request=None) -> dict

The "dry-run preview" UI feeds the user through ``parse_rows`` then
``validate_rows`` without ever calling ``apply_rows``.

Collision policy: **update on collision** (matched by ``question_code``
within the same ``test``). Wrapped in a single transaction.
"""
from __future__ import annotations

import csv
import io
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from django.db import transaction

from .models import Question, Test
from .permissions import log_exam_event

logger = logging.getLogger(__name__)


REQUIRED_COLS = [
    'question_code', 'question_text', 'question_type',
    'option_a', 'option_b', 'option_c', 'option_d',
    'correct_answer', 'positive_marks',
]
OPTIONAL_COLS = [
    'option_e', 'difficulty', 'negative_marks', 'partial_marks',
    'answer_explanation', 'question_order', 'tags',
]
ALL_COLS = REQUIRED_COLS + OPTIONAL_COLS

VALID_TYPES = {
    'MCQ_SINGLE', 'MCQ_MULTI', 'NUMERICAL', 'TRUE_FALSE',
    'FILL_BLANK', 'SUBJECTIVE', 'MATRIX_MATCH',
    'ASSERTION_REASON', 'COMPREHENSION',
}
VALID_DIFFICULTY = {'EASY', 'MEDIUM', 'HARD'}


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
def _parse_csv(blob: bytes) -> list[dict]:
    text = blob.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def _parse_xlsx(blob: bytes) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise RuntimeError('openpyxl not installed; cannot parse XLSX') from e
    wb = load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(c or '').strip() for c in next(rows)]
    except StopIteration:
        return []
    out = []
    for row in rows:
        if not row or all(c is None or str(c).strip() == '' for c in row):
            continue
        out.append({header[i]: ('' if c is None else str(c).strip())
                    for i, c in enumerate(row) if i < len(header)})
    return out


def parse_rows(file_obj, ext: str) -> list[dict]:
    blob = file_obj.read() if hasattr(file_obj, 'read') else bytes(file_obj)
    ext = (ext or '').lower().lstrip('.')
    if ext == 'csv':
        return _parse_csv(blob)
    if ext in ('xlsx', 'xls'):
        return _parse_xlsx(blob)
    raise ValueError(f'Unsupported file extension: {ext!r}')


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
def _to_decimal(v, default='0'):
    try:
        return Decimal(str(v).strip() or default)
    except (InvalidOperation, AttributeError):
        return None


def validate_rows(rows: list[dict], *, test: Test, tenant) -> tuple[list[dict], list[dict]]:
    """
    Return (cleaned_rows, errors).
    - cleaned_rows: dicts ready for ``apply_rows``, with an ``_action`` key
      ('create' or 'update') and ``_question_code`` (normalised).
    - errors: list of {row, code, message}.
    """
    cleaned: list[dict] = []
    errors: list[dict] = []

    existing_codes = set(
        Question.objects.filter(test=test, is_deleted=False)
        .values_list('question_code', flat=True)
    )
    seen: set[str] = set()

    for i, raw in enumerate(rows, start=1):
        row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v)
               for k, v in raw.items() if k}

        # required columns present
        missing = [c for c in REQUIRED_COLS if not row.get(c)]
        if missing:
            errors.append({'row': i, 'code': 'MISSING',
                           'message': f'missing: {", ".join(missing)}'})
            continue

        qcode = row['question_code'].strip()
        if qcode in seen:
            errors.append({'row': i, 'code': 'DUPLICATE_IN_FILE',
                           'message': f'question_code "{qcode}" repeated in file'})
            continue
        seen.add(qcode)

        qtype = row['question_type'].upper()
        if qtype not in VALID_TYPES:
            errors.append({'row': i, 'code': 'BAD_TYPE',
                           'message': f'question_type "{qtype}" invalid'})
            continue

        diff = (row.get('difficulty') or 'MEDIUM').upper()
        if diff not in VALID_DIFFICULTY:
            errors.append({'row': i, 'code': 'BAD_DIFFICULTY',
                           'message': f'difficulty "{diff}" invalid'})
            continue

        ans = row['correct_answer'].strip().upper()
        if qtype == 'MCQ_SINGLE':
            opts = {k.upper().split('_')[1]: row.get(k)
                    for k in ('option_a', 'option_b', 'option_c', 'option_d', 'option_e')
                    if row.get(k)}
            if ans not in opts:
                errors.append({'row': i, 'code': 'ANSWER_NOT_IN_OPTIONS',
                               'message': f'correct_answer "{ans}" not in provided options'})
                continue

        pos = _to_decimal(row.get('positive_marks'))
        if pos is None:
            errors.append({'row': i, 'code': 'BAD_MARKS',
                           'message': 'positive_marks must be numeric'})
            continue
        neg = _to_decimal(row.get('negative_marks') or '0') or Decimal('0')
        partial = _to_decimal(row.get('partial_marks') or '0') or Decimal('0')

        order_raw = row.get('question_order') or '0'
        try:
            order = int(float(order_raw))
        except (TypeError, ValueError):
            order = 0

        cleaned.append({
            '_question_code': qcode,
            '_action': 'update' if qcode in existing_codes else 'create',
            'question_code': qcode,
            'question_text': row['question_text'],
            'question_type': qtype,
            'difficulty': diff,
            'option_a': row.get('option_a') or None,
            'option_b': row.get('option_b') or None,
            'option_c': row.get('option_c') or None,
            'option_d': row.get('option_d') or None,
            'option_e': row.get('option_e') or None,
            'correct_answer': ans,
            'positive_marks': pos,
            'negative_marks': neg,
            'partial_marks': partial,
            'answer_explanation': row.get('answer_explanation') or '',
            'question_order': order,
        })
    return cleaned, errors


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
@transaction.atomic
def apply_rows(rows: list[dict], *, test: Test, tenant, actor=None,
               request=None) -> dict:
    created = updated = 0
    for r in rows:
        qcode = r.pop('_question_code')
        action = r.pop('_action')
        defaults = {'tenant': tenant, 'test': test, **r}
        obj, was_created = Question.objects.update_or_create(
            test=test, question_code=qcode, defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    # Recount
    test.total_questions = Question.objects.filter(test=test, is_deleted=False).count()
    test.total_marks = sum(
        (q.positive_marks or 0)
        for q in Question.objects.filter(test=test, is_deleted=False)
    )
    test.save(update_fields=['total_questions', 'total_marks'])

    log_exam_event(
        request=request, actor=actor,
        action='QUESTION_BULK_IMPORT',
        resource_type='Test', resource_id=test.id, resource_name=test.test_code,
        description=f'Imported {created + updated} rows ({created} new, {updated} updated)',
        extra_meta={'created': created, 'updated': updated},
    )
    return {'created': created, 'updated': updated, 'total': created + updated}


# ---------------------------------------------------------------------------
# Template (for download)
# ---------------------------------------------------------------------------
def template_csv() -> str:
    sample = {
        'question_code': 'IMP-001',
        'question_text': 'Capital of France?',
        'question_type': 'MCQ_SINGLE',
        'difficulty': 'EASY',
        'option_a': 'Berlin', 'option_b': 'Madrid',
        'option_c': 'Paris', 'option_d': 'Rome', 'option_e': '',
        'correct_answer': 'C',
        'positive_marks': '4', 'negative_marks': '-1', 'partial_marks': '0',
        'answer_explanation': 'Paris is the capital of France.',
        'question_order': '1', 'tags': 'geography',
    }
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=ALL_COLS)
    w.writeheader()
    w.writerow({k: sample.get(k, '') for k in ALL_COLS})
    return out.getvalue()
