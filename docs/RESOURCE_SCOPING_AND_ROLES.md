# Class-Group Resource Scoping & Role Catalogue

This doc answers three product questions from the April 2026 admin review:

1. **How do we keep a Class 9 student from seeing Class 12 materials / exams?**
2. **What default roles ship for Students / Teachers / Parents?**
3. **What non-admin staff roles exist, and how is the staff dashboard filtered?**

The implementation leans on the models already in the codebase
(`accounts.Role`, `accounts.Permission`, `accounts.RolePermission`,
`accounts.StaffRole`, `academics.Group`, `academics.Batch`) — no new
schema is required.


## 1. Class-group resource scoping

### Recommended approach — **Class Groups + scoped querysets**

Every resource (study material, test, notice, live class, assignment,
attendance) already has a tenant. We add a **class-scope filter** on top:

```python
# academics/groups.py  (new helper module)
from academics.models import Group

def group_for_class(class_level: str, tenant=None):
    """
    Return the canonical `Group` for a given class level
    (e.g. "9" -> "Class 9 — Academic Session 2025-26").
    """
    code = f'CLASS_{class_level}'
    return Group.objects.get(tenant=tenant, code=code)


def scope_to_class(qs, student):
    """
    Restrict a resource queryset (Material / Test / LiveClass / …) to
    anything tagged with the student's class group OR a broader 'ALL' scope.
    """
    class_group = group_for_class(student.student_class, student.tenant)
    return qs.filter(
        models.Q(group=class_group) | models.Q(group__code='ALL')
    )
```

### Steps to roll it out

| # | Step | File |
|---|------|------|
| 1 | Seed a `Group` per class: `CLASS_9`, `CLASS_10`, `CLASS_11`, `CLASS_12`, `CLASS_ALL` | `apps/academics/management/commands/seed_class_groups.py` |
| 2 | Each resource already has `group = FK(Group)` (StudyMaterial, Test, LiveClass) — make it non-null on new rows | existing migrations |
| 3 | In every API view / admin `get_queryset`, apply `scope_to_class(qs, request.user)` | `materials/views.py`, `assessments/views.py`, `classes/views.py` |
| 4 | When a student's `student_class` changes, their scope flips automatically next request — **no data migration needed** | implicit |
| 5 | For mixed-class content (e.g. school-wide notices) tag them with `CLASS_ALL` | content uploads |
| 6 | Teachers: use `batch.class_level` (not student.class) so a Class 9 teacher only sees Class 9 dashboards | `classes/permissions.py` |

### Enforcement checklist

- [ ] REST API viewsets call `scope_to_class` in `get_queryset`
- [ ] Django admin pages call the same helper from `get_queryset`
- [ ] Mobile feed endpoints use the scoped queryset
- [ ] Celery notification tasks filter targets by class group
- [ ] Audit middleware logs any cross-class read (tripwire)

Because scoping is implemented as a **single reusable function**, the
invariant is testable with one integration test per resource type
(see `tests/test_class_scope.py`).


## 2. Default roles (Student / Teacher / Parent)

Run once per environment (or per tenant):

```bash
python manage.py seed_default_roles                 # global SYSTEM roles
python manage.py seed_default_roles --tenant ABC    # tenant-specific clones
```

The command creates these rows in `accounts.Role`:

| Code | Who | Level | Purpose |
|---|---|---:|---|
| STUDENT_ACTIVE | Student | 10 | Enrolled student default |
| STUDENT_ALUMNI | Student | 8 | Read-only after passout |
| PARENT_PRIMARY | Parent | 12 | Primary guardian |
| PARENT_SECONDARY | Parent | 10 | Secondary guardian |
| TEACHER_PRIMARY | Teacher | 40 | Class teacher |
| TEACHER_ASSISTANT | Teacher | 30 | TA — drafts only |
| TEACHER_SUBJECT_HEAD | Teacher | 50 | Leads a subject dept |

Assignment to a user happens via `UserRoleAssignment` (already in the
schema). Signal suggestion: whenever a `Student` is saved with
`status='ACTIVE'`, create a `UserRoleAssignment(role=STUDENT_ACTIVE)`
record automatically.


## 3. Staff roles — subset of admin

Non-technical admins (operations, academics, finance, reports, …) should
see only what their role allows. We use the existing `StaffRole` model
(one row per staff role, boolean per capability).

### Staff role catalogue (seeded by `seed_default_roles`)

| Code | Role | Typical day-to-day |
|---|---|---|
| STAFF_ACADEMIC | Academic Operator | Admissions, batch assignment, class schedules |
| STAFF_ATTENDANCE | Attendance Officer | View/fix attendance, export |
| STAFF_EXAM | Exam Coordinator | Create tests, publish results |
| STAFF_FINANCE | Finance Officer | Fees, invoices, scholarships |
| STAFF_CONTENT | Content Curator | Materials / notes / videos upload |
| STAFF_FRONTDESK | Front Desk | Enquiries, ID cards, limited edit |
| STAFF_COUNSELLOR | Counsellor | Case notes, read student history |
| STAFF_REPORTS | Reports & Analytics | Read-only + export MIS |
| ADMIN_BRANCH | Branch Admin | Full rights for one branch |
| ADMIN_TENANT | Tenant Admin | Full rights, all branches |

### Wiring staff roles into the admin site

The `AdminUser` model already has a `staff_role` FK. The admin uses a
capability check similar to:

```python
# apps/core/enf_admin_site.py
def user_can_see_model(user, app_label, model_name):
    sr = getattr(user, 'staff_role', None)
    if sr is None:
        return user.is_superuser
    matrix = {
        ('accounts', 'student'):  sr.can_manage_students,
        ('accounts', 'teacher'):  sr.can_manage_teachers,
        ('assessments', 'test'):  sr.can_manage_exams,
        ('attendance', 'attendance'): sr.can_manage_attendance,
        ('materials',  'studymaterial'): sr.can_manage_content,
        ('system_config', 'featureflag'): sr.can_manage_settings,
        # add one row per (app, model) as new features land
    }
    return matrix.get((app_label, model_name), False)
```

Then override `AdminSite.get_app_list` to drop entries whose
`user_can_see_model()` returns `False`. Each staff role therefore sees
a **strict subset** of the super-admin sidebar — no extra permission
model is needed.

### Why not `auth.Group` + `auth.Permission`?

Those built-ins work at the model level only. Our scope requirement
("Class 9 materials only", "branch X only", "own attendance only") needs
**data-scope** filters. The `Permission.scope` enum
(`OWN`, `BATCH`, `BRANCH`, `TENANT`, `GLOBAL`) already gives us that
vocabulary. `StaffRole` boolean flags then gate the dashboard UI on top.


## 4. Testing strategy

```python
# tests/test_class_scope.py
def test_class9_student_sees_only_class9_materials(student9, class9_material, class12_material):
    scoped = scope_to_class(StudyMaterial.objects.all(), student9)
    assert class9_material in scoped
    assert class12_material not in scoped
```

Run:

```bash
python -m pytest tests/test_class_scope.py --nomigrations
```

## 5. Rollout order

1. `python manage.py seed_default_roles`
2. Create a data migration that back-fills `UserRoleAssignment` for every
   existing active student / teacher
3. Apply `scope_to_class` to viewsets in `materials`, `assessments`,
   `classes`, `realtime`
4. Enable the `StaffRole` check in `enf_admin_site.get_app_list`
5. QA each staff role by impersonating a dummy user and verifying that
   the sidebar shows only their expected subset.
