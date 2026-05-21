"""
Signal handlers for the core application
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Customer, Subscription, UserNewsletterPreference, Blog, Product
from .newsletter import send_blog_newsletter, send_product_newsletter

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


@receiver(post_save, sender=User)
def create_newsletter_preference(sender, instance, created, **kwargs):
    if created:
        UserNewsletterPreference.objects.get_or_create(user=instance)


@receiver(post_save, sender=Blog)
def notify_new_blog(sender, instance, created, **kwargs):
    if not created:
        return

    related_blogs = Blog.objects.exclude(pk=instance.pk)
    if instance.category:
        related_blogs = related_blogs.filter(Q(category=instance.category) | Q(author=instance.author))
    else:
        related_blogs = related_blogs.filter(author=instance.author)

    related_blogs = related_blogs.order_by('-created_at')[:3]
    send_blog_newsletter(instance, related_blogs)


@receiver(post_save, sender=Product)
def notify_new_product(sender, instance, created, **kwargs):
    if not created:
        return

    related_products = Product.objects.exclude(pk=instance.pk)
    related_products = related_products.filter(Q(category=instance.category) | Q(user=instance.user)).order_by('-created_at')[:3]
    send_product_newsletter(instance, related_products)
