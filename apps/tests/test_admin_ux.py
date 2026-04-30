"""
Integration tests for the admin UX changes:

  • Student list page exposes the new column set (school name, state, district,
    city, student name, phone, father name, guardian contact, student code,
    email, class, gender, category, physically handicapped, date of birth,
    tps, previous class marks).
  • Teacher list page shows the simplified column set requested by admins.
  • Batch list surfaces the live `enrolled_count` (not `max_students`).
  • School list is trimmed to 4 columns: state / city-village / district / name.
  • Sidebar hides Category / Religion / State under Academics but keeps Cities.
  • Batch `max_students` field is not rendered on the edit form.
  • Category FK on Student is wired.
  • `column_manager.js` is served and references PREFS_VERSION 5.

These tests are deliberately high-level: they exercise the admin URLs end-to-end
without mocking so that any admin registration / template / migration regression
will fail the build.
"""
import os
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import Student, Teacher
from academics.models import Batch, Category, School, City, State
from tenants.models import Tenant


pytestmark = pytest.mark.django_db


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        code='TEST', defaults={'name': 'Test Tenant', 'status': 'ACTIVE'},
    )
    return t


@pytest.fixture
def super_admin(db, django_user_model):
    user = django_user_model.objects.create_superuser(
        username='colmgr_admin',
        email='colmgr_admin@example.com',
        password='Pass!23456',
    )
    return user


@pytest.fixture
def admin_client(client, super_admin):
    assert client.login(username='colmgr_admin', password='Pass!23456')
    return client


@pytest.fixture
def state(db):
    s, _ = State.objects.get_or_create(name='TestState', defaults={'code': 'TS'})
    return s


@pytest.fixture
def city(db, state):
    c, _ = City.objects.get_or_create(name='TestCity', state=state)
    return c


@pytest.fixture
def category(db, tenant):
    cat, _ = Category.objects.get_or_create(tenant=tenant, name='TestCat')
    return cat


@pytest.fixture
def student(db, tenant, category):
    return Student.objects.create(
        tenant=tenant,
        student_code='ADMTST0001',
        first_name='Ada',
        last_name='Lovelace',
        email='ada@test.example',
        phone='9000000001',
        student_class='11',
        exam_target='JEE',
        medium='ENGLISH',
        city='Lovelace Village',
        state='TestState',
        district='TestDistrict',
        pin_code='560001',
        password_hash='x',
        parent_name='Byron',
        parent_phone='9000000002',
        school_name='EMRS Test',
        category=category,
        physically_handicapped=False,
        tps=True,
        previous_class_marks='480',
    )


@pytest.fixture
def teacher(db, tenant):
    return Teacher.objects.create(
        tenant=tenant,
        teacher_code='TSKRL0001',
        first_name='Richard',
        last_name='Feynman',
        email='feynman@test.example',
        phone='9111111111',
        designation='Senior Physics Faculty',
        teacher_city='Kurnool',
        teacher_district='Kurnool',
        teacher_state='TS',
        joining_date='2023-06-01',
        password_hash='x',
    )


@pytest.fixture
def batch(db, tenant):
    return Batch.objects.create(
        tenant=tenant,
        code='TSTBATCH',
        name='Test Batch 11',
        class_level='11',
        exam_target='JEE',
    )


@pytest.fixture
def school(db, state, city):
    return School.objects.create(
        name='EMRS Dornala Test',
        state=state,
        city=city,
        city_name='Dornala',
    )


# ── Student changelist ──────────────────────────────────────────────────────
def test_student_changelist_renders_with_new_columns(admin_client, student):
    url = reverse('admin:accounts_student_changelist')
    resp = admin_client.get(url)
    assert resp.status_code == 200
    body = resp.content.decode()
    import re
    thead_m = re.search(r'<table id="result_list".*?</thead>', body, re.S)
    assert thead_m, 'result_list thead missing'
    thead = thead_m.group()
    # Required column headers from the provided screenshots.
    for header in [
        'School Name', 'State', 'District', 'City / Village',
        'Student Name', 'Phone',
        'Father Name', 'Father Phone',
        'Guardian Name', 'Guardian Contact',
        'Student code', 'Email', 'Student class', 'Gender', 'Category',
        'Physically Handicapped', 'Date of birth', 'TPS',
        'Previous Class Marks',
    ]:
        assert header in thead, f'missing column: {header!r}'


def test_student_edit_form_hides_academic_json(admin_client, student):
    url = reverse('admin:accounts_student_change', args=[student.pk])
    resp = admin_client.get(url)
    assert resp.status_code == 200
    body = resp.content.decode()
    # academic_json MUST NOT appear in the admin form.
    assert 'name="academic_json"' not in body
    # physically_handicapped / tps ARE editable (dropdown / checkbox).
    assert 'name="physically_handicapped"' in body
    assert 'name="tps"' in body
    assert 'name="previous_class_marks"' in body


def test_student_edit_form_has_extension_block_description(admin_client, student):
    """The Reserved-for-future-use block should explain what extension fields do."""
    url = reverse('admin:accounts_student_change', args=[student.pk])
    body = admin_client.get(url).content.decode()
    assert 'Extension fields' in body
    assert 'tenant-specific future data' in body


# ── Teacher changelist ──────────────────────────────────────────────────────
def test_teacher_changelist_exposes_simplified_columns(admin_client, teacher):
    url = reverse('admin:accounts_teacher_changelist')
    body = admin_client.get(url).content.decode()
    for header in [
        'Teacher code', 'Teacher Name', 'Phone', 'Email', 'Designation',
        'Subject', 'Status', 'Teacher city', 'District', 'Teacher state',
        'Joining date',
    ]:
        assert header in body, f'missing teacher column: {header!r}'


def test_teacher_edit_form_hides_financial_youtube_extension(admin_client, teacher):
    url = reverse('admin:accounts_teacher_change', args=[teacher.pk])
    body = admin_client.get(url).content.decode()
    # Sections dropped per requirement.
    for removed in ['name="bank_account"', 'name="youtube_oauth_token"',
                    'name="expertise_json"', 'name="availability_json"',
                    'name="ext_teacher_1"']:
        assert removed not in body, f'{removed} still on teacher form'


# ── Batch changelist / form ─────────────────────────────────────────────────
def test_batch_changelist_shows_enrolled_not_max(admin_client, batch):
    url = reverse('admin:academics_batch_changelist')
    body = admin_client.get(url).content.decode()
    assert 'Enrolled' in body
    # `max_students` column header must NOT be present anymore.
    assert 'Max students' not in body


def test_batch_edit_form_hides_max_students_and_extensions(admin_client, batch):
    url = reverse('admin:academics_batch_change', args=[batch.pk])
    body = admin_client.get(url).content.decode()
    assert 'name="max_students"' not in body
    assert 'name="ext_string_1"' not in body
    # Group helper copy + metadata example must be present.
    assert 'cluster related batches' in body
    assert '&quot;room&quot;' in body or '"room"' in body


# ── School changelist ───────────────────────────────────────────────────────
def test_school_changelist_is_trimmed(admin_client, school):
    url = reverse('admin:academics_school_changelist')
    body = admin_client.get(url).content.decode()
    assert 'School name' in body or 'Name' in body
    assert 'State' in body
    assert 'City / Village' in body
    assert 'District' in body
    # Removed columns.
    assert 'School type' not in body
    assert 'Religion' not in body


# ── Sidebar: hidden master data in Academics ────────────────────────────────
def test_academics_sidebar_hides_master_data(admin_client):
    resp = admin_client.get('/admin/')
    body = resp.content.decode()
    # Cities remain visible…
    assert '/admin/academics/city/' in body
    # …but Categories / Religions / States are hidden.
    assert '/admin/academics/category/' not in body
    assert '/admin/academics/religion/' not in body
    assert '/admin/academics/state/' not in body


# ── Student.category FK wiring ──────────────────────────────────────────────
def test_student_category_fk_is_queryable(student, category):
    assert student.category_id == category.id
    # Reverse relation populated.
    assert category.students.filter(pk=student.pk).exists()


# ── Column manager asset ────────────────────────────────────────────────────
def test_column_manager_js_is_v7():
    js_path = os.path.join(
        os.path.dirname(__file__), '..', 'static', 'js', 'column_manager.js',
    )
    with open(js_path, 'r') as fh:
        src = fh.read()
    assert 'PREFS_VERSION = 7' in src, 'column_manager.js is not the v7 build'
    # CSS-injection approach replaces the brittle inline-style hide.
    assert 'colmgr-hide-style' in src
    assert 'display:none !important' in src
    # Safety nets.
    assert 'MIN_VISIBLE' in src
    assert 'MutationObserver' in src
    assert 'Show All' in src
    # v7 contract: the observer must NOT call the full retagger; it must only
    # fill missing data-orig-col attributes on new cells. This is the bug fix
    # that prevents existing reorder/hide state from being clobbered when the
    # admin re-renders the table (filters, pagination, sort).
    assert 'tagNewBodyCells' in src, 'v7 helper tagNewBodyCells missing'
    # Find the observer block and assert it does NOT call tagOriginalIndices.
    obs_idx = src.find('new MutationObserver')
    assert obs_idx > 0
    obs_block = src[obs_idx:obs_idx + 800]
    assert 'tagOriginalIndices' not in obs_block, (
        'MutationObserver must not retag existing cells (v6 regression).'
    )
    assert 'tagNewBodyCells' in obs_block


# ── Teacher code auto-generation ───────────────────────────────────────────
def test_teacher_code_autogenerates_from_state_district(db, tenant):
    t = Teacher.objects.create(
        tenant=tenant,
        first_name='Grace', last_name='Hopper',
        email='grace@test.example', phone='9222222222',
        teacher_state='Andhra Pradesh', teacher_district='Kurnool',
        password_hash='x',
    )
    # Format: 3-letter state + 3-letter district + 4-digit serial.
    assert len(t.teacher_code) == 10
    assert t.teacher_code.startswith('AND')  # Andhra → AND
    assert t.teacher_code[3:6] == 'KUR'
    assert t.teacher_code[6:].isdigit()


def test_teacher_code_respects_explicit_value(db, tenant):
    t = Teacher.objects.create(
        tenant=tenant, teacher_code='CUSTOM123',
        first_name='Ada', last_name='Byron',
        email='ada2@test.example', phone='9333333333',
        password_hash='x',
    )
    assert t.teacher_code == 'CUSTOM123'


# ── Batch enrolled_count via legacy Users table ─────────────────────────────
def test_batch_enrolled_count_uses_legacy_users(admin_client, batch, tenant):
    from academics.models import Users as LegacyUser
    for i in range(3):
        LegacyUser.objects.create(
            tenant=tenant, batch=batch, is_active=True,
            name=f'Legacy{i}', phone=f'900{i:07d}',
        )
    LegacyUser.objects.create(
        tenant=tenant, batch=batch, is_active=False,
        name='Inactive', phone='9999999999',
    )
    url = reverse('admin:academics_batch_changelist')
    body = admin_client.get(url).content.decode()
    # 3 active legacy users + 0 modern students = 3 enrolled
    assert '>3</span>' in body


# ── StaffRole-based admin sidebar filtering ────────────────────────────────
def test_staff_role_matrix_contains_core_models():
    from core.enf_admin_site import STAFF_ROLE_MODEL_MATRIX
    for key in [
        ('academics', 'Student'),
        ('academics', 'Teacher'),
        ('academics', 'Batch'),
        ('assessments', 'Test'),
        ('attendance', 'Attendance'),
    ]:
        assert key in STAFF_ROLE_MODEL_MATRIX, f'missing staff-role gate: {key}'
