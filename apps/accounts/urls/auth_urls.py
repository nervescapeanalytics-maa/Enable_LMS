"""
Authentication URLs
"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from accounts.views import auth_views

app_name = 'auth'


class _RootView(APIView):
    # permission_classes uses IsAuthenticated default from settings
    def get(self, request):
        return Response({'success': True, 'data': {
            'endpoints': {
                'login': 'POST /api/v1/auth/login',
                'register': 'POST /api/v1/auth/register',
                'logout': 'POST /api/v1/auth/logout',
                'refresh-token': 'POST /api/v1/auth/refresh-token',
                'forgot-password': 'POST /api/v1/auth/forgot-password',
                'reset-password': 'POST /api/v1/auth/reset-password',
                'change-password': 'POST /api/v1/auth/change-password',
                'verify-email': 'POST /api/v1/auth/verify-email',
                'send-otp': 'POST /api/v1/auth/send-otp',
                'verify-otp': 'POST /api/v1/auth/verify-otp',
                'mfa-setup': 'POST /api/v1/auth/mfa/setup',
                'sessions': '/api/v1/auth/sessions',
                'devices': '/api/v1/auth/devices',
            }
        }})


urlpatterns = [
    path('', _RootView.as_view(), name='root'),

    # Registration & Login
    path('register', auth_views.RegisterView.as_view(), name='register'),
    path('login', auth_views.LoginView.as_view(), name='login'),
    path('logout', auth_views.LogoutView.as_view(), name='logout'),
    path('logout-all-devices', auth_views.LogoutAllDevicesView.as_view(), name='logout-all'),
    path('refresh-token', auth_views.RefreshTokenView.as_view(), name='refresh-token'),

    # Password
    path('forgot-password', auth_views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password', auth_views.ResetPasswordView.as_view(), name='reset-password'),
    path('change-password', auth_views.ChangePasswordView.as_view(), name='change-password'),

    # Verification
    path('verify-email', auth_views.VerifyEmailView.as_view(), name='verify-email'),
    path('verify-phone', auth_views.VerifyPhoneView.as_view(), name='verify-phone'),
    path('send-otp', auth_views.SendOTPView.as_view(), name='send-otp'),
    path('verify-otp', auth_views.VerifyOTPView.as_view(), name='verify-otp'),

    # MFA
    path('mfa/setup', auth_views.MFASetupView.as_view(), name='mfa-setup'),
    path('mfa/verify', auth_views.MFAVerifyView.as_view(), name='mfa-verify'),
    path('mfa/disable', auth_views.MFADisableView.as_view(), name='mfa-disable'),
    path('mfa/backup-codes', auth_views.MFABackupCodesView.as_view(), name='mfa-backup-codes'),

    # Sessions & Devices
    path('sessions', auth_views.SessionListView.as_view(), name='sessions'),
    path('sessions/<uuid:pk>', auth_views.SessionDetailView.as_view(), name='session-detail'),
    path('devices', auth_views.DeviceListView.as_view(), name='devices'),
    path('devices/<uuid:pk>/trust', auth_views.DeviceTrustView.as_view(), name='device-trust'),
    path('devices/<uuid:pk>', auth_views.DeviceDeleteView.as_view(), name='device-delete'),
]
