"""Seed 4-5 realistic attendance scenarios for demo / testing.

Scenarios:
  1. Perfect attendance — student present every working day for last 30 days.
  2. Chronic absentee — present 30%, absent 70% of days; pattern: Mon/Fri absent.
  3. Late comer — present every day but 60% of days marked LATE (>15 min).
  4. Recovering absentee — first half of period absent/leave, second half present.
  5. Live-class auto-tracked — attendance auto-marked from live class with
     watch_percentage values and SOURCE=LIVE_CLASS.

Run:
    python manage.py seed_attendance_demo
    python manage.py seed_attendance_demo --days 60 --reset
    python manage.py seed_attendance_demo --tenant <code>

Idempotent: safe to re-run; uses unique constraint
(tenant, user_type, user_id, attendance_date) and update_or_create.
"""

from __future__ import annotations

import random
from datetime import timedelta, time, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


SCENARIOS = [
    {
        'key': 'perfect',
        'label': 'Aarav (Perfect Attendance)',
        'pattern': 'all_present',
    },
    {
        'key': 'chronic',
        'label': 'Bhavna (Chronic Absentee)',
        'pattern': 'mostly_absent',
    },
    {
        'key': 'late',
        'label': 'Chintan (Frequent Late Comer)',
        'pattern': 'mostly_late',
    },
    {
        'key': 'recovering',
        'label': 'Diya (Recovering Absentee)',
        'pattern': 'recovering',
    },
    {
        'key': 'liveclass',
        'label': 'Eshan (Live-Class Auto-Tracked)',
        'pattern': 'liveclass_auto',
    },
]


class Command(BaseCommand):
    help = 'Seed realistic attendance demo data covering 4-5 student scenarios.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30,
                            help='Days back from today to populate (default 30)')
        parser.add_argument('--tenant', default=None,
                            help='Tenant code (defaults to first active tenant)')
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing demo records before seeding')
        parser.add_argument('--dry-run', action='store_true',
                            help='Plan only; do not write')

    def handle(self, *args, **opts):
        from accounts.models import Student
        from attendance.models import Attendance
        from tenants.models import Tenant

        # Resolve tenant
        if opts['tenant']:
            tenant = Tenant.objects.filter(code=opts['tenant']).first()
            if not tenant:
                raise CommandError(f"Tenant '{opts['tenant']}' not found")
        else:
            tenant = Tenant.objects.filter(status='ACTIVE').first() or Tenant.objects.first()
            if not tenant:
                raise CommandError('No tenants exist. Create one first.')
        self.stdout.write(self.style.NOTICE(f'Using tenant: {tenant.code} ({tenant.id})'))

        # Pick or designate 5 demo students from this tenant
        students = list(
            Student.objects.filter(tenant=tenant)
            .order_by('?')[:len(SCENARIOS)]
        )
        if len(students) < len(SCENARIOS):
            raise CommandError(
                f'Need at least {len(SCENARIOS)} students in tenant {tenant.code}; '
                f'found {len(students)}.'
            )

        today = timezone.localdate()
        start = today - timedelta(days=opts['days'] - 1)

        if opts['reset'] and not opts['dry_run']:
            n = Attendance.objects.filter(
                tenant=tenant,
                user_id__in=[s.id for s in students],
                attendance_date__gte=start,
            ).delete()[0]
            self.stdout.write(self.style.WARNING(f'Reset: removed {n} existing demo rows'))

        random.seed(42)
        plans = []
        for student, scen in zip(students, SCENARIOS):
            plans.append((student, scen))

        created = 0
        updated = 0

        with transaction.atomic():
            for student, scen in plans:
                pattern = scen['pattern']
                for offset in range(opts['days']):
                    d = start + timedelta(days=offset)
                    # Skip Sundays — most schools are off
                    if d.weekday() == 6:
                        status, source, ci, co, watch_pct, remarks = (
                            Attendance.Status.HOLIDAY, Attendance.Source.SYSTEM,
                            None, None, None, 'Sunday',
                        )
                    elif pattern == 'all_present':
                        status, source = Attendance.Status.PRESENT, Attendance.Source.BIOMETRIC
                        ci = time(8, 55, random.randint(0, 59))
                        co = time(15, 30)
                        watch_pct, remarks = None, None
                    elif pattern == 'mostly_absent':
                        if d.weekday() in (0, 4) or random.random() < 0.6:
                            status, source = Attendance.Status.ABSENT, Attendance.Source.MANUAL
                            ci = co = None
                            remarks = 'Notified by guardian — health issue'
                        else:
                            status, source = Attendance.Status.PRESENT, Attendance.Source.MANUAL
                            ci = time(9, 5)
                            co = time(15, 30)
                            remarks = None
                        watch_pct = None
                    elif pattern == 'mostly_late':
                        if random.random() < 0.6:
                            status = Attendance.Status.LATE
                            ci = time(9, 20 + random.randint(0, 25))
                            remarks = 'Bus delay'
                        else:
                            status = Attendance.Status.PRESENT
                            ci = time(8, 58)
                            remarks = None
                        source = Attendance.Source.QR_CODE
                        co = time(15, 30)
                        watch_pct = None
                    elif pattern == 'recovering':
                        midpoint = opts['days'] // 2
                        if offset < midpoint:
                            status = random.choice([
                                Attendance.Status.ABSENT, Attendance.Status.LEAVE,
                                Attendance.Status.ABSENT,
                            ])
                            ci = co = None
                            remarks = 'Medical leave'
                            source = Attendance.Source.MANUAL
                        else:
                            status = Attendance.Status.PRESENT
                            ci = time(9, 0)
                            co = time(15, 30)
                            remarks = 'Returned from leave'
                            source = Attendance.Source.MANUAL
                        watch_pct = None
                    elif pattern == 'liveclass_auto':
                        watch_pct = round(random.uniform(45, 99), 2)
                        if watch_pct >= 75:
                            status = Attendance.Status.PRESENT
                        elif watch_pct >= 50:
                            status = Attendance.Status.HALF_DAY
                        else:
                            status = Attendance.Status.ABSENT
                        source = Attendance.Source.LIVE_CLASS
                        ci = time(10, 0)
                        co = time(11, 0) if watch_pct >= 50 else None
                        remarks = f'Auto from live class, watched {watch_pct}%'
                    else:
                        continue

                    if opts['dry_run']:
                        continue

                    obj, was_created = Attendance.objects.update_or_create(
                        tenant=tenant,
                        user_type=Attendance.UserType.STUDENT,
                        user_id=student.id,
                        attendance_date=d,
                        defaults=dict(
                            month=d.month,
                            year=d.year,
                            status=status,
                            source=source,
                            check_in_time=ci,
                            check_out_time=co,
                            watch_percentage=watch_pct,
                            watch_duration_seconds=int((watch_pct or 0) * 36),
                            remarks=remarks,
                            marked_at=timezone.now(),
                        ),
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                self.stdout.write(
                    f'  {scen["label"]:45s} -> {student.full_name or student.student_code} ({student.id})'
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete (dry_run={opts["dry_run"]}): '
            f'created={created}  updated={updated}  '
            f'students={len(plans)}  days={opts["days"]}'
        ))
