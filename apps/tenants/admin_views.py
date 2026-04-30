"""
Tenant admin views — switch tenant for admin panel.
"""
import json
from django.http import JsonResponse
from django.views import View
from tenants.models import Tenant


class SwitchTenantView(View):
    """POST to switch the active tenant in admin session."""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST

        tenant_id = data.get('tenant_id', '')

        if tenant_id == '' or tenant_id == 'all':
            request.session.pop('admin_tenant_id', None)
            request.session.pop('admin_tenant_name', None)
            return JsonResponse({'success': True, 'tenant': None, 'label': 'All Tenants'})

        try:
            tenant = Tenant.objects.get(id=tenant_id)
            request.session['admin_tenant_id'] = str(tenant.id)
            request.session['admin_tenant_name'] = tenant.name
            return JsonResponse({
                'success': True,
                'tenant': str(tenant.id),
                'label': tenant.name,
            })
        except Tenant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Tenant not found'}, status=404)
