import time
from datetime import datetime
from django.conf import settings
from django.contrib.auth import logout


class SessionIdleTimeoutMiddleware:
    """
    Middleware to track user session activity.
    Sessions are now configured to persist indefinitely until explicit logout.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = time.time()
            
            # Update last activity timestamp for authenticated users
            request.session['last_activity'] = current_time
            
            # Set a flag to indicate the user is active (for UI purposes)
            request.session['user_active'] = True
            
            # Extend session expiry on each request
            # This ensures the session never expires during active use
            if 'sessionid' in request.COOKIES:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        
        response = self.get_response(request)
        return response
