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
            'https://www.google.com',
            'https://pagead2.googlesyndication.com',
            'https://googleads.g.doubleclick.net',
            'https://www.googleadservices.com',
            'https://ep1.adtrafficquality.google',
            'https://ep2.adtrafficquality.google',
            'https://static.cloudflareinsights.com',
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            'https://js.stripe.com',
            'https://fundingchoicesmessages.google.com',
            'https://ad.doubleclick.net',
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
        'worker-src': [
            "'self'",
            'blob:',
        ],
        'connect-src': [
            "'self'",
            'https://www.google-analytics.com',
            'https://www.google.com',
            'https://pagead2.googlesyndication.com',
            'https://googleads.g.doubleclick.net',
            'https://www.googleadservices.com',
            'https://ep1.adtrafficquality.google',
            'https://ep2.adtrafficquality.google',
            'https://static.cloudflareinsights.com',
            'https://cdn.jsdelivr.net',
            'https://*.stripe.com',
            'https://res.cloudinary.com',
            'https://ad.doubleclick.net',
            'https://fundingchoicesmessages.google.com',
            'wss:',
            'https://*.acscdn.com',
            'https://adexchangerapid.com',
            'https://usrpubtrk.com',
        ],
        'frame-src': [
            "'self'",
            'https://www.youtube.com',
            'https://www.youtube-nocookie.com',
            'https://js.stripe.com',
            'https://hooks.stripe.com',
            'https://googleads.g.doubleclick.net',
            'https://www.googleadservices.com',
            'https://ep2.adtrafficquality.google',
            'https://www.google.com',
            'https://acscdn.com',
            'https://*.acscdn.com',
        ],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        # Forms submit only to ChuoSmart. External payment checkout navigation
        # happens from a normal 200 transition page, not from the form POST's
        # redirect chain, so third-party origins do not belong in form-action.
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
    }

    def _build_csp(self):
        parts = []
        for directive, sources in self.CSP_DIRECTIVES.items():
            if isinstance(sources, str):
                sources = [sources]
            else:
                # Never mutate the class-level directive lists while building a
                # response-specific policy.
                sources = list(sources)

            if directive == 'form-action':
                # Payment forms normally submit to the current origin. In
                # production, however, an allowed alias such as
                # ``www.chuosmart.com`` can render a form whose canonical target
                # is ``https://chuosmart.com``. CSP considers those different
                # origins, so ``'self'`` alone blocks the payment POST before it
                # reaches Django. Permit only the configured canonical HTTPS
                # origin in addition to self.
                canonical_domain = str(
                    getattr(settings, 'CANONICAL_DOMAIN', '') or ''
                ).strip().rstrip('/')
                if canonical_domain and canonical_domain != '*':
                    if '://' in canonical_domain:
                        canonical_origin = canonical_domain
                    else:
                        canonical_origin = f'https://{canonical_domain}'
                    if canonical_origin not in sources:
                        sources.append(canonical_origin)

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
            response['Content-Security-Policy'] = self._build_csp()
        return response


class SessionIdleTimeoutMiddleware:
    """Enforce a sliding authenticated-session idle timeout."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = time.time()
            last_activity = request.session.get('last_activity')
            idle_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 60 * 60 * 24 * 7)

            if last_activity and current_time - float(last_activity) > idle_timeout:
                logout(request)
                request.session.flush()
            else:
                request.session['last_activity'] = current_time
                request.session['user_active'] = True
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        return self.get_response(request)

# CHUOSMART_ADCASH_CSP_MIDDLEWARE_V1
class AdcashCSPMiddleware:
    """
    Extend the site's Content-Security-Policy with the sources required
    by the configured Adcash AutoTag and banner zones.
    """

    DIRECTIVE_SOURCES = {
        "script-src": (
            "https://acscdn.com",
            "https://*.acscdn.com",
            "https://ad.votravis.me",
        ),
        "connect-src": (
            "https://acscdn.com",
            "https://*.acscdn.com",
            "https://adexchangerapid.com",
            "https://usrpubtrk.com",
            "https://my.rtmark.net",
            "https://jhnwr.com",
            "https://ldrws.com",
        ),
        "worker-src": (
            "'self'",
            "blob:",
        ),
        "frame-src": (
            "https://acscdn.com",
            "https://*.acscdn.com",
        ),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _extend_policy(policy, additions):
        directives = []
        indexes = {}

        for raw_directive in policy.split(";"):
            raw_directive = raw_directive.strip()

            if not raw_directive:
                continue

            parts = raw_directive.split()
            name = parts[0]
            sources = parts[1:]

            indexes[name] = len(directives)
            directives.append([name, sources])

        for name, required_sources in additions.items():
            if name in indexes:
                sources = directives[indexes[name]][1]
            else:
                indexes[name] = len(directives)
                sources = []
                directives.append([name, sources])

            for source in required_sources:
                if source not in sources:
                    sources.append(source)

        return "; ".join(
            " ".join([name] + sources)
            for name, sources in directives
        ) + ";"

    def __call__(self, request):
        response = self.get_response(request)

        policy = response.get(
            "Content-Security-Policy",
            "default-src 'self';",
        )

        response["Content-Security-Policy"] = self._extend_policy(
            policy,
            self.DIRECTIVE_SOURCES,
        )

        return response
