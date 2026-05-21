"""Signal handlers for talent uploads."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Talent
from core.newsletter import send_talent_newsletter


@receiver(post_save, sender=Talent)
def notify_new_talent(sender, instance, created, **kwargs):
    if not created:
        return

    def dispatch_newsletter():
        related_talents = Talent.objects.exclude(pk=instance.pk).filter(category=instance.category).order_by('-created_at')[:3]
        send_talent_newsletter(instance, related_talents)

    transaction.on_commit(dispatch_newsletter)