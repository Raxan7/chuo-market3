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
