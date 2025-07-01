"""
Signal handlers for the LMS application
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import LMSProfile


@receiver(post_save, sender=User)
def create_lms_profile(sender, instance, created, **kwargs):
    """
    Create an LMS profile for a user
    """
    # Check if the user already has a profile
    if not hasattr(instance, 'lms_profile'):
        # For new users, set role to student by default
        # For existing users (admin users likely existed before LMS app), try to detect role
        role = 'student'
        if instance.is_staff and instance.is_superuser:
            role = 'admin'
        elif instance.is_staff:
            role = 'instructor'
        
        # Get phone number from Customer profile if available
        phone_number = None
        if hasattr(instance, 'customer') and instance.customer:
            phone_number = instance.customer.phone_number
            
        LMSProfile.objects.create(
            user=instance, 
            role=role,
            phone_number=phone_number
        )
