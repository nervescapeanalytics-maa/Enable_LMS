"""
Frontend Views – Home, Login, Register, Dashboards
"""
import json
import jwt
from datetime import datetime, timedelta, date
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F

from accounts.models import Student, Teacher, Admin
from academics.models import Users
from tenants.models import Tenant
from audit.models import AuditLog


def _load_website_settings():
    """Load all active WebsiteSettings into a nested dict and return helper functions."""
    from system_config.models import WebsiteSetting
    settings = {}
    for ws in WebsiteSetting.objects.filter(is_active=True):
        settings.setdefault(ws.section, {})[ws.setting_key] = ws

    def s(section, key, default=''):
        obj = settings.get(section, {}).get(key)
        if obj:
            return obj.setting_value or default
        return default

    def s_url(section, key, default=''):
        obj = settings.get(section, {}).get(key)
        if obj:
            return obj.media_url or obj.setting_value or default
        return default

    return settings, s, s_url


def _common_ctx(s, s_url=None):
    """Build context dict with common settings shared by all pages."""
    if s_url is None:
        s_url = s
    return {
        # Stats
        'stat_students': s('HERO', 'stat_students', '15,000+'),
        'stat_schools': s('HERO', 'stat_schools', '380+'),
        'stat_classes': s('HERO', 'stat_classes', '1,200+'),
        'stat_success': s('HERO', 'stat_success', '95%'),
        'stat_teachers': s('HERO', 'stat_teachers', '50+'),
        'stat_jnvs': s('HERO', 'stat_jnvs', '350+'),
        'stat_partners': s('HERO', 'stat_partners', '7+'),
        # Contact
        'contact_phone': s('CONTACT', 'phone', '+91-76070 02100'),
        'contact_email': s('CONTACT', 'email', 'exnavodayanfoundation1@gmail.com'),
        'contact_address': s('CONTACT', 'address'),
        'contact_support_email': s('CONTACT', 'support_email'),
        'office_hours': s('CONTACT', 'office_hours', 'Mon-Sat: 9:00 AM - 6:00 PM'),
        # Social
        'social_youtube': s('SOCIAL', 'youtube_url'),
        'social_facebook': s('SOCIAL', 'facebook_url'),
        'social_twitter': s('SOCIAL', 'twitter_url'),
        'social_linkedin': s('SOCIAL', 'linkedin_url'),
        'social_instagram': s('SOCIAL', 'instagram_url'),
        # Branding
        'brand_name': s('BRANDING', 'brand_name', 'ENABLE PROGRAM'),
        'logo_url': s_url('BRANDING', 'logo_url'),
        'favicon_url': s_url('BRANDING', 'favicon_url'),
        'primary_color': s('BRANDING', 'primary_color', '#844FC1'),
        'secondary_color': s('BRANDING', 'secondary_color', '#6D28D9'),
        # SEO
        'meta_title': s('SEO', 'meta_title', 'ENABLE PROGRAM — Learning Management System'),
        'meta_description': s('SEO', 'meta_description'),
        'meta_keywords': s('SEO', 'meta_keywords'),
        'og_image': s_url('SEO', 'og_image'),
        # Footer
        'footer_tagline': s('FOOTER', 'footer_tagline'),
        'footer_copyright': s('FOOTER', 'footer_copyright', '© 2026 Ex Navodayan Foundation. All rights reserved.'),
        'footer_links': s('FOOTER', 'footer_links'),
        'design_credit': s('FOOTER', 'design_credit', 'ERPDSOFT'),
        'design_credit_url': s('FOOTER', 'design_credit_url', 'https://erpdsoft.com'),
        # Founder
        'founder_name': s('FOUNDER', 'founder_name', 'Santosh Pillai'),
        'founder_title': s('FOUNDER', 'founder_title', 'Founder & CEO'),
        'founder_bio': s('FOUNDER', 'founder_bio'),
        'founder_photo': s_url('FOUNDER', 'founder_photo'),
        # Section titles
        'news_title': s('NEWS', 'news_title', 'Latest Updates'),
        'programs_title': s('PROGRAMS', 'programs_title', 'Our Programs'),
        'testimonials_title': s('TESTIMONIALS', 'testimonials_title', 'Student Success Stories'),
    }


class HomeView(View):
    """Landing page — pulls content from WebsiteSetting, WebsiteNews, Testimonial, FooterConfig."""
    def get(self, request):
        from system_config.models import WebsiteNews, Testimonial, FooterConfig, TickerItem

        settings, s, s_url = _load_website_settings()

        # News (published, show_on_homepage)
        news = WebsiteNews.objects.filter(
            is_published=True, show_on_homepage=True
        ).order_by('-priority', '-publish_date')[:3]

        # Testimonials (published, featured first)
        testimonials = Testimonial.objects.filter(
            is_published=True
        ).order_by('-is_featured', 'sort_order')[:10]

        # Footer
        footer_configs = FooterConfig.objects.filter(is_active=True).order_by('sort_order')
        footer = {}
        for fc in footer_configs:
            footer[fc.section] = fc

        ctx = _common_ctx(s, s_url)
        ctx.update({
            # Hero
            'hero_badge': s('HERO', 'hero_badge', 'AI-Powered Learning Platform'),
            'hero_title': s('HERO', 'hero_title', 'Empowering Students Through Premium Education'),
            'hero_subtitle': s('HERO', 'hero_subtitle'),
            'hero_cta_text': s('HERO', 'hero_cta_text', 'Get Started'),
            'hero_cta_url': s('HERO', 'hero_cta_url', '/login/'),
            'hero_image': s_url('HERO', 'hero_bg_image'),
            'map_embed_url': s('CONTACT', 'map_embed_url'),
            # Dynamic content
            'news_items': news,
            'testimonials': testimonials,
            'footer_configs': footer,
            # Ticker items (scrolling stats bar)
            'ticker_items': TickerItem.objects.filter(is_active=True).order_by('sort_order'),
        })
        return render(request, 'frontend/home.html', ctx)


class ProgramsView(View):
    def get(self, request):
        settings, s, s_url = _load_website_settings()
        return render(request, 'frontend/programs.html', _common_ctx(s, s_url))


class PartnersView(View):
    def get(self, request):
        settings, s, s_url = _load_website_settings()
        return render(request, 'frontend/partners.html', _common_ctx(s, s_url))


class ScholarshipsView(View):
    def get(self, request):
        from materials.models import Scholarship
        scholarships = Scholarship.objects.filter(is_active=True).order_by('title')
        # Group by a simple category: derive from title or use a fixed split
        engineering = []
        medical = []
        for s in scholarships:
            title_lower = s.title.lower()
            if 'medical' in title_lower or 'neet' in title_lower or 'aiims' in title_lower or 'jipmer' in title_lower or 'icmr' in title_lower or 'nmc' in title_lower or 'dhr' in title_lower:
                medical.append(s)
            else:
                engineering.append(s)
        total = scholarships.count()
        return render(request, 'frontend/scholarships.html', {
            'scholarships': scholarships,
            'engineering': engineering,
            'medical': medical,
            'eng_count': len(engineering),
            'med_count': len(medical),
            'total_count': total,
        })


class NewsView(View):
    def get(self, request):
        from system_config.models import WebsiteNews
        news_items = WebsiteNews.objects.filter(
            is_published=True
        ).order_by('-priority', '-publish_date')
        return render(request, 'frontend/news.html', {
            'news_items': news_items,
            'featured_item': news_items.first() if news_items.exists() else None,
            'other_items': news_items[1:] if news_items.count() > 1 else [],
        })


class AboutView(View):
    def get(self, request):
        settings, s, s_url = _load_website_settings()
        ctx = _common_ctx(s, s_url)
        ctx.update({
            'about_title': s('ABOUT', 'about_title', 'About ENABLE PROGRAM'),
            'about_description': s('ABOUT', 'about_description'),
            'mission_statement': s('ABOUT', 'mission_statement', 'To make quality education accessible and effective through innovative technology.'),
            'vision_statement': s('ABOUT', 'vision_statement', 'A future where every student has access to personalized, high-quality education.'),
        })
        return render(request, 'frontend/about.html', ctx)


class FounderView(View):
    def get(self, request):
        settings, s, s_url = _load_website_settings()
        return render(request, 'frontend/founder.html', _common_ctx(s, s_url))


class ManagementView(View):
    def get(self, request):
        settings, s, s_url = _load_website_settings()
        return render(request, 'frontend/management.html', _common_ctx(s, s_url))


class GalleryView(View):
    """Photo gallery page — pulls images from PhotoGallery model."""
    def get(self, request):
        from materials.models import PhotoGallery
        photos = PhotoGallery.objects.filter(is_active=True).order_by('category', 'sort_order')
        categories = photos.values_list('category', flat=True).distinct()
        return render(request, 'frontend/gallery.html', {
            'photos': photos,
            'categories': categories,
        })


class EnquiryView(View):
    """Handle contact form submissions"""
    def post(self, request):
        from django.http import HttpResponseRedirect
        # Store enquiry (optional: save to DB if enquiry_forms table exists)
        try:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO enquiry_forms (id, first_name, last_name, email, phone, subject, message, created_at)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW())""",
                [
                    request.POST.get('first_name', ''),
                    request.POST.get('last_name', ''),
                    request.POST.get('email', ''),
                    request.POST.get('phone', ''),
                    request.POST.get('subject', ''),
                    request.POST.get('message', ''),
                ]
            )
        except Exception:
            pass
        return HttpResponseRedirect('/#contact')


class LoginView(View):
    """Unified login page for all roles"""
    def get(self, request):
        role = request.GET.get('role', 'student')
        # Map 'staff' to 'admin' for compatibility
        if role == 'staff':
            role = 'admin'
        if role not in ('student', 'teacher', 'admin'):
            role = 'student'
        tenants = Tenant.objects.all().order_by('name')
        return render(request, 'accounts/login.html', {'role': role, 'tenants': tenants})

    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', 'STUDENT').upper()
        tenant_code = request.POST.get('tenant_code', '').strip()
        role = user_type.lower()
        tenants = Tenant.objects.all().order_by('name')

        # Validate inputs
        if not email or not password:
            return render(request, 'accounts/login.html', {
                'role': role,
                'error': 'Email and password are required.',
                'email': email,
                'tenant_code': tenant_code,
                'tenants': tenants,
            })

        # Find user
        model_map = {'STUDENT': Student, 'TEACHER': Teacher, 'ADMIN': Admin}
        Model = model_map.get(user_type)
        if not Model:
            return render(request, 'accounts/login.html', {
                'role': role,
                'error': 'Invalid user type.',
                'email': email,
                'tenant_code': tenant_code,
                'tenants': tenants,
            })

        try:
            # Identifier can be email OR phone number (User Id).
            # Resolution order: phone match -> email exact -> email prefix.
            user = None
            if email.isdigit() or (len(email) >= 10 and email.replace('+', '').replace('-', '').replace(' ', '').isdigit()):
                user = Model.objects.filter(phone=email).first()
            if not user:
                user = Model.objects.filter(email=email).first()
            if not user and '@' not in email:
                user = Model.objects.filter(email__istartswith=email + '@').first()

            if tenant_code:
                try:
                    tenant = Tenant.objects.get(code=tenant_code)
                    tenant_user = (
                        Model.objects.filter(phone=email, tenant=tenant).first()
                        or Model.objects.filter(email=email, tenant=tenant).first()
                    )
                    if tenant_user:
                        user = tenant_user
                except Tenant.DoesNotExist:
                    return render(request, 'accounts/login.html', {
                        'role': role,
                        'error': 'Invalid school/tenant code.',
                        'email': email,
                        'tenant_code': tenant_code,
                        'tenants': tenants,
                    })

            # Password check with lazy phone-as-password fallback for students
            # whose stored hash is not the canonical phone hash (legacy imports).
            password_ok = bool(user) and check_password(password, user.password_hash)
            if (
                not password_ok
                and user is not None
                and user_type == 'STUDENT'
                and getattr(user, 'phone', None)
                and password == user.phone
            ):
                user.set_password(user.phone)
                user.save(update_fields=['password_hash', 'password_changed_at'])
                password_ok = True

            if not password_ok:
                return render(request, 'accounts/login.html', {
                    'role': role,
                    'error': 'Invalid User Id or password.',
                    'email': email,
                    'tenant_code': tenant_code,
                    'tenants': tenants,
                })

            # Auto-associate tenant in session
            tenant_id = str(user.tenant_id) if user.tenant_id else None

            # Generate JWT token
            from datetime import datetime, timedelta
            import uuid
            now = datetime.utcnow()
            payload = {
                'user_id': str(user.id),
                'user_type': user_type,
                'tenant_id': tenant_id,
                'email': user.email,
                'token_type': 'access',
                'exp': now + timedelta(minutes=60),
                'iat': now,
                'jti': str(uuid.uuid4()),
            }
            access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # Store session data
            request.session['access_token'] = access_token
            request.session['user_id'] = str(user.id)
            request.session['user_type'] = user_type
            request.session['user_name'] = f"{user.first_name} {user.last_name}"
            request.session['user_email'] = user.email
            request.session['tenant_id'] = str(user.tenant_id) if user.tenant_id else None
            request.session['tenant_name'] = user.tenant.name if user.tenant_id else None

            # Redirect to appropriate dashboard
            dashboard_map = {
                'STUDENT': '/student/dashboard/',
                'TEACHER': '/teacher/dashboard/',
                'ADMIN': '/staff/dashboard/',
            }
            return redirect(dashboard_map.get(user_type, '/'))

        except Exception as e:
            return render(request, 'accounts/login.html', {
                'role': role,
                'error': f'Login error: {str(e)}',
                'email': email,
                'tenant_code': tenant_code,
                'tenants': tenants,
            })


class RegisterView(View):
    """Registration page"""
    def get(self, request):
        role = request.GET.get('role', 'student')
        # Map 'staff' to 'admin' for compatibility
        if role == 'staff':
            role = 'admin'
        if role not in ('student', 'teacher', 'admin'):
            role = 'student'
        return render(request, 'accounts/register.html', {'role': role})

    def post(self, request):
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        user_type = request.POST.get('user_type', 'STUDENT').upper()
        tenant_code = request.POST.get('tenant_code', '').strip()
        role = user_type.lower()

        # Validate
        if not all([first_name, last_name, email, phone, password]):
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': 'All fields are required.'
            })

        if password != password2:
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': 'Passwords do not match.'
            })

        if len(password) < 8:
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': 'Password must be at least 8 characters.'
            })

        # Find tenant
        tenant = None
        if tenant_code:
            try:
                tenant = Tenant.objects.get(code=tenant_code)
            except Tenant.DoesNotExist:
                return render(request, 'accounts/register.html', {
                    'role': role,
                    'error': 'Invalid school/tenant code.'
                })

        # Create user
        import uuid
        model_map = {'STUDENT': Student, 'TEACHER': Teacher, 'ADMIN': Admin}
        Model = model_map.get(user_type)
        if not Model:
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': 'Invalid user type.'
            })

        # Check duplicate
        if Model.objects.filter(email=email).exists():
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': 'An account with this email already exists.'
            })

        prefix_map = {'STUDENT': 'STU', 'TEACHER': 'TCH', 'ADMIN': 'ADM'}
        prefix = prefix_map.get(user_type, 'USR')
        code = f"{prefix}{uuid.uuid4().hex[:8].upper()}"

        try:
            user = Model.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                password_hash=make_password(password),
                code=code,
                tenant=tenant,
                status='ACTIVE',
            )
            # Redirect to login with success message
            return render(request, 'accounts/login.html', {
                'role': role,
                'success': f'Account created successfully! Your ID is {code}. Please login.',
                'email': email,
                'tenant_code': tenant_code,
                'tenants': Tenant.objects.all().order_by('name'),
            })
        except Exception as e:
            return render(request, 'accounts/register.html', {
                'role': role,
                'error': f'Registration error: {str(e)}'
            })


class LogoutView(View):
    """Logout and clear session"""
    def get(self, request):
        request.session.flush()
        return redirect('/login/')


def _get_session_user(request):
    """Get user info from session"""
    return {
        'user_name': request.session.get('user_name', 'User'),
        'user_type': request.session.get('user_type', ''),
        'user_id': request.session.get('user_id', ''),
        'user_email': request.session.get('user_email', ''),
        'user_initials': ''.join(w[0].upper() for w in request.session.get('user_name', 'U').split()[:2]),
        'access_token': request.session.get('access_token', ''),
    }


class StudentDashboardView(View):
    """Student Dashboard - React SPA"""
    def get(self, request, path=''):
        if request.session.get('user_type') != 'STUDENT':
            return redirect('/login/?role=student')
        # Server-side routes: intercept before the SPA renders hardcoded demo data
        norm = path.rstrip('/').lower()
        if norm in ('exams', 'exam', 'tests', 'my-tests'):
            return redirect('/student/exams/')
        if norm == 'schedule':
            return redirect('/student/schedule/')
        return render(request, 'dashboards/student_dashboard_react.html')


class TeacherDashboardView(View):
    """Teacher Dashboard - React SPA"""
    def get(self, request, path=''):
        if request.session.get('user_type') != 'TEACHER':
            return redirect('/login/?role=teacher')
        return render(request, 'dashboards/teacher_dashboard_react.html')


class AdminDashboardView(View):
    """Admin Dashboard – Comprehensive executive overview"""
    def get(self, request):
        if request.session.get('user_type') != 'ADMIN':
            return redirect('/login/?role=admin')
        ctx = _get_session_user(request)

        # ── Lazy imports (avoid circular) ──
        from academics.models import Batch, Users, BatchTeacher, Subject, AcademicSession
        from communication.models import SupportTicket, Announcement
        from sessions_tracking.models import UserSession, LoginHistory
        from materials.models import StudyMaterial
        try:
            from classes.models import ScheduledClass
            has_classes = True
        except Exception:
            has_classes = False
        try:
            from assessments.models import Test, TestAttempt
            has_assessments = True
        except Exception:
            has_assessments = False
        try:
            from attendance.models import Attendance, AttendanceSummary
            has_attendance = True
        except Exception:
            has_attendance = False

        now = timezone.now()
        today = now.date()

        # ═══════ KPI CARDS ═══════
        # Students
        total_students = Users.objects.count()
        active_students = Users.objects.filter(is_active=True).count()
        inactive_students = total_students - active_students

        # Teachers
        total_teachers = Teacher.objects.count()
        active_teachers = Teacher.objects.filter(status='ACTIVE').count()

        # Batches
        total_batches = Batch.objects.count()
        active_batches = Batch.objects.filter(status='ACTIVE').count()

        # Subjects
        total_subjects = Subject.objects.count()

        # Tenants/Centers
        total_tenants = Tenant.objects.count()

        # Tests
        total_tests = 0
        if has_assessments:
            total_tests = Test.objects.count()

        # Study Materials
        total_materials = StudyMaterial.objects.count()

        # Support Tickets
        open_tickets = SupportTicket.objects.filter(
            status__in=['OPEN', 'IN_PROGRESS', 'PENDING']
        ).count()
        total_tickets = SupportTicket.objects.count()

        # Audit Logs
        audit_count = AuditLog.objects.count()

        # ═══════ LIVE ACTIVITY ═══════
        fifteen_min_ago = now - timedelta(minutes=15)
        active_sessions = UserSession.objects.filter(
            status='ACTIVE',
            last_activity_at__gte=fifteen_min_ago
        ).count()

        # Currently live classes
        live_classes_list = []
        if has_classes:
            live_now = ScheduledClass.objects.filter(
                status='LIVE'
            ).select_related('teacher', 'batch')[:10]
            for lc in live_now:
                live_classes_list.append({
                    'title': lc.title,
                    'teacher': f"{lc.teacher.first_name} {lc.teacher.last_name}" if lc.teacher else 'N/A',
                    'batch': lc.batch.name if lc.batch else 'N/A',
                    'subject': str(lc.subject) if lc.subject else '',
                })
        live_class_count = len(live_classes_list)

        # Today's scheduled classes
        today_classes = []
        if has_classes:
            today_scheduled = ScheduledClass.objects.filter(
                scheduled_date=today
            ).select_related('teacher', 'batch').order_by('start_time')[:20]
            for sc in today_scheduled:
                today_classes.append({
                    'title': sc.title,
                    'teacher': f"{sc.teacher.first_name} {sc.teacher.last_name}" if sc.teacher else 'N/A',
                    'batch': sc.batch.name if sc.batch else 'N/A',
                    'start_time': sc.start_time.strftime('%I:%M %p') if sc.start_time else '',
                    'end_time': sc.end_time.strftime('%I:%M %p') if sc.end_time else '',
                    'status': sc.status,
                })

        # ═══════ TODAY'S STATS ═══════
        today_new_students = Users.objects.filter(enrolled_at__date=today).count()
        today_new_teachers = Teacher.objects.filter(created_at__date=today).count()
        today_logins = LoginHistory.objects.filter(
            attempted_at__date=today,
            result='SUCCESS'
        ).count()

        # ═══════ STUDENTS BY CENTER ═══════
        students_by_center = []
        tenants_qs = Tenant.objects.all().order_by('name')
        for t in tenants_qs:
            count = Users.objects.filter(tenant=t).count()
            active = Users.objects.filter(tenant=t, is_active=True).count()
            students_by_center.append({
                'center_name': t.name,
                'center_code': t.code,
                'total': count,
                'active': active,
                'inactive': count - active,
            })

        # ═══════ BATCH SUMMARY ═══════
        batch_summaries = []
        batches_qs = Batch.objects.filter(status='ACTIVE').order_by('name')[:15]
        for b in batches_qs:
            enrolled = Users.objects.filter(batch=b, is_active=True).count()
            teacher_count = BatchTeacher.objects.filter(batch=b).count()
            batch_summaries.append({
                'name': b.name,
                'code': b.code,
                'class_level': b.class_level or '',
                'enrolled': enrolled,
                'max_students': b.max_students or '-',
                'teacher_count': teacher_count,
            })

        # ═══════ RECENT AUDIT LOGS ═══════
        recent_audits = []
        audit_qs = AuditLog.objects.all().order_by('-created_at')[:8]
        for a in audit_qs:
            recent_audits.append({
                'user': a.username or a.user_type or 'System',
                'action': a.action,
                'description': (a.action_description or '')[:80],
                'resource': a.resource_type or '',
                'time': _time_ago(a.created_at, now),
                'severity': a.severity or 'INFO',
            })

        # ═══════ TEACHER SUMMARY ═══════
        teacher_summaries = []
        teachers_qs = Teacher.objects.filter(status='ACTIVE').order_by('first_name')[:20]
        for t in teachers_qs:
            batch_count = BatchTeacher.objects.filter(teacher=t).count()
            subjects = t.subjects if isinstance(t.subjects, list) else []
            teacher_summaries.append({
                'name': f"{t.first_name} {t.last_name}",
                'code': t.teacher_code or '',
                'subjects': ', '.join(subjects[:3]) if subjects else 'N/A',
                'batches': batch_count,
                'status': t.status,
            })

        # ═══════ TEST SUMMARY ═══════
        test_summaries = []
        if has_assessments:
            tests_qs = Test.objects.all().order_by('-created_at')[:10]
            for t in tests_qs:
                attempts = TestAttempt.objects.filter(test=t).count()
                test_summaries.append({
                    'title': t.title,
                    'code': t.test_code or '',
                    'type': t.test_type or '',
                    'subject': str(t.subject) if t.subject else 'N/A',
                    'attempts': attempts,
                    'status': t.status,
                })

        # ═══════ ANNOUNCEMENTS ═══════
        recent_announcements = []
        ann_qs = Announcement.objects.filter(is_published=True).order_by('-published_at')[:5]
        for a in ann_qs:
            recent_announcements.append({
                'title': a.title,
                'type': a.announcement_type or 'General',
                'date': a.published_at.strftime('%d %b %Y') if a.published_at else '',
                'views': a.view_count or 0,
            })

        # ═══════ CONTEXT ═══════
        ctx.update({
            'today_date': today.strftime('%A, %d %B %Y'),
            # KPIs
            'total_students': total_students,
            'active_students': active_students,
            'inactive_students': inactive_students,
            'total_teachers': total_teachers,
            'active_teachers': active_teachers,
            'total_batches': total_batches,
            'active_batches': active_batches,
            'total_subjects': total_subjects,
            'total_tenants': total_tenants,
            'total_tests': total_tests,
            'total_materials': total_materials,
            'open_tickets': open_tickets,
            'total_tickets': total_tickets,
            'audit_count': audit_count,
            # Live Activity
            'active_sessions': active_sessions,
            'live_class_count': live_class_count,
            'live_classes': live_classes_list,
            'today_classes': today_classes,
            # Today
            'today_new_students': today_new_students,
            'today_new_teachers': today_new_teachers,
            'today_logins': today_logins,
            # Breakdowns
            'students_by_center': students_by_center,
            'batch_summaries': batch_summaries,
            'teacher_summaries': teacher_summaries,
            'test_summaries': test_summaries,
            'recent_audits': recent_audits,
            'recent_announcements': recent_announcements,
        })
        return render(request, 'dashboards/admin_dashboard.html', ctx)


def _time_ago(dt, now=None):
    """Human-readable time-ago string"""
    if not dt:
        return ''
    if now is None:
        now = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = seconds // 60
        return f'{mins} min ago'
    elif seconds < 86400:
        hrs = seconds // 3600
        return f'{hrs} hr ago'
    else:
        days = seconds // 86400
        return f'{days} day{"s" if days > 1 else ""} ago'
