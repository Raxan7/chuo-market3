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
            'https://www.highrevenueformat.com',
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
            'https://www.highrevenueformat.com',
            'wss:',
            'https://*.highrevenueformat.com',
            'https://*.profitableratecpmnetwork.com',
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
            'https://www.profitableratecpmnetwork.com',
            'https://www.highrevenueformat.com',
            'https://*.highrevenueformat.com',
            'https://*.profitableratecpmnetwork.com',
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

# CHUOSMART_MONETAG_CSP_MIDDLEWARE_V1
class MonetagCSPMiddleware:
    """
    Extend ChuoSmart's existing Content-Security-Policy with only
    the origins required by the configured Monetag zones.

    Primary JS:
      - nap5k.com
      - n6wxm.com

    Provider network/config requests:
      - my.rtmark.net
      - jhnwr.com
      - ldrws.com
    """

    SCRIPT_ORIGINS = (
        "https://nap5k.com",
        "https://n6wxm.com",
    )

    CONNECT_ORIGINS = (
        "https://nap5k.com",
        "https://n6wxm.com",
        "https://my.rtmark.net",
        "https://jhnwr.com",
        "https://ldrws.com",
    )

    FRAME_ORIGINS = (
        "https://nap5k.com",
        "https://n6wxm.com",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _parse_policy(policy):
        parts = [
            part.strip()
            for part in policy.split(";")
            if part.strip()
        ]

        return parts

    @staticmethod
    def _extend_directive(parts, directive, origins, create=True):
        index = None

        for i, part in enumerate(parts):
            tokens = part.split()

            if tokens and tokens[0].lower() == directive:
                index = i
                break

        if index is None:
            if create:
                parts.append(
                    "{} 'self' {}".format(
                        directive,
                        " ".join(origins),
                    )
                )

            return parts

        tokens = parts[index].split()

        for origin in origins:
            if origin not in tokens:
                tokens.append(origin)

        parts[index] = " ".join(tokens)

        return parts

    @classmethod
    def _extend_policy(cls, policy):
        if not policy:
            return policy

        parts = cls._parse_policy(policy)

        parts = cls._extend_directive(
            parts,
            "script-src",
            cls.SCRIPT_ORIGINS,
        )

        # If script-src-elem already exists it needs the same
        # primary script hosts. Otherwise the browser correctly
        # falls back to script-src.
        parts = cls._extend_directive(
            parts,
            "script-src-elem",
            cls.SCRIPT_ORIGINS,
            create=False,
        )

        parts = cls._extend_directive(
            parts,
            "connect-src",
            cls.CONNECT_ORIGINS,
        )

        parts = cls._extend_directive(
            parts,
            "frame-src",
            cls.FRAME_ORIGINS,
        )

        return "; ".join(parts) + ";"

    def __call__(self, request):
        response = self.get_response(request)

        policy = response.get(
            "Content-Security-Policy"
        )

        if policy:
            response[
                "Content-Security-Policy"
            ] = self._extend_policy(policy)

        return response
