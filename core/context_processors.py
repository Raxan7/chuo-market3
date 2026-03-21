from django.contrib.auth.models import AnonymousUser

def auth_status(request):
    return {
        'is_authenticated': not isinstance(request.user, AnonymousUser)
    }

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
