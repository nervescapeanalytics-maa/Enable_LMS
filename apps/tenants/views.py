from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from tenants.models import Tenant
from tenants.serializers import TenantSerializer


class TenantListCreateView(generics.ListCreateAPIView):
    """List all tenants or create a new tenant (Super Admin only)."""
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAdminUser]


class TenantDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a tenant (Super Admin only)."""
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAdminUser]


class TenantStatsView(APIView):
    """Get statistics for a specific tenant."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        stats = {
            'tenant_id': str(tenant.id),
            'tenant_name': tenant.name,
            'plan_type': tenant.plan_type,
            'status': tenant.status,
            # Counts will be populated from related models
            'student_count': 0,
            'teacher_count': 0,
            'active_classes': 0,
            'total_tests': 0,
        }
        return Response(stats)
