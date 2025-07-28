# affiliates/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .models import Affiliate, Referral, ReferralType

# Import your order/purchase models
from lms.models import CourseEnrollment
from core.models import OrderPlaced  # Using OrderPlaced which is the actual order model

@receiver(post_save, sender=CourseEnrollment)
def track_course_referral(sender, instance, created, **kwargs):
    """Track referrals for course enrollments"""
    if not created or not instance.paid:
        return
    
    user = instance.user
    course = instance.course
    
    # Instead of relying on the request object (which won't be available in signals),
    # we need to check if there's a cookie or other method of tracking the referral
    
    # Try to find a referral from any active user session
    affiliate_code = None
    from .middleware import ReferralMiddleware
    cookie_name = getattr(settings, 'AFFILIATE_COOKIE_NAME', 'ref')
    
    # Use the direct database lookup instead, checking if there's a record in your referral tracking model
    from .models import ClickTracking
    try:
        # Look for click tracking records for this user that aren't converted yet
        click = ClickTracking.objects.filter(
            user=user,
            converted=False
        ).order_by('-timestamp').first()
        
        if click:
            affiliate_code = click.affiliate.affiliate_code
            # Mark as converted
            click.converted = True
            click.save()
    except Exception:
        pass
    
    if not affiliate_code:
        return
    
    try:
        affiliate = Affiliate.objects.get(affiliate_code=affiliate_code)
        
        # Don't allow self-referrals
        if affiliate.user == user:
            return
        
        # Create referral record
        content_type = ContentType.objects.get_for_model(course)
        
        Referral.objects.create(
            affiliate=affiliate,
            referred_user=user,
            content_type=content_type,
            object_id=course.id,
            referral_type=ReferralType.COURSE,
            converted_at=timezone.now(),
            purchase_amount=course.price or 0
        )
        
    except Affiliate.DoesNotExist:
        pass

@receiver(post_save, sender=OrderPlaced)  # Using OrderPlaced model
def track_product_referral(sender, instance, created, **kwargs):
    """Track referrals for product purchases"""
    if not created or instance.status != 'Delivered':  # Only track delivered orders
        return
    
    user = instance.user
    
    # Instead of relying on the request object (which won't be available in signals),
    # we need to check if there's a cookie or other method of tracking the referral
    from django.contrib.sessions.models import Session
    from django.contrib.sessions.backends.db import SessionStore
    
    # Try to find a referral from any active user session
    affiliate_code = None
    from .middleware import ReferralMiddleware
    cookie_name = getattr(settings, 'AFFILIATE_COOKIE_NAME', 'ref')
    
    # Use the direct database lookup instead, checking if there's a record in your referral tracking model
    from .models import ClickTracking
    try:
        # Look for click tracking records for this user that aren't converted yet
        click = ClickTracking.objects.filter(
            user=user,
            converted=False
        ).order_by('-timestamp').first()
        
        if click:
            affiliate_code = click.affiliate.affiliate_code
            # Mark as converted
            click.converted = True
            click.save()
    except Exception:
        pass
    
    if not affiliate_code:
        return
    
    try:
        affiliate = Affiliate.objects.get(affiliate_code=affiliate_code)
        
        # Don't allow self-referrals
        if affiliate.user == user:
            return
        
        # OrderPlaced represents a single product order
        product = instance.product
        
        # Create referral record
        content_type = ContentType.objects.get_for_model(product)
        
        Referral.objects.create(
            affiliate=affiliate,
            referred_user=user,
            content_type=content_type,
            object_id=product.id,
            referral_type=ReferralType.PRODUCT,
            converted_at=timezone.now(),
            purchase_amount=float(instance.price if instance.price else 0) * instance.quantity
            )
        
    except Affiliate.DoesNotExist:
        pass