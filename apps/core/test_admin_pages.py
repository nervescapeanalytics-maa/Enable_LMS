#!/usr/bin/env python3
"""Test all admin pages after login"""
import requests, re, sys

BASE = "http://127.0.0.1:8000"
s = requests.Session()

# Get CSRF token
resp = s.get(f"{BASE}/login/")
csrf_match = re.search(r'csrfmiddlewaretoken.*?value=["\']([^"\']+)', resp.text)
csrf = csrf_match.group(1) if csrf_match else s.cookies.get('csrftoken', '')
print(f"CSRF: {csrf[:20]}...")

# Login
login_data = {
    'csrfmiddlewaretoken': csrf,
    'email': 'admin@lms.com',
    'password': 'Admin@12345',
    'user_type': 'ADMIN',
}
resp = s.post(f"{BASE}/login/", data=login_data, allow_redirects=True)
print(f"Login: {resp.status_code} -> {resp.url}")

pages = [
    '/staff/dashboard/', '/staff/analytics/', '/staff/monitoring/',
    '/staff/subjects/', '/staff/batches/', '/staff/programs/', '/staff/sessions/',
    '/staff/tests/', '/staff/questions/', '/staff/test-reports/',
    '/staff/schools/', '/staff/teachers/', '/staff/teacher-attendance/',
    '/staff/students/', '/staff/student-attendance/',
    '/staff/live-classes/', '/staff/study-materials/',
    '/staff/announcements/', '/staff/tickets/', '/staff/tenants/',
    '/staff/settings/', '/staff/audit/', '/staff/profile/', '/staff/notifications/',
]

print("\n" + "="*65)
print(f"{'PAGE':<35} {'STATUS':>6} {'SIZE':>8} {'RESULT'}")
print("="*65)

p, f = 0, 0
for page in pages:
    try:
        r = s.get(f"{BASE}{page}", allow_redirects=False, timeout=15)
        sz = len(r.content)
        if r.status_code == 200 and sz > 500:
            res = "PASS"; p += 1
        elif r.status_code in [301, 302]:
            res = f"REDIRECT -> {r.headers.get('Location','')}"; f += 1
        else:
            res = f"FAIL (size={sz})"; f += 1
        print(f"{page:<35} {r.status_code:>6} {sz:>7}B {res}")
    except Exception as e:
        print(f"{page:<35}  ERROR {str(e)[:30]}"); f += 1

print("="*65)
print(f"TOTAL: {p} PASS / {f} FAIL out of {len(pages)} pages")
print("="*65)
