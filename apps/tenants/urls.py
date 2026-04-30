from django.urls import path
from tenants import views

app_name = 'tenants'

urlpatterns = [
    path('', views.TenantListCreateView.as_view(), name='tenant-list'),
    path('<uuid:pk>/', views.TenantDetailView.as_view(), name='tenant-detail'),
    path('<uuid:pk>/stats/', views.TenantStatsView.as_view(), name='tenant-stats'),
]
