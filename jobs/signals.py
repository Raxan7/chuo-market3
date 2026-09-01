"""Keep public job announcements synchronized with visibility changes."""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.newsletter import send_job_newsletter
from .models import Company, Job, UserJobApproval


def _queue_if_public(job):
    if not job.is_public:
        return
    related_jobs = Job.public_queryset().exclude(pk=job.pk).filter(
        job_type=job.job_type
    ).order_by('-posted_date')[:3]
    send_job_newsletter(job, related_jobs)


@receiver(post_save, sender=Job)
def notify_new_job(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: _queue_if_public(instance))


@receiver(post_save, sender=Company)
def announce_jobs_after_company_verification(sender, instance, **kwargs):
    if not instance.is_verified:
        return

    def dispatch():
        for job in instance.jobs.filter(is_active=True).order_by('-posted_date'):
            _queue_if_public(job)

    transaction.on_commit(dispatch)


@receiver(post_save, sender=UserJobApproval)
def announce_jobs_after_user_approval(sender, instance, **kwargs):
    if not instance.is_approved:
        return

    def dispatch():
        for job in instance.user.posted_jobs.filter(is_active=True).order_by('-posted_date'):
            _queue_if_public(job)

    transaction.on_commit(dispatch)
