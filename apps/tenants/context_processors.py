"""
Tenant context processor for templates.
Provides tenant information to every template, including the admin panel.
"""
from tenants.models import Tenant


def tenant_context(request):
    """Add tenant information to template context."""
    tenant = getattr(request, 'tenant', None)

    ctx = {
        'tenant': tenant,
        'tenant_name': tenant.name if tenant else 'LMS Platform',
        'tenant_logo': tenant.logo_url if tenant else None,
        'primary_color': tenant.primary_color if tenant else '#1E3A5F',
    }

    if request.path.startswith('/admin/'):
        try:
            all_tenants = Tenant.objects.filter(
                status__in=['ACTIVE', 'active', 'TRIAL']
            ).order_by('name')
            ctx['all_tenants'] = all_tenants

            selected_id = request.session.get('admin_tenant_id')
            if selected_id:
                try:
                    ctx['selected_tenant'] = Tenant.objects.get(id=selected_id)
                except Tenant.DoesNotExist:
                    ctx['selected_tenant'] = None
            else:
                ctx['selected_tenant'] = None

            is_super = False
            user_id = request.session.get('_auth_user_id')
            if user_id:
                from accounts.models import Admin as AdminModel
                try:
                    adm = AdminModel.objects.get(id=user_id)
                    is_super = adm.admin_type == 'SUPER_ADMIN'
                except Exception:
                    pass
            ctx['is_super_admin'] = is_super or request.user.is_superuser
        except Exception:
            ctx['all_tenants'] = []
            ctx['selected_tenant'] = None
            ctx['is_super_admin'] = getattr(request.user, 'is_superuser', False)

    return ctx
