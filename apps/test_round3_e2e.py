"""End-to-end smoke tests for Round-3 fixes:
  1. Gender display normalization
  2. Tools dropdown markup is present (delegated handler)
  3. Attendance demo records exist
  4. Alert rules + Alert log endpoints work
  5. Monitoring dashboard URLs (under both AlertLog and AlertRule)
  6. _filter-choices for several Student columns

Run inside the api container:
    python /app/test_round3_e2e.py
"""
import os, sys, re, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')
django.setup()

from django.test import Client
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

User = get_user_model()
results = []
def t(name, ok, detail=''):
    results.append((name, ok, detail))
    mark = '✓' if ok else '✗'
    print(f'  {mark} {name}{(" — " + detail) if detail else ""}')

print('\n=== Round 3 E2E Tests ===')

# ── 1. Gender canonicalization (model + admin) ──
print('\n[1] Gender canonicalization')
from accounts.models import Student
s = Student.objects.exclude(gender__isnull=True).first()
t('admin label resolves', s.get_gender_display() in ('Male', 'Female', 'Other', 'Prefer not to say'),
  f'value={s.gender!r} display={s.get_gender_display()!r}')
# Future-proof: save() should canonicalize lowercase → uppercase
s.gender = 'male'
s.save(update_fields=['gender'])
s.refresh_from_db()
t('save() canonicalizes lowercase', s.gender == 'MALE', f'after save: {s.gender!r}')

# ── 2. Attendance seed ──
print('\n[2] Attendance demo data')
from attendance.models import Attendance
n = Attendance.objects.count()
t('attendance rows exist', n >= 100, f'{n} rows')
distinct_statuses = set(Attendance.objects.values_list('status', flat=True).distinct())
t('multiple statuses represented', len(distinct_statuses) >= 4, f'statuses={distinct_statuses}')

# ── 3. Alert rules ──
print('\n[3] Alert rules')
from alerts.models import AlertRule, AlertLog
active = AlertRule.objects.filter(is_active=True).count()
t('14+ active alert rules seeded', active >= 14, f'{active} rules')
emails_set = AlertRule.objects.filter(notify_emails__icontains='neeraj.vishen@gmail.com').count()
t('email recipient configured', emails_set >= 14, f'{emails_set} rules with target email')

# ── 4. Trigger evaluator ──
print('\n[4] Alert evaluation pipeline')
from alerts.tasks import evaluate_alert_rules
before = AlertLog.objects.count()
triggered = evaluate_alert_rules()
after = AlertLog.objects.count()
t('evaluator runs without crashing', isinstance(triggered, int))
t('logs persist', after >= before, f'before={before} after={after}')

# ── 5. Admin URLs ──
print('\n[5] Admin pages respond')
with override_settings(ALLOWED_HOSTS=['*']):
    c = Client()
    su = User.objects.filter(is_superuser=True).first()
    c.force_login(su)
    pages = [
        ('Student list',           '/admin/accounts/student/'),
        ('Student filter-choices', '/admin/accounts/student/_filter-choices/?field=gender'),
        ('AlertRule list',         '/admin/alerts/alertrule/'),
        ('AlertLog list',          '/admin/alerts/alertlog/'),
        ('AlertLog monitoring',    '/admin/alerts/alertlog/monitoring/'),
        ('AlertRule monitoring',   '/admin/alerts/alertrule/monitoring/'),
        ('Attendance list',        '/admin/attendance/attendance/'),
    ]
    for name, url in pages:
        r = c.get(url)
        t(f'{name} -> {r.status_code}', r.status_code == 200, url)

    # Tools dropdown markup is present on student list
    r = c.get('/admin/accounts/student/?list_per_page=1')
    html = r.content.decode()
    t('Tools trigger present', 'data-enf-tools-trigger' in html)
    t('Tools delegated handler emitted', '__enfToolsDelegated' in html)
    t('Premium menu items present', 'data-enf-action="copy-link"' in html)

    # Gender cell renders Male/Female (not '-')
    m = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.S)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(1), re.S)
    cells = re.findall(r'<td[^>]*>(.*?)</td>', rows[0], re.S)
    gender_text = re.sub(r'<[^>]+>',' ', cells[11]).strip()
    t('gender column shows label', gender_text in ('Male', 'Female'), f'cell={gender_text!r}')

    # AlertRule list embeds monitoring iframe (task 6)
    r = c.get('/admin/alerts/alertrule/')
    t('AlertRule embeds monitoring iframe', 'monitoring/?embed=1' in r.content.decode())

    # _filter-choices for various columns
    r = c.get('/admin/accounts/student/_filter-choices/?field=phone')
    t('phone filter-choices works', r.status_code == 200 and len(r.json().get('choices', [])) > 0)
    r = c.get('/admin/accounts/student/_filter-choices/?field=category')
    cats = r.json().get('choices', [])
    t('category filter-choices returns labels', r.status_code == 200 and any(c.get('label') for c in cats))

# ── Summary ──
print('\n=== Summary ===')
ok = sum(1 for _, k, _ in results if k)
total = len(results)
print(f'Passed {ok}/{total}')
sys.exit(0 if ok == total else 1)
