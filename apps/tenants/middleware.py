"""
Tenant Middleware - Resolves tenant from request subdomain/domain.
Also sets the PostgreSQL session variable `app.current_tenant_id`
for Row-Level Security enforcement at the database layer.
"""
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from tenants.models import Tenant
import logging

logger = logging.getLogger('lms')


def _set_pg_tenant(tenant_id):
    """Set the PostgreSQL session variable for RLS."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant_id', %s, false)",
                [str(tenant_id) if tenant_id else ''],
            )
    except Exception:
        pass


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to resolve the current tenant from request host.
    Sets request.tenant for use in views and querysets.
    Also sets the PostgreSQL session var for RLS enforcement.
    """
    EXEMPT_PATHS = ['/admin/', '/staff/', '/api/v1/system/health/']

    def process_request(self, request):
        for path in self.EXEMPT_PATHS:
            if request.path.startswith(path):
                request.tenant = None
                _set_pg_tenant('')
                return None

        host = request.get_host().split(':')[0]

        tenant = Tenant.objects.filter(
            custom_domain=host,
            status__in=[Tenant.Status.ACTIVE, Tenant.Status.TRIAL]
        ).first()

        if not tenant:
            parts = host.split('.')
            if len(parts) >= 3:
                subdomain = parts[0]
                tenant = Tenant.objects.filter(
                    subdomain=subdomain,
                    status__in=[Tenant.Status.ACTIVE, Tenant.Status.TRIAL]
                ).first()

        if not tenant and not request.path.startswith('/api/v1/admin/tenants'):
            tenant_header = request.META.get('HTTP_X_TENANT_ID')
            if tenant_header:
                tenant = Tenant.objects.filter(
                    id=tenant_header,
                    status__in=[Tenant.Status.ACTIVE, Tenant.Status.TRIAL]
                ).first()

        if not tenant:
            session_tenant = getattr(request, 'session', {}).get('tenant_id')
            if session_tenant:
                tenant = Tenant.objects.filter(
                    id=session_tenant,
                    status__in=[Tenant.Status.ACTIVE, Tenant.Status.TRIAL, 'active']
                ).first()

        request.tenant = tenant
        _set_pg_tenant(tenant.id if tenant else '')
        return None
