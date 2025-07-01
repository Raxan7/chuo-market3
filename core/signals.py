"""
Signal handlers for the core application
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Customer, Subscription

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    """
    Create a Customer profile when a new user registers
    """
    if created:
        # Try to get the default "Free" subscription
        try:
            default_subscription = Subscription.objects.get(level='Free')
        except Subscription.DoesNotExist:
            default_subscription = None
        
        # Create the customer with default values
        Customer.objects.create(
            user=instance,
            name=instance.username,
            university='University of Dar es Salaam',  # Default value
            college='College of Information and Communication Technologies',  # Default value
            room_number='Not specified',
            subscription=default_subscription
        )
