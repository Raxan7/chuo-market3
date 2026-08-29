"""Small cache-backed rate limiting helpers for sensitive POST endpoints.

This intentionally has no third-party dependency. In production configure a shared
Django cache (Redis/Memcached) if you run more than one application server.
"""
from functools import wraps
import hashlib

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _key(prefix, request, identity_field=None):
    identity = ''
    if identity_field:
        identity = str(request.POST.get(identity_field, '')).strip().lower()
    principal = f"{_client_ip(request)}|{identity}"
    digest = hashlib.sha256(principal.encode('utf-8')).hexdigest()
    return f"ratelimit:{prefix}:{digest}"


def rate_limit(prefix, limit=5, window=300, identity_field=None, methods=('POST',)):
    """Reject requests that exceed ``limit`` inside ``window`` seconds.

    ``identity_field`` can be set to a submitted username/email so an attacker
    rotating targets from one IP does not share a single global counter.
    """
    methods = {m.upper() for m in methods}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method.upper() not in methods:
                return view_func(request, *args, **kwargs)

            key = _key(prefix, request, identity_field=identity_field)
            try:
                if cache.add(key, 1, timeout=window):
                    count = 1
                else:
                    try:
                        count = cache.incr(key)
                    except (ValueError, NotImplementedError):
                        count = int(cache.get(key, 0)) + 1
                        cache.set(key, count, timeout=window)
            except Exception:
                # A cache outage must not take authentication/payment pages down.
                return view_func(request, *args, **kwargs)

            if count > limit:
                retry_after = str(window)
                if request.headers.get('Accept', '').startswith('application/json'):
                    response = JsonResponse(
                        {'status': 'error', 'message': 'Too many attempts. Please try again later.'},
                        status=429,
                    )
                else:
                    response = HttpResponse('Too many attempts. Please try again later.', status=429)
                response['Retry-After'] = retry_after
                return response

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
