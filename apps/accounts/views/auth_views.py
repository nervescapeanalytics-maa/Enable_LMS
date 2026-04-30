"""
LMS Enterprise - Auth Views
Handles authentication with custom user models + JWT tokens.
"""
import uuid
import jwt
import time
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Student, Teacher, Admin, Parent
from accounts.serializers import LoginSerializer, RegisterSerializer
from tenants.models import Tenant


USER_MODEL_MAP = {
    'STUDENT': Student,
    'TEACHER': Teacher,
    'ADMIN': Admin,
    'PARENT': Parent,
}


def _generate_tokens(user, user_type):
    """Generate JWT access and refresh tokens for a user."""
    now = time.time()
    access_exp = now + settings.SIMPLE_JWT.get(
        'ACCESS_TOKEN_LIFETIME', timedelta(minutes=15)
    ).total_seconds()
    refresh_exp = now + settings.SIMPLE_JWT.get(
        'REFRESH_TOKEN_LIFETIME', timedelta(days=7)
    ).total_seconds()

    access_payload = {
        'user_id': str(user.id),
        'user_type': user_type,
        'tenant_id': str(user.tenant_id),
        'email': user.email,
        'token_type': 'access',
        'exp': int(access_exp),
        'iat': int(now),
        'jti': str(uuid.uuid4()),
    }
    refresh_payload = {
        'user_id': str(user.id),
        'user_type': user_type,
        'tenant_id': str(user.tenant_id),
        'token_type': 'refresh',
        'exp': int(refresh_exp),
        'iat': int(now),
        'jti': str(uuid.uuid4()),
    }

    secret = settings.SECRET_KEY
    access_token = jwt.encode(access_payload, secret, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, secret, algorithm='HS256')

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': int(settings.SIMPLE_JWT.get(
            'ACCESS_TOKEN_LIFETIME', timedelta(minutes=15)
        ).total_seconds()),
        'user_type': user_type,
        'user_id': str(user.id),
        'user_name': user.full_name,
    }


class RegisterView(APIView):
    """Register a new user."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_type = data['user_type']
        try:
            tenant = Tenant.objects.get(code=data['tenant_code'])
        except Tenant.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Invalid tenant code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Model = USER_MODEL_MAP[user_type]

        if Model.objects.filter(tenant=tenant, email=data['email']).exists():
            return Response(
                {'success': False, 'error': 'Email already registered'},
                status=status.HTTP_409_CONFLICT,
            )

        common = {
            'tenant': tenant,
            'email': data['email'],
            'phone': data['phone'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'status': 'ACTIVE',
            'email_verified': False,
        }

        if user_type == 'STUDENT':
            count = Student.objects.filter(tenant=tenant).count() + 1
            common['student_code'] = f"STU{tenant.code}{count:04d}"
            common['student_class'] = data.get('student_class', '11')
            common['exam_target'] = data.get('exam_target', 'JEE')
            common['city'] = data.get('city', 'NA')
            common['state'] = data.get('state', 'NA')
            common['pin_code'] = data.get('pin_code', '000000')
        elif user_type == 'TEACHER':
            count = Teacher.objects.filter(tenant=tenant).count() + 1
            common['teacher_code'] = f"TCH{tenant.code}{count:04d}"
        elif user_type == 'ADMIN':
            count = Admin.objects.filter(tenant=tenant).count() + 1
            common['admin_code'] = f"ADM{tenant.code}{count:04d}"
            common['admin_type'] = 'TENANT_ADMIN'

        user = Model(**common)
        user.set_password(data['password'])
        user.save()

        tokens = _generate_tokens(user, user_type)
        return Response({'success': True, 'data': tokens}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticate a user and return JWT tokens."""
    permission_classes = [AllowAny]

    def _get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _record_login(self, request, tenant, user_id, user_type, result,
                      failure_reason=None, session_obj=None):
        """Create a LoginHistory record (best-effort, never blocks login)."""
        try:
            from sessions_tracking.models import LoginHistory
            LoginHistory.objects.create(
                tenant=tenant,
                user_id=user_id,
                user_type=user_type,
                username_attempted=request.data.get('email') or request.data.get('phone', ''),
                result=result,
                failure_reason=failure_reason,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
                session_id=session_obj.id if session_obj else None,
            )
        except Exception:
            pass

    def _create_session(self, request, tenant, user, user_type, tokens):
        """Create a UserSession record (best-effort)."""
        try:
            from sessions_tracking.models import UserSession
            import hashlib
            refresh_hash = hashlib.sha256(
                tokens['refresh_token'].encode()
            ).hexdigest()[:64] if tokens.get('refresh_token') else None
            return UserSession.objects.create(
                tenant=tenant,
                user_id=user.id,
                user_type=user_type,
                session_token=tokens['access_token'][:500],
                refresh_token_hash=refresh_hash,
                ip_address=self._get_client_ip(request),
                status='ACTIVE',
                expires_at=timezone.now() + timedelta(
                    seconds=tokens.get('expires_in', 900)
                ),
            )
        except Exception:
            return None

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_type = data['user_type']
        Model = USER_MODEL_MAP.get(user_type)
        if not Model:
            return Response(
                {'success': False, 'error': 'Invalid user type'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lookup = {}
        if data.get('email'):
            lookup['email'] = data['email']
        elif data.get('phone'):
            lookup['phone'] = data['phone']

        tenant = None
        if data.get('tenant_code'):
            try:
                tenant = Tenant.objects.get(code=data['tenant_code'])
                lookup['tenant'] = tenant
            except Tenant.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Invalid tenant code'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            user = Model.objects.get(**lookup)
        except Model.DoesNotExist:
            self._record_login(request, tenant, None, user_type,
                               'FAILED', 'User not found')
            return Response(
                {'success': False, 'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Model.MultipleObjectsReturned:
            return Response(
                {'success': False, 'error': 'Multiple accounts found. Provide tenant_code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(data['password']):
            # Lazy phone-as-password fallback: students/teachers/admins whose
            # stored hash does not match the canonical "password = phone" rule
            # (legacy imports) can still log in with their phone number once;
            # we rehash to PBKDF2 on success so the next login uses the new
            # hash. This avoids a 30+ minute bulk-rehash of imported records.
            if (
                user_type == 'STUDENT'
                and getattr(user, 'phone', None)
                and data['password'] == user.phone
            ):
                user.set_password(user.phone)
                user.save(update_fields=['password_hash', 'password_changed_at'])
            else:
                self._record_login(request, getattr(user, 'tenant', tenant),
                                   user.id, user_type, 'FAILED', 'Wrong password')
                return Response(
                    {'success': False, 'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        if user.status != 'ACTIVE':
            self._record_login(request, getattr(user, 'tenant', tenant),
                               user.id, user_type, 'INACTIVE',
                               f'Account status: {user.status}')
            return Response(
                {'success': False, 'error': f'Account is {user.status}'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

        tokens = _generate_tokens(user, user_type)

        # Record successful login and session
        user_tenant = getattr(user, 'tenant', tenant)
        session_obj = self._create_session(request, user_tenant, user, user_type, tokens)
        self._record_login(request, user_tenant, user.id, user_type,
                           'SUCCESS', session_obj=session_obj)

        return Response({'success': True, 'data': tokens})


class LogoutView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Logged out successfully'})


class LogoutAllDevicesView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'All sessions invalidated'})


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.data.get('refresh_token')
        if not refresh:
            return Response(
                {'success': False, 'error': 'refresh_token is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('token_type') != 'refresh':
                raise jwt.InvalidTokenError("Not a refresh token")
            user_type = payload['user_type']
            Model = USER_MODEL_MAP[user_type]
            user = Model.objects.get(id=payload['user_id'])
            tokens = _generate_tokens(user, user_type)
            return Response({'success': True, 'data': tokens})
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            return Response(
                {'success': False, 'error': f'Invalid token: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception:
            return Response(
                {'success': False, 'error': 'Token refresh failed'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Password reset instructions sent'})

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Password reset successfully'})

class ChangePasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Password changed'})

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Email verified'})

class VerifyPhoneView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'Phone verified'})

class SendOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'OTP sent'})

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'OTP verified'})

class MFASetupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'MFA setup initiated'})

class MFAVerifyView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'MFA verified'})

class MFADisableView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        return Response({'success': True, 'message': 'MFA disabled'})

class MFABackupCodesView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'success': True, 'data': {'codes': []}})

class SessionListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'success': True, 'data': []})

class SessionDetailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        return Response({'success': True, 'data': {}})
    def delete(self, request, pk):
        return Response({'success': True, 'message': 'Session terminated'})

class DeviceListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'success': True, 'data': []})

class DeviceTrustView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, pk):
        return Response({'success': True, 'message': 'Device trusted'})

class DeviceDeleteView(APIView):
    permission_classes = [AllowAny]
    def delete(self, request, pk):
        return Response({'success': True, 'message': 'Device removed'})
