"""
Middleware for URL canonicalization to improve SEO.
This ensures that all URLs follow a consistent pattern.
"""
from django.http import HttpResponsePermanentRedirect
from django.conf import settings

class CanonicalDomainMiddleware:
    """Middleware to enforce a canonical domain name."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define the canonical domain from settings, or use the first allowed host
        self.canonical_domain = getattr(settings, 'CANONICAL_DOMAIN', settings.ALLOWED_HOSTS[0])
        self.enforce_ssl = getattr(settings, 'ENFORCE_SSL', not settings.DEBUG)
    
    def __call__(self, request):
        """
        If the request's host doesn't match the canonical domain,
        redirect to the same path on the canonical domain.
        """
        host = request.get_host().split(':')[0]
        
        # If we're not on the canonical domain, redirect
        if host != self.canonical_domain and self.canonical_domain != '*':
            scheme = 'https' if self.enforce_ssl else request.scheme
            new_url = f"{scheme}://{self.canonical_domain}{request.path}"
            if request.META.get('QUERY_STRING', ''):
                new_url = f"{new_url}?{request.META['QUERY_STRING']}"
            
            # Use permanent redirect (301) for better SEO
            return HttpResponsePermanentRedirect(new_url)
        
        # Remove trailing slashes for better SEO consistency (except for the homepage)
        if request.path != '/' and request.path.endswith('/'):
            new_url = request.path.rstrip('/')
            if request.META.get('QUERY_STRING', ''):
                new_url = f"{new_url}?{request.META['QUERY_STRING']}"
                
            return HttpResponsePermanentRedirect(new_url)
            
        return self.get_response(request)
