"""
Phase 5 — Feature 2: ZIP+Excel question importer with embedded images.

Covers:
  - parse_zip_with_assets extracts xlsx + maps image refs to /media/...
  - validate_rows + apply_rows happy path with image columns persisted
  - Bad ZIP raises ValueError
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from assessments.importers import (
    ALL_COLS, parse_zip_with_assets, validate_rows, apply_rows,
)
from assessments.models import Question, Test
from tenants.models import Tenant


PNG_1x1 = bytes.fromhex(
    '89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489'
    '0000000A49444154789C636000000002000148AFA4710000000049454E44AE426082'
)


def _build_zip(rows: list[dict], image_files: dict[str, bytes]) -> io.BytesIO:
    """Build an in-memory ZIP with questions.csv and image files."""
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=list(ALL_COLS))
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in ALL_COLS})

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('questions.csv', sio.getvalue())
        for name, blob in image_files.items():
            z.writestr(name, blob)
    zbuf.seek(0)
    return zbuf


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='ZIP_T1', name='Zip', subdomain='zipt')


@pytest.fixture
def test_obj(db, tenant):
    return Test.objects.create(
        tenant=tenant, test_code='ZIP-T', title='ZipT',
        test_type='PRACTICE', access_mode='OPEN', status='DRAFT',
        total_questions=0, total_marks=0, total_duration_minutes=10,
    )


@pytest.mark.django_db
class TestZipImporter:
    def test_parse_zip_resolves_images_to_media_urls(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        settings.MEDIA_URL = '/media/'
        rows_in = [{
            'question_code': 'ZQ1', 'question_text': 'Pic question?',
            'question_type': 'MCQ_SINGLE',
            'option_a': 'A', 'option_b': 'B', 'option_c': 'C', 'option_d': 'D',
            'correct_answer': 'A',
            'positive_marks': '1', 'negative_marks': '0', 'partial_marks': '0',
            'difficulty': 'EASY', 'question_order': '1',
            'question_image': 'q1.png',
            'option_a_image': 'images/optA.png',
        }]
        zbuf = _build_zip(rows_in, {
            'q1.png': PNG_1x1,
            'images/optA.png': PNG_1x1,
        })

        rows = parse_zip_with_assets(zbuf)
        assert len(rows) == 1
        r = rows[0]
        assert r['question_image'].startswith('/media/question_images/')
        assert r['question_image'].endswith('q1.png')
        assert r['option_a_image'].startswith('/media/question_images/')
        # File actually written
        rel = r['question_image'][len('/media/'):]
        assert (tmp_path / rel).exists()

    def test_apply_rows_persists_image_urls(self, tmp_path, settings, tenant, test_obj):
        settings.MEDIA_ROOT = str(tmp_path)
        rows_in = [{
            'question_code': 'ZQ2', 'question_text': 'Q with image',
            'question_type': 'MCQ_SINGLE',
            'option_a': 'A', 'option_b': 'B', 'option_c': 'C', 'option_d': 'D',
            'correct_answer': 'B',
            'positive_marks': '2', 'negative_marks': '0', 'partial_marks': '0',
            'difficulty': 'EASY', 'question_order': '1',
            'question_image': 'pic.png',
        }]
        zbuf = _build_zip(rows_in, {'pic.png': PNG_1x1})
        rows = parse_zip_with_assets(zbuf)
        cleaned, errors = validate_rows(rows, tenant=tenant, test=test_obj)
        assert errors == []
        result = apply_rows(cleaned, tenant=tenant, test=test_obj, actor=None)
        assert result['created'] == 1
        q = Question.objects.get(tenant=tenant, question_code='ZQ2')
        assert q.question_image and q.question_image.startswith('/media/question_images/')

    def test_bad_zip_raises(self):
        bad = io.BytesIO(b'not a zip')
        with pytest.raises(ValueError):
            parse_zip_with_assets(bad)

    def test_zip_missing_spreadsheet_raises(self):
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, 'w') as z:
            z.writestr('readme.txt', 'no sheet here')
        zbuf.seek(0)
        with pytest.raises(ValueError):
            parse_zip_with_assets(zbuf)
