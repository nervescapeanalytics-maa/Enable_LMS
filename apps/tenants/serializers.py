from rest_framework import serializers
from tenants.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_subdomain(self, value):
        """Ensure subdomain is lowercase and alphanumeric."""
        value = value.lower().strip()
        if not value.isalnum():
            raise serializers.ValidationError("Subdomain must be alphanumeric.")
        reserved = ['www', 'admin', 'api', 'app', 'mail', 'ftp', 'static', 'media']
        if value in reserved:
            raise serializers.ValidationError(f"'{value}' is a reserved subdomain.")
        return value
