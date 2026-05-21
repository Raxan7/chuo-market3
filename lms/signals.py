"""
Signal handlers for the LMS application
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Q
from .models import LMSProfile, Course
from core.newsletter import send_course_newsletter


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


@receiver(post_save, sender=Course)
def notify_new_course(sender, instance, created, **kwargs):
    if not created:
        return

    related_courses = Course.objects.exclude(pk=instance.pk)
    if instance.program:
        related_courses = related_courses.filter(Q(program=instance.program) | Q(level=instance.level) | Q(course_type=instance.course_type))
    else:
        related_courses = related_courses.filter(Q(level=instance.level) | Q(course_type=instance.course_type))

    related_courses = related_courses.order_by('-id')[:3]
    send_course_newsletter(instance, related_courses)
