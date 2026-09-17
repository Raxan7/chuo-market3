from datetime import date, datetime, timedelta

from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


def auth_status(request):
    return {
        'is_authenticated': not isinstance(request.user, AnonymousUser)
    }


def creator_access(request):
    """Expose creator permissions to the global UI shell.

    The redesigned navigation must not make users hunt for actions they are
    already allowed to perform. Keep these flags aligned with the underlying
    publishing rules:

    * Any signed-in user can submit a job; job/company approval controls public
      visibility after submission, matching the existing job creation view.
    * Courses can be created by LMS instructors/admins. An approved instructor
      request is also accepted because the course view promotes that profile on
      first access via ``is_instructor``.

    The imports are intentionally local so this context processor remains safe
    during Django app loading and management commands.
    """
    user = getattr(request, 'user', None)
    defaults = {
        'can_post_jobs': False,
        'can_create_courses': False,
        'can_use_instructor_dashboard': False,
        'has_creator_tools': False,
    }
    if not user or not user.is_authenticated:
        return defaults

    # ``jobs:create_job`` is protected by login only. Approval determines whether
    # a submitted job is public, not whether the user may submit it.
    can_post_jobs = True

    profile = None
    try:
        profile = user.lms_profile
    except (AttributeError, ObjectDoesNotExist):
        pass

    can_use_instructor_dashboard = bool(profile and profile.role == 'instructor')
    can_create_courses = bool(profile and profile.role in {'instructor', 'admin'})

    # Be resilient to legacy/stale data where an instructor request was
    # approved but the LMS profile role was not updated yet.
    if profile and not can_use_instructor_dashboard:
        try:
            from lms.models import InstructorRequest

            approved_instructor_request = InstructorRequest.objects.filter(
                user=user,
                status='approved',
            ).exists()
            can_use_instructor_dashboard = approved_instructor_request
            can_create_courses = can_create_courses or approved_instructor_request
        except Exception:
            # Navigation should never make the whole site fail if an optional
            # creator lookup is temporarily unavailable.
            pass

    return {
        'can_post_jobs': can_post_jobs,
        'can_create_courses': can_create_courses,
        'can_use_instructor_dashboard': can_use_instructor_dashboard,
        'has_creator_tools': can_post_jobs or can_create_courses,
    }


def certificate_notice(request):
    release = getattr(django_settings, 'CERTIFICATE_RELEASE_DATE', None)
    active = release is not None and date.today() < release
    return {'certificate_notice_active': active}


def certificate_available_announcement(request):
    """Show a one-time 'downloads now available' banner for 48 hours."""
    start = getattr(django_settings, 'CERTIFICATE_ANNOUNCEMENT_START', None)
    if start is not None and django_settings.USE_TZ:
        from django.utils.timezone import is_naive, make_aware
        if is_naive(start):
            start = make_aware(start)
    now = timezone.now() if django_settings.USE_TZ else datetime.now()
    show = (
        start is not None
        and start <= now
        and now - start < timedelta(hours=48)
    )
    return {'certificate_available_announcement': show}


def dashboard_notification(request):
    """
    A context processor that adds dashboard notification flag to the template context
    """
    show_dashboard_modal = False
    
    # Only show modal for authenticated users
    if request.user.is_authenticated:
        # Check the session flag
        show_dashboard_modal = request.session.pop('show_dashboard_modal', False)
    
    return {'show_dashboard_modal': show_dashboard_modal}


def site_ad_settings(request):
    """Expose ad toggles and suppress ads on trust-sensitive/high-intent pages."""
    path = request.path.lower()
    business_surface = path.startswith('/for-business/')
    premium_surface = path == '/' or business_surface
    sensitive_prefixes = (
        '/login/', '/registration/', '/checkout/', '/cart/', '/profile/',
        '/changepassword/', '/account-deletion-request/', '/lms/certificates/',
        '/lms/quizzes/', '/lms/quiz', '/for-business/',
    )
    sensitive_fragments = ('/payment/', '/access/pay/', '/access/success/', '/access/status/')
    # The company front door and enterprise surfaces are intentionally ad-free.
    # Ads remain available on appropriate marketplace/content pages.
    ads_allowed = not (
        path == '/' or path.startswith(sensitive_prefixes) or any(fragment in path for fragment in sensitive_fragments)
    )
    show_list_ads = ads_allowed
    try:
        from lms.models import SiteSettings
        settings_obj = SiteSettings.get_settings()
        show_list_ads = settings_obj.show_list_ads
    except Exception:
        show_list_ads = True

    return {
        'show_list_ads': show_list_ads and ads_allowed,
        'ads_allowed': ads_allowed,
        'business_surface': business_surface,
        'premium_surface': premium_surface,
    }
