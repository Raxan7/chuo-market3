# affiliates/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from lms.models import Course
from core.models import Product
import uuid

class AffiliateStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PENDING = 'pending', 'Pending Approval'
    REJECTED = 'rejected', 'Rejected'
    SUSPENDED = 'suspended', 'Suspended'

class Affiliate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')
    affiliate_code = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=AffiliateStatus.choices, default=AffiliateStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        if not self.affiliate_code:
            # Generate a unique affiliate code if not provided
            self.affiliate_code = f"{self.user.username[:5]}-{get_random_string(5).lower()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - {self.affiliate_code}"
    
    @property
    def get_referral_link(self):
        from django.urls import reverse
        return reverse('affiliates:referral_link', kwargs={'code': self.affiliate_code})
    
    @property
    def pending_balance(self):
        return self.referrals.filter(is_paid=False).aggregate(models.Sum('commission_earned'))['commission_earned__sum'] or 0

class ReferralType(models.TextChoices):
    COURSE = 'course', 'Course'
    PRODUCT = 'product', 'Product'
    SERVICE = 'service', 'Service'
    GENERAL = 'general', 'General Referral'

class Referral(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, related_name='referrals')
    referred_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_received')
    
    # Generic foreign key for referencing different content types
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    referral_type = models.CharField(max_length=20, choices=ReferralType.choices, default=ReferralType.GENERAL)
    referral_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Referral by {self.affiliate.user.username} for {self.referred_user.username}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new referral
            # Calculate commission based on the purchase amount
            commission_rate = getattr(settings, 'AFFILIATE_COMMISSION_RATE', 0.10)
            self.commission_earned = self.purchase_amount * commission_rate
            
            # Update affiliate's total earnings
            self.affiliate.total_earnings += self.commission_earned
            self.affiliate.balance += self.commission_earned
            self.affiliate.save()
            
        super().save(*args, **kwargs)

class ClickTracking(models.Model):
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, related_name='clicks')
    referral_link = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referral_clicks')
    
    def __str__(self):
        return f"Click by {self.affiliate.user.username} at {self.timestamp}"

class PayoutRequest(models.Model):
    class PayoutStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PAID = 'paid', 'Paid'
    
    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE, related_name='payout_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50)
    payment_details = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Payout request by {self.affiliate.user.username} - {self.amount}"