import time
from datetime import datetime
from django.conf import settings
from django.contrib.auth import logout


class SessionIdleTimeoutMiddleware:
    """
    Middleware to timeout a session after a specified time of inactivity.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = time.time()
            last_activity = request.session.get('last_activity', None)
            
            # Check if session should be expired due to inactivity
            if last_activity and (current_time - last_activity) > settings.SESSION_IDLE_TIMEOUT:
                # If the session has been idle too long, log the user out
                logout(request)
                # After logout, the user will be redirected to the login page
                # You could add a message here if desired
            
            # Update last activity timestamp for authenticated users
            request.session['last_activity'] = current_time
            
            # Set a flag to indicate the user is active (for UI purposes)
            request.session['user_active'] = True
        
        response = self.get_response(request)
        return response
