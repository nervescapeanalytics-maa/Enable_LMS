"""
LMS Enterprise - Audit Middleware
Automatically records audit log entries for mutating API requests.
"""
import json
import uuid
from django.utils import timezone


class AuditMiddleware:
    """Middleware to capture audit trails for write operations."""

    MUTATING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    EXCLUDED_PATHS = {
        '/api/v3/auth/token/refresh/',
        '/health/',
        '/ready/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method in self.MUTATING_METHODS and request.path not in self.EXCLUDED_PATHS:
            try:
                self._create_audit_log(request, response)
            except Exception:
                pass  # Audit failures should never break the request

        return response

    def _create_audit_log(self, request, response):
        from audit.models import AuditLog

        action_map = {
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
        }

        user_id = None
        user_type = None
        username = None
        tenant_id = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = getattr(request.user, 'id', None)
            user_type = getattr(request.user, 'user_type', 'UNKNOWN')
            username = getattr(request.user, 'username', str(user_id))

        if hasattr(request, 'tenant') and request.tenant:
            tenant_id = request.tenant.id

        # Parse request body (limit size)
        request_body = None
        if request.content_type == 'application/json':
            try:
                body = request.body[:10000]
                request_body = json.loads(body)
                # Redact sensitive fields
                for key in ('password', 'token', 'secret', 'access_token', 'refresh_token'):
                    if key in request_body:
                        request_body[key] = '***REDACTED***'
            except (json.JSONDecodeError, Exception):
                pass

        AuditLog.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            user_type=user_type,
            username=username,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            session_id=getattr(request, 'session_id', None),
            action=action_map.get(request.method, 'SYSTEM'),
            action_description=f"{request.method} {request.path}",
            http_method=request.method,
            request_path=request.path[:1000],
            request_body=request_body,
            response_status=response.status_code,
            severity='INFO' if response.status_code < 400 else 'WARNING',
            is_security_event=request.path.startswith('/api/v3/auth/'),
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
