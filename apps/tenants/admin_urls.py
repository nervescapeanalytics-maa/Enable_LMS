from django.urls import path
from tenants.admin_views import SwitchTenantView

urlpatterns = [
    path('', SwitchTenantView.as_view(), name='admin-switch-tenant'),
]
