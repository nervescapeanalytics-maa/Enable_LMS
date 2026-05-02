"""
Question bulk import — CSV / XLSX / ZIP.

Public API:
    parse_rows(file, ext)             -> list[dict]
    validate_rows(rows, *, test, tenant) -> (cleaned, errors)
    apply_rows(rows, *, test, tenant, actor=None, request=None) -> dict

The "dry-run preview" UI feeds the user through ``parse_rows`` then
``validate_rows`` without ever calling ``apply_rows``.

Collision policy: **update on collision** (matched by ``question_code``
within the same ``test``). Wrapped in a single transaction.

ZIP layout (expected):
    questions.xlsx        (or questions.csv)   — required
    images/               (optional)           — referenced by columns
                                                  ``question_image``,
                                                  ``option_a_image`` …
                                                  ``option_e_image``
                                                  using filenames like
                                                  ``q1.png`` (relative).
"""
from __future__ import annotations

import csv
import io
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional

from django.conf import settings
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
    'question_image', 'option_a_image', 'option_b_image',
    'option_c_image', 'option_d_image', 'option_e_image',
]
ALL_COLS = REQUIRED_COLS + OPTIONAL_COLS

# Columns whose value (when imported from a ZIP) is a relative filename
# inside the ZIP that we publish as a media URL on the Question record.
IMAGE_COLS = (
    'question_image',
    'option_a_image', 'option_b_image', 'option_c_image',
    'option_d_image', 'option_e_image',
)

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
    if ext == 'zip':
        rows, _images_dir = _parse_zip(blob, register=False)
        return rows
    raise ValueError(f'Unsupported file extension: {ext!r}')


# ---------------------------------------------------------------------------
# ZIP support
# ---------------------------------------------------------------------------
ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}


def _parse_zip(blob: bytes, *, register: bool) -> tuple[list[dict], dict]:
    """Extract a ZIP and return (rows, image_url_map).

    The ZIP must contain exactly one of:
        questions.xlsx, questions.csv, *.xlsx, *.csv

    Image references in IMAGE_COLS are resolved to entries within the ZIP
    (case-insensitive, slash-tolerant). When ``register`` is True, image
    payloads are written under MEDIA_ROOT/question_images/<uuid>/<basename>
    and the row column is rewritten to the corresponding /media/... URL.

    On register=False, image columns are returned as-is (filenames).
    """
    rows: list[dict] = []
    image_url_map: dict[str, str] = {}

    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as e:
        raise ValueError(f'Invalid ZIP archive: {e}') from e

    # Find the spreadsheet
    names = [n for n in zf.namelist() if not n.endswith('/')]
    sheet_name = None
    # Prefer canonical names
    for cand in ('questions.xlsx', 'questions.csv'):
        for n in names:
            if Path(n).name.lower() == cand:
                sheet_name = n
                break
        if sheet_name:
            break
    if not sheet_name:
        for n in names:
            low = n.lower()
            if low.endswith('.xlsx') or low.endswith('.csv'):
                sheet_name = n
                break
    if not sheet_name:
        raise ValueError('ZIP must contain a questions.xlsx or questions.csv')

    sheet_blob = zf.read(sheet_name)
    if sheet_name.lower().endswith('.csv'):
        rows = _parse_csv(sheet_blob)
    else:
        rows = _parse_xlsx(sheet_blob)

    # Build a case-insensitive basename → zip-entry map for image lookup
    by_basename: dict[str, str] = {}
    for n in names:
        if n == sheet_name:
            continue
        ext = Path(n).suffix.lower()
        if ext in ALLOWED_IMAGE_EXTS:
            by_basename[Path(n).name.lower()] = n

    if not register:
        zf.close()
        return rows, image_url_map

    # Persist images on disk under MEDIA_ROOT/question_images/<batch>/
    media_root = Path(getattr(settings, 'MEDIA_ROOT', 'runtime/media'))
    media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
    batch_dir_name = uuid.uuid4().hex[:12]
    target_dir = media_root / 'question_images' / batch_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        for col in IMAGE_COLS:
            ref = (row.get(col) or '').strip()
            if not ref:
                continue
            # Resolve by basename (also accept full zip paths)
            base = Path(ref).name.lower()
            zip_entry = by_basename.get(base)
            if not zip_entry:
                # If they wrote a full path with slashes, try a strict match
                norm = ref.replace('\\', '/').lstrip('/').lower()
                for n in names:
                    if n.lower() == norm:
                        zip_entry = n
                        break
            if not zip_entry:
                continue  # validate phase will not flag — image is optional

            cached = image_url_map.get(zip_entry)
            if not cached:
                safe_name = Path(zip_entry).name
                # Sanitise filename (avoid path traversal)
                safe_name = safe_name.replace('/', '_').replace('\\', '_')
                out_path = target_dir / safe_name
                with zf.open(zip_entry) as src, open(out_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                cached = f'{media_url}/question_images/{batch_dir_name}/{safe_name}'
                image_url_map[zip_entry] = cached
            row[col] = cached

    zf.close()
    return rows, image_url_map


def parse_zip_with_assets(file_obj) -> list[dict]:
    """Convenience wrapper used by views that want image extraction."""
    blob = file_obj.read() if hasattr(file_obj, 'read') else bytes(file_obj)
    rows, _ = _parse_zip(blob, register=True)
    return rows


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
            # Image URLs (already resolved to /media/... by parse_zip_with_assets,
            # or empty when CSV/XLSX direct)
            'question_image': row.get('question_image') or None,
            'option_a_image': row.get('option_a_image') or None,
            'option_b_image': row.get('option_b_image') or None,
            'option_c_image': row.get('option_c_image') or None,
            'option_d_image': row.get('option_d_image') or None,
            'option_e_image': row.get('option_e_image') or None,
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
