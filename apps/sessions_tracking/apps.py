from django.apps import AppConfig


class SessionsTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.UUIDField'
    name = 'sessions_tracking'
    verbose_name = 'Session & Activity Tracking'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        user_logged_in.connect(_on_admin_login)


def _on_admin_login(sender, request, user, **kwargs):
    """Record every Django admin login in LoginHistory + create/update UserSession + UserDevice."""
    try:
        from sessions_tracking.models import LoginHistory, UserSession
        from sessions_tracking.middleware import get_client_ip, get_or_create_device
        from tenants.models import Tenant
        from django.utils import timezone
        from datetime import timedelta

        tenant = Tenant.objects.first()
        if not tenant:
            return

        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:2000]

        # Create / update the UserDevice record
        device = None
        try:
            device = get_or_create_device(tenant, user.pk, 'ADMIN', ua)
        except Exception:
            pass

        # Ensure session key exists
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key or f'admin-{user.pk}'

        # Use update_or_create to handle unique constraint on session_token
        session_obj, created = UserSession.objects.update_or_create(
            session_token=session_key,
            defaults={
                'tenant': tenant,
                'user_id': user.pk,
                'user_type': 'ADMIN',
                'device': device,
                'ip_address': ip,
                'status': 'ACTIVE',
                'started_at': timezone.now(),
                'expires_at': timezone.now() + timedelta(hours=8),
                'total_active_seconds': 0,
            },
        )

        LoginHistory.objects.create(
            tenant=tenant,
            user_id=user.pk,
            user_type='ADMIN',
            username_attempted=user.username or user.email,
            result='SUCCESS',
            ip_address=ip,
            device=device,
            user_agent=ua,
            session_id=session_obj.id,
        )
    except Exception:
        pass  # never block login
