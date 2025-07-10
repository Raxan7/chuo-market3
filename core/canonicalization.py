"""
URL Canonicalization Middleware for ensuring consistent URL formats.
This middleware redirects all non-canonical URLs to their canonical forms.
"""

from django.http import HttpResponsePermanentRedirect
from django.conf import settings
import re

class CanonicalDomainMiddleware:
    """
    Middleware to ensure that all requests are served from the canonical domain.
    Redirects from non-canonical domains (like www.example.com) to the canonical domain (example.com).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define canonical domain - preferably from settings
        self.canonical_domain = getattr(settings, 'CANONICAL_DOMAIN', 'chuosmart.com')
        
    def __call__(self, request):
        host = request.get_host().split(':')[0]
        
        # If not on the canonical domain and not in DEBUG mode
        if host != self.canonical_domain and not settings.DEBUG:
            # Build the new URL using the canonical domain
            scheme = 'https'  # We always want HTTPS for production
            new_url = f"{scheme}://{self.canonical_domain}{request.path}"
            
            if request.META.get('QUERY_STRING', ''):
                new_url += f"?{request.META['QUERY_STRING']}"
                
            return HttpResponsePermanentRedirect(new_url)
            
        return self.get_response(request)


class TrailingSlashMiddleware:
    """
    Middleware to ensure all URLs have a trailing slash.
    Django's default behavior is to have trailing slashes, so this enforces that.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip if this is a file or media URL
        path = request.path
        
        # Don't redirect paths that end with file extensions or paths that already have a trailing slash
        if re.search(r'\.\w+$', path) or path.endswith('/') or path == '':
            return self.get_response(request)
            
        # Don't redirect for certain URLs where trailing slashes are not desired
        if path == '/robots.txt' or path == '/sitemap.xml' or '/admin' in path:
            return self.get_response(request)
            
        # Add the trailing slash
        new_url = f"{path}/"
        
        # Add query string if it exists
        if request.META.get('QUERY_STRING', ''):
            new_url += f"?{request.META['QUERY_STRING']}"
            
        return HttpResponsePermanentRedirect(new_url)
