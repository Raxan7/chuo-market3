from datetime import date, datetime, timedelta

from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone


def auth_status(request):
    return {
        'is_authenticated': not isinstance(request.user, AnonymousUser)
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
    """Expose site-wide ad toggles for templates with a safe default."""
    show_list_ads = True
    try:
        from lms.models import SiteSettings
        settings_obj = SiteSettings.get_settings()
        show_list_ads = settings_obj.show_list_ads
    except Exception:
        show_list_ads = True

    return {'show_list_ads': show_list_ads}
