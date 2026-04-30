"""
Session & Activity Tracking Middleware
Tracks admin page views, updates session last_activity_at, captures real IP,
and creates UserDevice records from User-Agent parsing.
"""
import hashlib
import re
import time
from django.utils import timezone


def get_client_ip(request):
    """Extract real client IP from proxy headers with proper fallback chain."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # First IP in the chain is the real client
        ip = xff.split(',')[0].strip()
        if ip and ip != 'unknown':
            return ip
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip and real_ip != 'unknown':
        return real_ip
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def parse_user_agent(ua_string):
    """Parse User-Agent string into device/browser/OS info without third-party libs."""
    ua = ua_string or ''
    info = {
        'device_type': 'OTHER',
        'device_name': 'Unknown',
        'os_name': '',
        'os_version': '',
        'browser_name': '',
        'browser_version': '',
    }

    # Device type
    ua_lower = ua.lower()
    if any(k in ua_lower for k in ('mobile', 'android', 'iphone', 'ipod')):
        info['device_type'] = 'MOBILE'
    elif any(k in ua_lower for k in ('ipad', 'tablet')):
        info['device_type'] = 'TABLET'
    elif any(k in ua_lower for k in ('windows', 'macintosh', 'mac os', 'linux', 'x11', 'cros')):
        info['device_type'] = 'DESKTOP'

    # OS
    os_patterns = [
        (r'Windows NT ([\d.]+)', 'Windows', {
            '10.0': '10/11', '6.3': '8.1', '6.2': '8', '6.1': '7',
        }),
        (r'Mac OS X ([\d_]+)', 'macOS', None),
        (r'Android ([\d.]+)', 'Android', None),
        (r'iPhone OS ([\d_]+)', 'iOS', None),
        (r'iPad.*OS ([\d_]+)', 'iPadOS', None),
        (r'Linux', 'Linux', None),
        (r'CrOS', 'ChromeOS', None),
    ]
    for pattern, name, version_map in os_patterns:
        m = re.search(pattern, ua)
        if m:
            info['os_name'] = name
            ver = m.group(1).replace('_', '.') if m.lastindex else ''
            if version_map and ver in version_map:
                ver = version_map[ver]
            info['os_version'] = ver
            break

    # Browser (order matters — check specific before generic)
    browser_patterns = [
        (r'Edg[e/]?([\d.]+)', 'Edge'),
        (r'OPR/([\d.]+)', 'Opera'),
        (r'Brave', 'Brave'),
        (r'Vivaldi/([\d.]+)', 'Vivaldi'),
        (r'Chrome/([\d.]+)', 'Chrome'),
        (r'Safari/([\d.]+).*Version/([\d.]+)', 'Safari'),
        (r'Firefox/([\d.]+)', 'Firefox'),
    ]
    for pattern, name in browser_patterns:
        m = re.search(pattern, ua)
        if m:
            info['browser_name'] = name
            # Pick the last group as version (Safari's version is in group 2)
            info['browser_version'] = m.group(m.lastindex) if m.lastindex else ''
            break

    # Device name
    if info['os_name'] and info['browser_name']:
        info['device_name'] = f"{info['os_name']} — {info['browser_name']}"
    elif info['os_name']:
        info['device_name'] = info['os_name']

    return info


def get_device_fingerprint(user_id, ua_string):
    """Create a stable fingerprint from user_id + User-Agent."""
    raw = f"{user_id}:{ua_string or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def get_or_create_device(tenant, user_id, user_type, ua_string):
    """Find or create a UserDevice record from the User-Agent."""
    from sessions_tracking.models import UserDevice

    fingerprint = get_device_fingerprint(user_id, ua_string)
    try:
        device = UserDevice.objects.get(device_fingerprint=fingerprint)
        # Update last_seen and bump session counter
        device.last_seen = timezone.now()
        device.total_sessions = (device.total_sessions or 0) + 1
        device.save(update_fields=['last_seen', 'total_sessions'])
        return device
    except UserDevice.DoesNotExist:
        pass

    info = parse_user_agent(ua_string)
    device = UserDevice.objects.create(
        tenant=tenant,
        user_id=user_id,
        user_type=user_type,
        device_fingerprint=fingerprint,
        device_name=info['device_name'],
        device_type=info['device_type'],
        os_name=info['os_name'],
        os_version=info['os_version'],
        browser_name=info['browser_name'],
        browser_version=info['browser_version'],
        user_agent=(ua_string or '')[:2000],
        is_trusted=True,
        total_sessions=1,
    )
    return device


# Paths to skip (static, media, health, favicon)
SKIP_PATTERNS = re.compile(
    r'^/(static|staticfiles|media|favicon\.ico|health|__debug__|ws/)'
)


class SessionTrackingMiddleware:
    """
    Middleware that:
    1. Updates UserSession.last_activity_at on every admin request
    2. Creates UserActivity records for admin page views
    3. Captures correct IP address
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.monotonic()
        response = self.get_response(request)

        # Only track authenticated users on non-static paths
        if (
            not getattr(request, 'user', None)
            or not request.user.is_authenticated
            or SKIP_PATTERNS.match(request.path)
        ):
            return response

        # Only track admin pages and API calls (not OPTIONS, HEAD etc.)
        if request.method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
            return response

        # Only track if user is staff (admin) — extend later for students/teachers via API
        if not getattr(request.user, 'is_staff', False):
            return response

        try:
            self._track_session_and_activity(request, response, start_time)
        except Exception:
            pass  # Never break the request cycle

        return response

    def _track_session_and_activity(self, request, response, start_time):
        from sessions_tracking.models import UserSession, UserActivity
        from tenants.models import Tenant

        session_key = request.session.session_key
        if not session_key:
            return

        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:2000]
        tenant = Tenant.objects.first()
        if not tenant:
            return

        # Ensure a UserDevice exists for this user+agent combo
        device = None
        try:
            device = get_or_create_device(tenant, request.user.pk, 'ADMIN', ua)
        except Exception:
            pass

        # Find the active session for this user
        user_session = UserSession.objects.filter(
            user_id=request.user.pk,
            session_token=session_key,
            status='ACTIVE',
        ).first()

        if not user_session:
            # Maybe the session was created with a different token — find any active session
            user_session = UserSession.objects.filter(
                user_id=request.user.pk,
                status='ACTIVE',
            ).order_by('-started_at').first()

        if user_session:
            # Update last_activity_at and fix IP if it was wrong
            update_fields = ['last_activity_at']
            user_session.last_activity_at = timezone.now()
            if user_session.ip_address in (None, '', '0.0.0.0') and ip not in ('0.0.0.0', '127.0.0.1'):
                user_session.ip_address = ip
                update_fields.append('ip_address')
            # Link device if not yet linked
            if device and not user_session.device_id:
                user_session.device = device
                update_fields.append('device')
            # Compute total_active_seconds
                update_fields.append('ip_address')
            # Compute total_active_seconds
            if user_session.started_at:
                delta = timezone.now() - user_session.started_at
                user_session.total_active_seconds = int(delta.total_seconds())
                update_fields.append('total_active_seconds')
            user_session.save(update_fields=update_fields)

        # Create UserActivity for admin page views (GET requests only, skip AJAX/API)
        is_admin_page = request.path.startswith('/admin/')
        if is_admin_page and request.method == 'GET' and response.status_code == 200:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            # Determine activity type
            if '/add/' in request.path or '/change/' in request.path:
                activity_type = 'PROFILE_UPDATE'
                desc = f"Admin form: {request.path}"
            else:
                activity_type = 'PAGE_VIEW'
                desc = f"Admin page: {request.path}"

            UserActivity.objects.create(
                tenant=tenant,
                session=user_session,
                user_id=request.user.pk,
                user_type='ADMIN',
                activity_type=activity_type,
                activity_description=desc[:500],
                page_url=request.build_absolute_uri()[:1000],
                referrer_url=(request.META.get('HTTP_REFERER') or '')[:1000] or None,
                ip_address=ip,
                duration_seconds=max(duration_ms // 1000, 0),
            )
