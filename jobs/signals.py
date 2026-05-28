"""Newsletter notifications for newly published job posts."""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.newsletter import send_job_newsletter
from .models import Job


@receiver(post_save, sender=Job)
def notify_new_job(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    def dispatch_newsletter():
        related_jobs = Job.public_queryset().exclude(pk=instance.pk).filter(
            job_type=instance.job_type
        ).order_by('-posted_date')[:3]
        send_job_newsletter(instance, related_jobs)

    transaction.on_commit(dispatch_newsletter)
