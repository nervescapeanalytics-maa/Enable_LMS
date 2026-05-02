"""
Phase 4 — importer unit + integration tests.

Covers:
  - parse_rows: CSV header row → dicts; XLSX (in-memory)
  - validate_rows: missing required column → error
  - validate_rows: duplicate question_code within file → error
  - validate_rows: invalid question_type → error
  - validate_rows: MCQ_SINGLE with correct_answer not in options → error
  - validate_rows: positive_marks not numeric → error
  - validate_rows: clean row → action 'create' or 'update'
  - apply_rows: creates new Questions, updates existing, recounts test totals
  - apply_rows: writes audit log QUESTION_BULK_IMPORT
  - template_csv: returns valid CSV with ALL_COLS headers
"""
from __future__ import annotations

import csv
import io
from decimal import Decimal

import pytest

from assessments.importers import (
    ALL_COLS, REQUIRED_COLS,
    parse_rows, validate_rows, apply_rows, template_csv,
)
from assessments.models import Question, Test
from audit.models import AuditLog
from tenants.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='IMP_T1', name='Import Tenant', subdomain='imp1')


@pytest.fixture
def test_obj(db, tenant):
    return Test.objects.create(
        tenant=tenant, test_code='IMP-TST', title='Import Test',
        test_type='PRACTICE', access_mode='OPEN', status='DRAFT',
        total_questions=0, total_marks=0, total_duration_minutes=20,
    )


def _make_csv(**overrides) -> io.BytesIO:
    base = {
        'question_code': 'Q001',
        'question_text': '2+2?',
        'question_type': 'MCQ_SINGLE',
        'option_a': 'Three', 'option_b': 'Four', 'option_c': 'Five', 'option_d': 'Six', 'option_e': '',
        'correct_answer': 'B',
        'positive_marks': '4', 'negative_marks': '-1', 'partial_marks': '0',
        'difficulty': 'EASY',
        'answer_explanation': '', 'question_order': '1', 'tags': '',
    }
    base.update(overrides)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=ALL_COLS)
    w.writeheader()
    w.writerow({k: base.get(k, '') for k in ALL_COLS})
    return io.BytesIO(out.getvalue().encode('utf-8'))


# ---------------------------------------------------------------------------
# parse_rows
# ---------------------------------------------------------------------------

def test_parse_csv_returns_dicts():
    f = _make_csv()
    rows = parse_rows(f, 'csv')
    assert len(rows) == 1
    r = rows[0]
    assert r['question_code'] == 'Q001'
    assert r['question_type'] == 'MCQ_SINGLE'


def test_parse_rows_unsupported_ext():
    with pytest.raises(ValueError, match='Unsupported'):
        parse_rows(io.BytesIO(b'data'), 'pdf')


def test_parse_rows_xlsx():
    """Round-trip through openpyxl XLSX writer/reader."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip('openpyxl not available')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(ALL_COLS)
    row_data = {k: '' for k in ALL_COLS}
    row_data.update({
        'question_code': 'XLS001',
        'question_text': 'XLSX question?',
        'question_type': 'MCQ_SINGLE',
        'option_a': 'A', 'option_b': 'B', 'option_c': 'C', 'option_d': 'D',
        'correct_answer': 'A', 'positive_marks': '5',
    })
    ws.append([row_data.get(c, '') for c in ALL_COLS])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    rows = parse_rows(buf, 'xlsx')
    assert len(rows) == 1
    assert rows[0]['question_code'] == 'XLS001'


# ---------------------------------------------------------------------------
# validate_rows — error cases
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_validate_missing_required_col(test_obj):
    f = _make_csv(question_text='')   # blank ≡ missing
    rows = parse_rows(f, 'csv')
    rows[0].pop('question_text')       # actually remove it
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert len(errs) == 1
    assert errs[0]['code'] == 'MISSING'
    assert len(cleaned) == 0


@pytest.mark.django_db
def test_validate_duplicate_code_in_file(test_obj):
    f1 = _make_csv(question_code='DUP001')
    rows = parse_rows(f1, 'csv') * 2   # duplicate
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert any(e['code'] == 'DUPLICATE_IN_FILE' for e in errs)


@pytest.mark.django_db
def test_validate_invalid_question_type(test_obj):
    f = _make_csv(question_type='ESSAY')
    rows = parse_rows(f, 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs[0]['code'] == 'BAD_TYPE'


@pytest.mark.django_db
def test_validate_mcq_answer_not_in_options(test_obj):
    # correct_answer='E' but option_e is blank
    f = _make_csv(correct_answer='E', option_e='')
    rows = parse_rows(f, 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs[0]['code'] == 'ANSWER_NOT_IN_OPTIONS'


@pytest.mark.django_db
def test_validate_non_numeric_marks(test_obj):
    f = _make_csv(positive_marks='FIVE')
    rows = parse_rows(f, 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs[0]['code'] == 'BAD_MARKS'


# ---------------------------------------------------------------------------
# validate_rows — happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_validate_new_question_action_create(test_obj):
    f = _make_csv(question_code='BRAND_NEW')
    rows = parse_rows(f, 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs == []
    assert cleaned[0]['_action'] == 'create'


@pytest.mark.django_db
def test_validate_existing_question_action_update(db, test_obj):
    Question.objects.create(
        tenant=test_obj.tenant, test=test_obj,
        question_code='EXIST1', question_text='Old text?',
        question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', positive_marks=4, negative_marks=0,
        question_order=1, is_active=True,
    )
    f = _make_csv(question_code='EXIST1')
    rows = parse_rows(f, 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs == []
    assert cleaned[0]['_action'] == 'update'


# ---------------------------------------------------------------------------
# apply_rows
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_apply_creates_question(test_obj):
    f = _make_csv(question_code='APPLY001', question_text='New?', positive_marks='4')
    rows = parse_rows(f, 'csv')
    cleaned, _ = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    result = apply_rows(cleaned, test=test_obj, tenant=test_obj.tenant)

    assert result['created'] == 1
    assert result['updated'] == 0
    q = Question.objects.get(test=test_obj, question_code='APPLY001')
    assert q.question_text == 'New?'
    assert q.positive_marks == Decimal('4')


@pytest.mark.django_db
def test_apply_updates_question(db, test_obj):
    Question.objects.create(
        tenant=test_obj.tenant, test=test_obj,
        question_code='UPD001', question_text='Original',
        question_type='MCQ_SINGLE',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', positive_marks=2, negative_marks=0,
        question_order=1, is_active=True,
    )
    f = _make_csv(question_code='UPD001', question_text='Updated', positive_marks='5')
    rows = parse_rows(f, 'csv')
    cleaned, _ = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    result = apply_rows(cleaned, test=test_obj, tenant=test_obj.tenant)

    assert result['updated'] == 1
    q = Question.objects.get(test=test_obj, question_code='UPD001')
    assert q.question_text == 'Updated'
    assert q.positive_marks == Decimal('5')


@pytest.mark.django_db
def test_apply_recounts_test_totals(test_obj):
    rows_csv = io.BytesIO()
    # 3 questions
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=ALL_COLS)
    w.writeheader()
    for i in range(1, 4):
        w.writerow({k: {
            'question_code': f'RCT{i:03d}',
            'question_text': f'Q{i}?',
            'question_type': 'MCQ_SINGLE',
            'option_a': 'A', 'option_b': 'B', 'option_c': 'C', 'option_d': 'D',
            'correct_answer': 'A',
            'positive_marks': '4',
            'negative_marks': '-1',
        }.get(k, '') for k in ALL_COLS})
    rows = parse_rows(io.BytesIO(out.getvalue().encode()), 'csv')
    cleaned, errs = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    assert errs == []
    apply_rows(cleaned, test=test_obj, tenant=test_obj.tenant)
    test_obj.refresh_from_db()
    assert test_obj.total_questions == 3
    assert test_obj.total_marks == Decimal('12')


@pytest.mark.django_db
def test_apply_writes_audit(test_obj):
    f = _make_csv(question_code='AUD001')
    rows = parse_rows(f, 'csv')
    cleaned, _ = validate_rows(rows, test=test_obj, tenant=test_obj.tenant)
    apply_rows(cleaned, test=test_obj, tenant=test_obj.tenant)
    assert AuditLog.objects.filter(
        action='QUESTION_BULK_IMPORT',
        resource_id=str(test_obj.id),
    ).exists()


# ---------------------------------------------------------------------------
# template_csv
# ---------------------------------------------------------------------------

def test_template_csv_has_required_columns():
    txt = template_csv()
    reader = csv.DictReader(io.StringIO(txt))
    headers = reader.fieldnames or []
    for col in REQUIRED_COLS:
        assert col in headers


def test_template_csv_has_sample_row():
    txt = template_csv()
    rows = list(csv.DictReader(io.StringIO(txt)))
    assert len(rows) == 1
    assert rows[0]['question_type'] == 'MCQ_SINGLE'
