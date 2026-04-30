"""
Celery tasks for evaluating alert rules and sending notifications.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='alerts.evaluate_alert_rules')
def evaluate_alert_rules():
    """Evaluate all active alert rules and create AlertLog entries for violations."""
    from alerts.models import AlertRule, AlertLog
    from tenants.models import Tenant

    rules = AlertRule.objects.filter(is_active=True).select_related('tenant')
    triggered = 0

    for rule in rules:
        try:
            result = _evaluate_rule(rule)
            if result:
                log = AlertLog.objects.create(
                    tenant=rule.tenant,
                    rule=rule,
                    message=result['message'],
                    details=result.get('details'),
                    severity=rule.severity,
                )
                triggered += 1

                # Send email if configured
                if rule.notify_method in ('EMAIL', 'BOTH') and rule.notify_emails:
                    _send_alert_email(rule, log)
        except Exception as e:
            logger.error(f"Error evaluating alert rule {rule.name}: {e}")

    logger.info(f"Alert evaluation complete: {triggered} alerts triggered from {rules.count()} rules")
    return triggered


def _evaluate_rule(rule):
    """Evaluate a single rule. Returns dict with 'message' and 'details' if triggered, else None."""
    now = timezone.now()
    window_start = now - timedelta(minutes=rule.time_window_minutes)
    threshold = float(rule.threshold)

    if rule.rule_type == 'FAILED_LOGIN_STREAK':
        return _check_failed_logins(rule, window_start, threshold)
    elif rule.rule_type == 'SUSPICIOUS_LOGIN':
        return _check_suspicious_logins(rule, window_start)
    elif rule.rule_type == 'CONCURRENT_SESSIONS':
        return _check_concurrent_sessions(rule, threshold)
    elif rule.rule_type == 'INACTIVE_SESSION':
        return _check_inactive_sessions(rule, window_start, threshold)
    elif rule.rule_type == 'BRUTE_FORCE':
        return _check_brute_force(rule, window_start, threshold)
    elif rule.rule_type in ('LOW_ATTENDANCE', 'ABSENT_STREAK', 'LOW_CLASS_ATTENDANCE',
                            'CLASS_NOT_STARTED', 'LOW_TEST_SCORE', 'TEST_NOT_SUBMITTED'):
        # These require app-specific models — check if they exist
        return _check_domain_rule(rule, window_start, threshold)
    elif rule.rule_type == 'STUDENT_LOW_ATTEND_PCT':
        return _check_student_low_attendance(rule, window_start, threshold)
    elif rule.rule_type == 'TEACHER_LOW_ATTEND_PCT':
        return _check_teacher_low_attendance(rule, window_start, threshold)
    elif rule.rule_type == 'BATCH_LOW_AVG_ATTEND':
        return _check_batch_low_attendance(rule, window_start, threshold)
    return None


def _check_failed_logins(rule, window_start, threshold):
    from sessions_tracking.models import LoginHistory
    count = LoginHistory.objects.filter(
        tenant=rule.tenant,
        result='FAILED',
        attempted_at__gte=window_start,
    ).count()
    if count >= threshold:
        return {
            'message': f'{int(count)} failed login attempts in the last {rule.time_window_minutes} minutes (threshold: {int(threshold)})',
            'details': {'failed_count': count, 'threshold': threshold, 'window_minutes': rule.time_window_minutes},
        }
    return None


def _check_suspicious_logins(rule, window_start):
    from sessions_tracking.models import LoginHistory
    suspicious = LoginHistory.objects.filter(
        tenant=rule.tenant,
        is_suspicious=True,
        attempted_at__gte=window_start,
    )
    if suspicious.exists():
        entries = list(suspicious.values('username_attempted', 'ip_address', 'attempted_at')[:5])
        for e in entries:
            e['attempted_at'] = e['attempted_at'].isoformat()
        return {
            'message': f'{suspicious.count()} suspicious login(s) detected in the last {rule.time_window_minutes} minutes',
            'details': {'entries': entries},
        }
    return None


def _check_concurrent_sessions(rule, threshold):
    from sessions_tracking.models import UserSession
    from django.db.models import Count
    users_with_many = UserSession.objects.filter(
        tenant=rule.tenant,
        status='ACTIVE',
    ).values('user_id').annotate(count=Count('id')).filter(count__gt=int(threshold))
    if users_with_many.exists():
        # Stringify UUID user_ids so AlertLog.details (JSONField) can serialize them.
        users_payload = [
            {'user_id': str(u['user_id']), 'count': u['count']}
            for u in users_with_many[:10]
        ]
        return {
            'message': f'{users_with_many.count()} user(s) have more than {int(threshold)} concurrent active sessions',
            'details': {'users': users_payload},
        }
    return None


def _check_inactive_sessions(rule, window_start, threshold):
    from sessions_tracking.models import UserSession
    cutoff = timezone.now() - timedelta(minutes=int(threshold))
    stale = UserSession.objects.filter(
        tenant=rule.tenant,
        status='ACTIVE',
        last_activity_at__lt=cutoff,
    ).count()
    if stale > 0:
        return {
            'message': f'{stale} active session(s) have been inactive for more than {int(threshold)} minutes',
            'details': {'stale_count': stale, 'threshold_minutes': int(threshold)},
        }
    return None


def _check_brute_force(rule, window_start, threshold):
    from sessions_tracking.models import LoginHistory
    from django.db.models import Count
    # Group failed logins by IP
    ips = LoginHistory.objects.filter(
        tenant=rule.tenant,
        result='FAILED',
        attempted_at__gte=window_start,
    ).values('ip_address').annotate(count=Count('id')).filter(count__gte=int(threshold))
    if ips.exists():
        ip_list = [f"{x['ip_address']} ({x['count']} attempts)" for x in ips[:5]]
        return {
            'message': f'Potential brute force from {ips.count()} IP(s): {", ".join(ip_list)}',
            'details': {'ips': list(ips[:10])},
        }
    return None


def _check_domain_rule(rule, window_start, threshold):
    """Evaluate attendance / live class / assessment rules if models are available."""
    try:
        if rule.rule_type == 'LOW_ATTENDANCE':
            from attendance.models import AttendanceRecord
            # Count records below threshold in the time window
            total = AttendanceRecord.objects.filter(
                tenant=rule.tenant,
                date__gte=window_start.date(),
            ).count()
            present = AttendanceRecord.objects.filter(
                tenant=rule.tenant,
                date__gte=window_start.date(),
                status='PRESENT',
            ).count()
            if total > 0:
                pct = (present / total) * 100
                if pct < threshold:
                    return {
                        'message': f'Overall attendance is {pct:.1f}% (threshold: {threshold}%)',
                        'details': {'total': total, 'present': present, 'percentage': round(pct, 1)},
                    }
        elif rule.rule_type == 'LOW_CLASS_ATTENDANCE':
            from realtime.models import LiveClass
            recent_classes = LiveClass.objects.filter(
                tenant=rule.tenant,
                scheduled_start__gte=window_start,
                status='COMPLETED',
            )
            for cls in recent_classes[:5]:
                if hasattr(cls, 'actual_attendance') and hasattr(cls, 'expected_attendance'):
                    if cls.expected_attendance and cls.expected_attendance > 0:
                        pct = (cls.actual_attendance / cls.expected_attendance) * 100
                        if pct < threshold:
                            return {
                                'message': f'Live class "{cls}" had {pct:.0f}% attendance (threshold: {threshold}%)',
                                'details': {'class': str(cls), 'percentage': round(pct, 1)},
                            }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Domain rule check failed for {rule.rule_type}: {e}")
    return None


# ── Real-time attendance evaluators ──────────────────────────────────
def _attend_window_dates(window_start):
    """Return (from_date, to_date) for the attendance percentage window."""
    return window_start.date(), timezone.now().date()


def _check_student_low_attendance(rule, window_start, threshold):
    """Trigger when any student's attendance % falls below `threshold` in window.

    Returns the worst-N students so the alert payload is actionable.
    """
    try:
        from attendance.models import Attendance
        from django.db.models import Count, Q
        from_date, to_date = _attend_window_dates(window_start)

        agg = (
            Attendance.objects
            .filter(
                tenant=rule.tenant,
                user_type='STUDENT',
                attendance_date__range=(from_date, to_date),
            )
            .values('user_id')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=['PRESENT', 'LATE', 'HALF_DAY'])),
            )
            .filter(total__gte=3)  # need at least 3 records to be meaningful
        )
        offenders = []
        for row in agg:
            if row['total'] == 0:
                continue
            pct = (row['present'] / row['total']) * 100
            if pct < threshold:
                offenders.append({
                    'user_id': str(row['user_id']),
                    'percentage': round(pct, 1),
                    'present': row['present'],
                    'total': row['total'],
                })
        if offenders:
            offenders.sort(key=lambda x: x['percentage'])
            top = offenders[:10]
            return {
                'message': f"{len(offenders)} student(s) below {int(threshold)}% attendance",
                'details': {
                    'threshold': float(threshold),
                    'window_days': (to_date - from_date).days or 1,
                    'count': len(offenders),
                    'worst': top,
                },
            }
    except Exception as e:
        logger.warning(f"STUDENT_LOW_ATTEND_PCT check failed: {e}")
    return None


def _check_teacher_low_attendance(rule, window_start, threshold):
    try:
        from attendance.models import Attendance
        from django.db.models import Count, Q
        from_date, to_date = _attend_window_dates(window_start)

        agg = (
            Attendance.objects
            .filter(
                tenant=rule.tenant,
                user_type='TEACHER',
                attendance_date__range=(from_date, to_date),
            )
            .values('user_id')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=['PRESENT', 'LATE', 'HALF_DAY'])),
            )
            .filter(total__gte=3)
        )
        offenders = []
        for row in agg:
            if row['total'] == 0:
                continue
            pct = (row['present'] / row['total']) * 100
            if pct < threshold:
                offenders.append({
                    'user_id': str(row['user_id']),
                    'percentage': round(pct, 1),
                    'present': row['present'],
                    'total': row['total'],
                })
        if offenders:
            offenders.sort(key=lambda x: x['percentage'])
            return {
                'message': f"{len(offenders)} teacher(s) below {int(threshold)}% attendance",
                'details': {
                    'threshold': float(threshold),
                    'window_days': (to_date - from_date).days or 1,
                    'count': len(offenders),
                    'worst': offenders[:10],
                },
            }
    except Exception as e:
        logger.warning(f"TEACHER_LOW_ATTEND_PCT check failed: {e}")
    return None


def _check_batch_low_attendance(rule, window_start, threshold):
    try:
        from attendance.models import Attendance
        from django.db.models import Count, Q
        from_date, to_date = _attend_window_dates(window_start)

        agg = (
            Attendance.objects
            .filter(
                tenant=rule.tenant,
                user_type='STUDENT',
                attendance_date__range=(from_date, to_date),
                batch__isnull=False,
            )
            .values('batch')
            .annotate(
                total=Count('id'),
                present=Count('id', filter=Q(status__in=['PRESENT', 'LATE', 'HALF_DAY'])),
            )
            .filter(total__gte=5)
        )
        offenders = []
        for row in agg:
            if row['total'] == 0:
                continue
            pct = (row['present'] / row['total']) * 100
            if pct < threshold:
                offenders.append({
                    'batch_id': str(row['batch']),
                    'percentage': round(pct, 1),
                    'present': row['present'],
                    'total': row['total'],
                })
        if offenders:
            offenders.sort(key=lambda x: x['percentage'])
            return {
                'message': f"{len(offenders)} batch(es) below {int(threshold)}% average attendance",
                'details': {
                    'threshold': float(threshold),
                    'window_days': (to_date - from_date).days or 1,
                    'count': len(offenders),
                    'worst': offenders[:10],
                },
            }
    except Exception as e:
        logger.warning(f"BATCH_LOW_AVG_ATTEND check failed: {e}")
    return None


def _tail_log(path, n=15):
    """Return the last `n` lines of `path`, or empty string if missing."""
    try:
        import os
        if not os.path.exists(path):
            return ''
        with open(path, 'rb') as fh:
            fh.seek(0, 2)
            size = fh.tell()
            blk = 4096
            data = b''
            while size > 0 and data.count(b'\n') <= n:
                step = min(blk, size)
                size -= step
                fh.seek(size)
                data = fh.read(step) + data
        return b'\n'.join(data.splitlines()[-n:]).decode('utf-8', errors='replace')
    except Exception:
        return ''


def _send_alert_email(rule, log):
    """Send alert notification email.

    Falls back to a local file outbox (logs/alerts_outbox/) when SMTP credentials
    are not configured, so alerts are still observable in non-prod environments.
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        import os

        # Per-rule recipients + global DL_ALERTS, deduped
        per_rule = [e.strip() for e in (rule.notify_emails or '').split(',') if e.strip()]
        dl = list(getattr(settings, 'DL_ALERTS', []) or [])
        recipients = sorted({*per_rule, *dl})
        if not recipients:
            return

        severity_emoji = {'INFO': 'ℹ️', 'WARNING': '⚠️', 'CRITICAL': '🚨'}.get(rule.severity, '🔔')

        # Log file references — surfaced in the email body so on-call has
        # immediate paths to investigate.
        log_dir = os.path.join(getattr(settings, 'BASE_DIR', '/app'), 'logs')
        log_paths = {
            'app':      os.path.join(log_dir, 'lms.log'),
            'celery':   os.path.join(log_dir, 'celery.log'),
            'alerts':   os.path.join(log_dir, 'alerts.log'),
            'gunicorn': os.path.join(log_dir, 'gunicorn.log'),
        }
        log_refs_lines = [f"  {name:<8} {path}" for name, path in log_paths.items()]
        tail = _tail_log(log_paths['app'], 10)

        subject = f'{severity_emoji} LMS Alert: {rule.name}'
        body = (
            f"Alert Rule: {rule.name}\n"
            f"Category: {rule.get_category_display()}\n"
            f"Severity: {rule.get_severity_display()}\n"
            f"Time: {log.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Message:\n{log.message}\n\n"
            f"───── Log files (on the API container) ─────\n"
            + '\n'.join(log_refs_lines) + '\n\n'
            + (f"───── Last 10 lines of lms.log ─────\n{tail}\n\n" if tail else '')
            + f"Recipients: {', '.join(recipients)}\n"
            f"Please review this alert in the admin console: /admin/alerts/alertlog/\n"
        )

        smtp_configured = bool(getattr(settings, 'EMAIL_HOST_USER', '')) and \
            bool(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))

        if smtp_configured:
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'alerts@lms-enterprise.com'),
                    recipient_list=recipients,
                    fail_silently=False,
                )
                logger.info(f"Alert email sent to {recipients} for rule {rule.name}")
            except Exception as smtp_err:
                # SMTP creds present but rejected (common with Gmail + regular pwd
                # when 2FA is on). Don't lose the alert — write to outbox.
                logger.warning(
                    f"SMTP send failed ({smtp_err}); falling back to outbox. "
                    f"If using Gmail with 2FA, generate an App Password "
                    f"at https://myaccount.google.com/apppasswords"
                )
                _write_outbox(log, recipients, subject, body)
        else:
            _write_outbox(log, recipients, subject, body)

        log.is_email_sent = True
        log.save(update_fields=['is_email_sent'])
    except Exception as e:
        logger.error(f"Failed to send alert email for rule {rule.name}: {e}")


def _write_outbox(log, recipients, subject, body):
    """Write a .eml-style file to logs/alerts_outbox/ as fallback."""
    import os
    from django.conf import settings
    outbox = os.path.join(getattr(settings, 'BASE_DIR', '/app'), 'logs', 'alerts_outbox')
    os.makedirs(outbox, exist_ok=True)
    fname = f"{log.triggered_at.strftime('%Y%m%dT%H%M%S')}_{log.id}.eml"
    with open(os.path.join(outbox, fname), 'w', encoding='utf-8') as fh:
        fh.write(f"To: {', '.join(recipients)}\n")
        fh.write(f"Subject: {subject}\n\n")
        fh.write(body)
    logger.info(f"Alert email written to outbox: {fname} (recipients: {recipients})")
