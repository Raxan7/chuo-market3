from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.newsletter import send_material_newsletter
from .models import Material


@receiver(post_save, sender=Material)
def queue_material_marketing(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    def dispatch():
        related = Material.objects.filter(is_active=True).exclude(pk=instance.pk).order_by('-created_at')[:3]
        send_material_newsletter(instance, related)

    transaction.on_commit(dispatch)
