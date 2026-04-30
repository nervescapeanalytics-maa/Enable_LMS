import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_enterprise.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT set_config('app.current_tenant_id', %s, false)", ['f883ed57-6f3a-40fa-b7f8-f0eebcd7e04c'])
from academics.models import Group, Batch
from accounts.models import Teacher, Student
print("Groups:")
for g in Group.objects.all():
    print(f"  {g.id} | {g.name} | status={g.status}")
print("\nBatches:")
for b in Batch.objects.all():
    print(f"  {b.id} | code='{b.code}' | {b.name} | class={b.class_level} | target={b.exam_target}")
print(f"\nTeachers: {Teacher.objects.count()}")
for t in Teacher.objects.all():
    print(f"  {t.teacher_code} | {t.email}")
print(f"\nStudents: {Student.objects.count()}")
for s in Student.objects.all():
    print(f"  {s.student_code} | {s.email} | class={s.student_class} | batch={s.batch_id}")
