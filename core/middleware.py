import time
from datetime import datetime
from django.conf import settings
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add Content-Security-Policy, Referrer-Policy, Permissions-Policy, and
    Cross-Origin-Opener-Policy headers to every response. The CSP allows the
    third-party assets the site legitimately loads (CDN scripts, Cloudinary
    uploads, YouTube embeds, Google Analytics/Ads, Stripe) and falls back to
    'self' for everything else.
    """

    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdn.tiny.cloud',
            'https://upload-widget.cloudinary.com',
            'https://www.googletagmanager.com',
            'https://www.google-analytics.com',
            'https://pagead2.googlesyndication.com',
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            'https://js.stripe.com',
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            'https://fonts.googleapis.com',
        ],
        'img-src': [
            "'self'",
            'data:',
            'blob:',
            'https:',
            'http://localhost',
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com',
            'https://cdnjs.cloudflare.com',
            'data:',
        ],
        'media-src': ["'self'", 'https:'],
        'connect-src': [
            "'self'",
            'https://www.google-analytics.com',
            'https://*.stripe.com',
            'https://res.cloudinary.com',
            'wss:',
        ],
        'frame-src': [
            "'self'",
            'https://www.youtube.com',
            'https://www.youtube-nocookie.com',
            'https://js.stripe.com',
            'https://hooks.stripe.com',
        ],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
    }

    def _build_csp(self):
        parts = []
        for directive, sources in self.CSP_DIRECTIVES.items():
            if isinstance(sources, str):
                sources = [sources]
            parts.append(f"{directive} {' '.join(sources)}")
        return '; '.join(parts)

    def process_response(self, request, response):
        # Permissions-Policy: disable powerful features by default
        response.setdefault(
            'Permissions-Policy',
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()',
        )
        # Referrer-Policy
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # Cross-origin isolation hints
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        # CSP only when not in DEBUG
        if not settings.DEBUG:
            response.setdefault('Content-Security-Policy', self._build_csp())
        return response


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
