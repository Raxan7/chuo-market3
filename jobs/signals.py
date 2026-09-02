"""Keep public job announcements synchronized with visibility changes.

Announcement/marketing work is deliberately best-effort. A queue outage must never
turn a successful employer action (posting a job or verifying a company) into an
HTTP 500 response.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.newsletter import send_job_newsletter
from .models import Company, Job, UserJobApproval

logger = logging.getLogger(__name__)


def _queue_if_public(job):
    if not job.is_public:
        return
    related_jobs = Job.public_queryset().exclude(pk=job.pk).filter(
        job_type=job.job_type
    ).order_by('-posted_date')[:3]
    send_job_newsletter(job, related_jobs)


def _safe_queue_if_public(job):
    """Queue one public job without allowing email infrastructure to break posting."""
    try:
        _queue_if_public(job)
    except Exception:
        logger.exception(
            'Job %s was saved successfully but its announcement could not be queued.',
            getattr(job, 'pk', None),
        )


def _safe_dispatch_jobs(jobs, reason):
    """Best-effort batch dispatch used after verification/approval changes."""
    for job in jobs:
        try:
            _queue_if_public(job)
        except Exception:
            logger.exception(
                'Job %s announcement queue failed during %s; continuing with remaining jobs.',
                getattr(job, 'pk', None),
                reason,
            )


@receiver(post_save, sender=Job)
def notify_new_job(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: _safe_queue_if_public(instance))


@receiver(post_save, sender=Company)
def announce_jobs_after_company_verification(sender, instance, **kwargs):
    if not instance.is_verified:
        return

    def dispatch():
        _safe_dispatch_jobs(
            instance.jobs.filter(is_active=True).order_by('-posted_date'),
            'company verification',
        )

    transaction.on_commit(dispatch)


@receiver(post_save, sender=UserJobApproval)
def announce_jobs_after_user_approval(sender, instance, **kwargs):
    if not instance.is_approved:
        return

    def dispatch():
        _safe_dispatch_jobs(
            instance.user.posted_jobs.filter(is_active=True).order_by('-posted_date'),
            'user job approval',
        )

    transaction.on_commit(dispatch)
