# affiliates/middleware.py
import re
from django.conf import settings
from django.utils import timezone
from .models import Affiliate, ClickTracking

class ReferralMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Regular expression to match /ref/<username>/<product_id> pattern
        self.ref_pattern = re.compile(r'^/ref/([^/]+)(?:/([^/]+))?/?$')

    def __call__(self, request):
        # Check for direct referral links in the pattern /ref/<username>/<product_id>
        path_match = self.ref_pattern.match(request.path)
        affiliate_code = request.GET.get('ref')  # Also check for ?ref=CODE from URL
        
        if path_match:
            affiliate_username = path_match.group(1)
            product_id = path_match.group(2)  # This could be None
            
            try:
                affiliate = Affiliate.objects.get(user__username=affiliate_username)
                self._set_affiliate_cookie(request, affiliate.affiliate_code)
                
                # Record click tracking data
                tracking_data = {
                    'affiliate': affiliate,
                    'referral_link': request.build_absolute_uri(),
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')
                }
                
                # Add user to tracking if authenticated
                if request.user.is_authenticated:
                    tracking_data['user'] = request.user
                    
                ClickTracking.objects.create(**tracking_data)
                
                # Redirect to the product or course page if product_id is provided
                if product_id:
                    # This is a simplified redirect - you'd need to determine if this is a course, product, or service
                    return self._get_product_redirect(product_id)
                
            except Affiliate.DoesNotExist:
                pass  # Invalid username, proceed with normal response
        
        # Check for the ref query parameter
        elif affiliate_code:
            try:
                affiliate = Affiliate.objects.get(affiliate_code=affiliate_code)
                self._set_affiliate_cookie(request, affiliate_code)
                
                # Record click tracking
                tracking_data = {
                    'affiliate': affiliate,
                    'referral_link': request.build_absolute_uri(),
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')
                }
                
                # Add user to tracking if authenticated
                if request.user.is_authenticated:
                    tracking_data['user'] = request.user
                    
                ClickTracking.objects.create(**tracking_data)
                
            except Affiliate.DoesNotExist:
                pass
        
        response = self.get_response(request)
        return response
    
    def _set_affiliate_cookie(self, request, affiliate_code):
        """Set affiliate cookie in the session and HTTP cookie"""
        request.session['affiliate_code'] = affiliate_code
        request.session['affiliate_timestamp'] = timezone.now().isoformat()
        
        # Mark the session as modified to ensure it's saved
        request.session.modified = True
    
    def _get_client_ip(self, request):
        """Extract the client IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_product_redirect(self, product_id):
        """
        Determine the appropriate redirect based on the product ID.
        This is a simplified version - you'll need to implement the logic to check
        if this is a course, product, or service ID and return the appropriate redirect.
        """
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # You would implement logic here to check if this is a course, product, or service
        # For now, we'll assume it's a course
        try:
            # Try to parse as integer first for database lookups
            product_id = int(product_id)
        except ValueError:
            # If not an integer, it might be a slug
            pass
        
        # This is a placeholder - replace with your actual URL resolution
        try:
            from lms.models import Course
            course = Course.objects.filter(id=product_id).first()
            if course:
                return HttpResponseRedirect(reverse('lms:course_detail', kwargs={'slug': course.slug}))
        except:
            pass
            
        try:
            from core.models import Product
            product = Product.objects.filter(id=product_id).first()
            if product:
                return HttpResponseRedirect(reverse('core:product_detail', kwargs={'pk': product.id}))
        except:
            pass
        
        # Default: redirect to homepage if product not found
        return HttpResponseRedirect('/')