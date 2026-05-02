"""
Phase 5b — ZIP export round-trip + QTI import.

Covers:
  - export_test_zip produces a valid ZIP with questions.csv + images
  - the produced ZIP, when re-fed through parse_zip_with_assets +
    validate_rows + apply_rows, recreates the same set of questions
  - QTI 2.x assessmentItem (single + multi MCQ) is parsed
  - QTI 1.x item with <varequal> is parsed
  - Pure-text QTI (no MCQ) raises ValueError
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from assessments.importers import (
    apply_rows, export_test_zip, parse_zip_with_assets, validate_rows,
)
from assessments.models import Question, Test
from tenants.models import Tenant


PNG_1x1 = bytes.fromhex(
    '89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489'
    '0000000A49444154789C636000000002000148AFA4710000000049454E44AE426082'
)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(code='RT_T', name='RT', subdomain='rtt')


@pytest.fixture
def test_obj(db, tenant):
    return Test.objects.create(
        tenant=tenant, test_code='RT-T', title='RoundTrip',
        test_type='PRACTICE', access_mode='OPEN', status='DRAFT',
        total_questions=0, total_marks=0, total_duration_minutes=10,
    )


@pytest.mark.django_db
class TestZipExport:
    def test_export_round_trip(self, tmp_path, settings, tenant, test_obj):
        settings.MEDIA_ROOT = str(tmp_path)
        settings.MEDIA_URL = '/media/'

        # Seed one question with an image on disk
        img_dir = tmp_path / 'question_images' / 'seed'
        img_dir.mkdir(parents=True)
        (img_dir / 'pic.png').write_bytes(PNG_1x1)

        Question.objects.create(
            tenant=tenant, test=test_obj, question_code='Q1',
            question_text='Pick A', question_type='MCQ_SINGLE',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A', positive_marks=1, negative_marks=0,
            question_order=1,
            question_image='/media/question_images/seed/pic.png',
        )

        blob = export_test_zip(test_obj)
        assert blob[:2] == b'PK'  # ZIP magic

        # Inspect contents
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = z.namelist()
            assert 'questions.csv' in names
            assert any(n.startswith('images/') and n.endswith('.png') for n in names)

        # Re-import into a *new* test in a fresh tenant
        new_tenant = Tenant.objects.create(code='RT_T2', name='RT2', subdomain='rtt2')
        new_test = Test.objects.create(
            tenant=new_tenant, test_code='RT-T2', title='RoundTrip2',
            test_type='PRACTICE', access_mode='OPEN', status='DRAFT',
            total_questions=0, total_marks=0, total_duration_minutes=10,
        )
        rows = parse_zip_with_assets(io.BytesIO(blob))
        cleaned, errors = validate_rows(rows, tenant=new_tenant, test=new_test)
        assert errors == []
        result = apply_rows(cleaned, tenant=new_tenant, test=new_test, actor=None)
        assert result['created'] == 1
        q = Question.objects.get(tenant=new_tenant, question_code='Q1')
        assert q.question_text == 'Pick A'
        assert q.question_image and q.question_image.startswith('/media/')


# ---------------------------------------------------------------------------
# QTI fixtures
# ---------------------------------------------------------------------------
QTI2_MANIFEST = b"""<?xml version='1.0'?>
<manifest xmlns='http://www.imsglobal.org/xsd/imscp_v1p1'/>"""

QTI2_ITEM_SINGLE = b"""<?xml version='1.0' encoding='UTF-8'?>
<assessmentItem xmlns='http://www.imsglobal.org/xsd/imsqti_v2p2' identifier='Q1' title='Q1'>
  <responseDeclaration identifier='RESPONSE' cardinality='single' baseType='identifier'>
    <correctResponse><value>opt_b</value></correctResponse>
  </responseDeclaration>
  <itemBody>
    <p>What is 2+2?</p>
    <choiceInteraction responseIdentifier='RESPONSE' shuffle='false' maxChoices='1'>
      <simpleChoice identifier='opt_a'>3</simpleChoice>
      <simpleChoice identifier='opt_b'>4</simpleChoice>
      <simpleChoice identifier='opt_c'>5</simpleChoice>
      <simpleChoice identifier='opt_d'>6</simpleChoice>
    </choiceInteraction>
  </itemBody>
</assessmentItem>"""

QTI2_ITEM_MULTI = b"""<?xml version='1.0' encoding='UTF-8'?>
<assessmentItem xmlns='http://www.imsglobal.org/xsd/imsqti_v2p2' identifier='Q2' title='Q2'>
  <responseDeclaration identifier='RESPONSE' cardinality='multiple' baseType='identifier'>
    <correctResponse><value>opt_a</value><value>opt_c</value></correctResponse>
  </responseDeclaration>
  <itemBody>
    <p>Pick primes</p>
    <choiceInteraction responseIdentifier='RESPONSE' shuffle='false' maxChoices='0'>
      <simpleChoice identifier='opt_a'>2</simpleChoice>
      <simpleChoice identifier='opt_b'>4</simpleChoice>
      <simpleChoice identifier='opt_c'>3</simpleChoice>
      <simpleChoice identifier='opt_d'>9</simpleChoice>
    </choiceInteraction>
  </itemBody>
</assessmentItem>"""

QTI1_ITEM = b"""<?xml version='1.0'?>
<questestinterop>
  <item ident='Q3' title='Q3'>
    <presentation>
      <material><mattext>Capital of France?</mattext></material>
      <response_lid ident='R'>
        <render_choice>
          <response_label ident='a'><material><mattext>Berlin</mattext></material></response_label>
          <response_label ident='b'><material><mattext>Paris</mattext></material></response_label>
          <response_label ident='c'><material><mattext>Madrid</mattext></material></response_label>
          <response_label ident='d'><material><mattext>Rome</mattext></material></response_label>
        </render_choice>
      </response_lid>
    </presentation>
    <resprocessing>
      <respcondition><conditionvar><varequal>b</varequal></conditionvar></respcondition>
    </resprocessing>
  </item>
</questestinterop>"""


def _qti_zip(items: dict[str, bytes]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('imsmanifest.xml', QTI2_MANIFEST)
        for name, blob in items.items():
            z.writestr(name, blob)
    buf.seek(0)
    return buf


@pytest.mark.django_db
class TestQTIImport:
    def test_qti2_single(self):
        rows = parse_zip_with_assets(_qti_zip({'q1.xml': QTI2_ITEM_SINGLE}))
        assert len(rows) == 1
        r = rows[0]
        assert r['question_type'] == 'MCQ_SINGLE'
        assert r['correct_answer'] == 'B'
        assert r['option_a'] == '3'
        assert r['option_b'] == '4'
        assert 'qti' in r['tags']

    def test_qti2_multi(self):
        rows = parse_zip_with_assets(_qti_zip({'q2.xml': QTI2_ITEM_MULTI}))
        assert len(rows) == 1
        r = rows[0]
        assert r['question_type'] == 'MCQ_MULTI'
        assert r['correct_answer'] == 'A,C'

    def test_qti1_single(self):
        rows = parse_zip_with_assets(_qti_zip({'q3.xml': QTI1_ITEM}))
        assert len(rows) == 1
        r = rows[0]
        assert r['question_type'] == 'MCQ_SINGLE'
        assert r['correct_answer'] == 'B'
        assert 'Paris' in (r['option_b'] or '')

    def test_qti_no_mcq_raises(self):
        empty = b"<?xml version='1.0'?><foo><bar/></foo>"
        with pytest.raises(ValueError):
            parse_zip_with_assets(_qti_zip({'random.xml': empty}))

    def test_qti_full_apply(self, tenant, test_obj):
        rows = parse_zip_with_assets(_qti_zip({'q1.xml': QTI2_ITEM_SINGLE}))
        cleaned, errors = validate_rows(rows, tenant=tenant, test=test_obj)
        assert errors == [], errors
        result = apply_rows(cleaned, tenant=tenant, test=test_obj, actor=None)
        assert result['created'] == 1
        q = Question.objects.get(tenant=tenant, question_code='Q1')
        assert q.correct_answer == 'B'
