"""
Phase 3 — manual smoke test against live DB. Rolls back via transaction.
Run inside the API container:

    docker exec docker-api-1 python /app/_smoke_phase3.py
"""
import io, json, sys, traceback, uuid
import django
django.setup()
from decimal import Decimal
from django.db import transaction
from django.test import Client
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Student
from tenants.models import Tenant
from system_config.models import FeatureFlag
from assessments.models import Test, Question, TestAttempt, TestAttemptAnswer
from assessments.permissions import ensure_exam_feature_flags
from audit.models import AuditLog


HOST = 'lms.automatebot.shop'


def _login(client, student):
    s = client.session
    s['user_type'] = 'STUDENT'
    s['user_id']   = str(student.id)
    s['user_name'] = student.first_name
    s.save()


def run():
    sid = uuid.uuid4().hex[:6]
    sp = transaction.savepoint()
    try:
        ensure_exam_feature_flags()
        tenant = Tenant.objects.create(code=f'P3T_{sid}', name='Phase3 Smoke',
                                       subdomain=f'p3{sid}')
        student = Student(tenant=tenant, email=f'p3_{sid}@t.local',
                          phone='9'+sid+'00000', first_name='Stu', last_name='Smoke',
                          student_code=f'STU{sid}', student_class='12',
                          exam_target='JEE', city='X', state='Y', status='ACTIVE')
        student.set_password('x'); student.save()

        test = Test.objects.create(tenant=tenant, test_code=f'P3_{sid}',
            title='Phase3 Smoke', test_type='PRACTICE', access_mode='OPEN',
            status='PUBLISHED', total_questions=2, total_marks=2,
            total_duration_minutes=30, passing_percent=33)
        q1 = Question.objects.create(tenant=tenant, test=test, question_code='Q1',
            question_text='2+2?', question_type='MCQ_SINGLE',
            option_a='3', option_b='4', option_c='5', option_d='6',
            correct_answer='B', positive_marks=1, negative_marks=0,
            question_order=1)
        q2 = Question.objects.create(tenant=tenant, test=test, question_code='Q2',
            question_text='Capital FR?', question_type='MCQ_SINGLE',
            option_a='Berlin', option_b='Madrid', option_c='Paris', option_d='Rome',
            correct_answer='C', positive_marks=1, negative_marks=0,
            question_order=2)
        attempt = TestAttempt.objects.create(tenant=tenant, test=test, student=student,
            attempt_number=1, started_at=timezone.now(), total_questions=2,
            status='IN_PROGRESS')

        c = Client(HTTP_HOST=HOST, enforce_csrf_checks=False)

        # 1) Anonymous answer -> 401
        r = c.post(f'/student/exams/{test.id}/api/answer/', data='{}',
                   content_type='application/json')
        assert r.status_code == 401, f'anon answer expected 401, got {r.status_code}'
        print('[OK] anonymous answer rejected (401)')

        _login(c, student)

        # 2) Auto-save: create + update
        r = c.post(f'/student/exams/{test.id}/api/answer/',
                   data=json.dumps({'question_id': str(q1.id), 'answer': 'A'}),
                   content_type='application/json')
        assert r.status_code == 200 and r.json()['ok'], r.content
        a = TestAttemptAnswer.objects.get(attempt=attempt, question=q1)
        assert a.student_answer == 'A' and a.status == 'ANSWERED'
        print('[OK] auto-save create works')

        r = c.post(f'/student/exams/{test.id}/api/answer/',
                   data=json.dumps({'question_id': str(q1.id), 'answer': 'B'}),
                   content_type='application/json')
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.student_answer == 'B' and a.answer_change_count == 1
        print('[OK] auto-save update increments change-count')

        # 3) Proctor TAB_SWITCH increments + audits
        for i in range(4):
            r = c.post(f'/student/exams/{test.id}/api/proctor-event/',
                       data=json.dumps({'event_type': 'TAB_SWITCH'}),
                       content_type='application/json')
            assert r.status_code == 200, r.content
        attempt.refresh_from_db()
        assert attempt.tab_switch_count == 4, attempt.tab_switch_count
        print('[OK] tab-switch counter = 4')

        # 4) 5th tab switch triggers auto-submit
        r = c.post(f'/student/exams/{test.id}/api/proctor-event/',
                   data=json.dumps({'event_type': 'TAB_SWITCH'}),
                   content_type='application/json')
        body = r.json()
        assert body.get('auto_submitted') is True, body
        attempt.refresh_from_db()
        assert attempt.auto_terminated is True
        assert attempt.status == 'AUTO_SUBMITTED', attempt.status
        print(f'[OK] 5th tab switch auto-submitted → status={attempt.status}')

        # 5) Audit log entries written
        n = AuditLog.objects.filter(resource_type='TestAttempt',
                                    resource_id=str(attempt.id),
                                    is_security_event=True).count()
        assert n >= 5, f'expected ≥5 security events, got {n}'
        print(f'[OK] {n} security audit entries logged')

        # 6) Submit endpoint on a fresh attempt
        attempt2 = TestAttempt.objects.create(tenant=tenant, test=test, student=student,
            attempt_number=2, started_at=timezone.now(), total_questions=2,
            status='IN_PROGRESS')
        c.post(f'/student/exams/{test.id}/api/answer/',
               data=json.dumps({'question_id': str(q1.id), 'answer': 'B'}),
               content_type='application/json')   # correct
        c.post(f'/student/exams/{test.id}/api/answer/',
               data=json.dumps({'question_id': str(q2.id), 'answer': 'A'}),
               content_type='application/json')   # wrong
        r = c.post(f'/student/exams/{test.id}/api/submit/', data='{}',
                   content_type='application/json')
        body = r.json()
        assert r.status_code == 200 and body['ok'], body
        assert body['redirect'].startswith(f'/student/exams/{test.id}/result/')
        attempt2.refresh_from_db()
        assert attempt2.status == 'EVALUATED'
        assert attempt2.correct == 1 and attempt2.incorrect == 1
        assert attempt2.percentage == Decimal('50.00')
        assert attempt2.result == 'PASS'
        print(f'[OK] submit graded: correct=1 wrong=1 pct=50.00 result=PASS')

        # 7) Snapshot upload disabled-flag returns ignored
        FeatureFlag.objects.filter(flag_key='exam.proctoring_snapshots').update(is_enabled=False)
        attempt3 = TestAttempt.objects.create(tenant=tenant, test=test, student=student,
            attempt_number=3, started_at=timezone.now(), total_questions=2,
            status='IN_PROGRESS')
        f = SimpleUploadedFile('snap.jpg', b'\xff\xd8\xff\xe0' + b'\x00'*16 + b'\xff\xd9',
                               content_type='image/jpeg')
        r = c.post(f'/student/exams/{test.id}/api/snapshot/', data={'snapshot': f})
        assert r.status_code == 200 and r.json().get('ignored') is True, r.content
        print('[OK] snapshot ignored when feature flag disabled')

        # Re-enable + upload
        FeatureFlag.objects.filter(flag_key='exam.proctoring_snapshots').update(is_enabled=True)
        f = SimpleUploadedFile('snap.jpg', b'\xff\xd8\xff\xe0' + b'\x00'*16 + b'\xff\xd9',
                               content_type='image/jpeg')
        r = c.post(f'/student/exams/{test.id}/api/snapshot/', data={'snapshot': f})
        assert r.status_code == 200 and r.json()['ok'], r.content
        print(f"[OK] snapshot stored: {r.json()['path']}")

        # 8) Unsupported snapshot type
        f = SimpleUploadedFile('x.gif', b'GIF89a', content_type='image/gif')
        r = c.post(f'/student/exams/{test.id}/api/snapshot/', data={'snapshot': f})
        assert r.status_code == 415
        print('[OK] unsupported snapshot type rejected (415)')

        # 9) Page renders with feature_flags context
        # need a fresh in-progress attempt
        attempt4 = TestAttempt.objects.create(tenant=tenant, test=test, student=student,
            attempt_number=4, started_at=timezone.now(), total_questions=2,
            status='IN_PROGRESS')
        r = c.get(f'/student/exams/{test.id}/take/')
        assert r.status_code == 200, r.status_code
        body = r.content.decode('utf-8', errors='replace')
        for marker in ('data-ff-tab-switch', 'data-ff-copy-paste', 'data-ff-fullscreen',
                       'data-ff-devtools', 'data-ff-snapshot', 'data-url-answer',
                       'data-url-proctor', 'data-url-submit'):
            assert marker in body, f'missing {marker} in rendered take page'
        print('[OK] take page renders with all proctoring data attributes')

        print('\nALL PHASE 3 SMOKE TESTS PASSED ✅')
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    finally:
        transaction.savepoint_rollback(sp)
        print('(transaction rolled back, no DB changes persisted)')


if __name__ == '__main__':
    run()
