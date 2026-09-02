import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone

from core.content_marketing import (
    active_auto_content_campaign_exists,
    due_content_job,
    materialize_job_as_campaign,
    rebalance_content_schedule,
    sync_content_jobs,
)
from core.models import NewsletterJob

logger = logging.getLogger('core.email')


class Command(BaseCommand):
    help = (
        'Reconcile published ChuoSmart content and convert due content jobs into '
        'throttled marketing campaigns. Recipient SMTP delivery is handled by '
        'process_marketing_queue.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=1,
            help='Maximum due content campaigns to materialize in this run. Serial safety normally limits this to one.',
        )
        parser.add_argument(
            '--reconcile-limit', type=int,
            default=getattr(settings, 'CONTENT_MARKETING_RECONCILE_LIMIT', 250),
            help='Newest database content rows to reconcile each routine run.',
        )
        parser.add_argument(
            '--backfill-all', action='store_true',
            help='One-time option: reconcile every eligible historical content row from newest to oldest.',
        )
        parser.add_argument('--retry-delay-minutes', type=int, default=10)

    def handle(self, *args, **options):
        limit = max(1, min(int(options['limit']), 10))
        retry_delay = max(1, int(options['retry_delay_minutes']))
        reconcile_limit = None if options['backfill_all'] else max(1, int(options['reconcile_limit']))

        sync = sync_content_jobs(limit=reconcile_limit)
        schedule = rebalance_content_schedule()
        self.stdout.write(
            f"Content reconciliation: created={sync['created']}, existing={sync['existing']}; "
            f"scheduled backlog={schedule['scheduled']}."
        )

        # Recover conversion jobs abandoned by a killed cron process. This stage
        # never sends recipient email itself.
        NewsletterJob.objects.filter(
            status='processing',
            updated_at__lt=timezone.now() - timedelta(minutes=30),
            attempts__lt=models.F('max_attempts'),
        ).update(status='pending', run_after=timezone.now(), last_error='Recovered stale content conversion job')

        if active_auto_content_campaign_exists():
            self.stdout.write(
                'An automatic content campaign is already scheduled/queued/sending/paused; '
                'older content remains safely in the database queue.'
            )
            return

        processed = 0
        while processed < limit:
            candidate = due_content_job()
            if candidate is None:
                break

            with transaction.atomic():
                job = NewsletterJob.objects.select_for_update().get(pk=candidate.pk)
                if job.status not in ('pending', 'failed') or job.run_after > timezone.now():
                    continue
                job.status = 'processing'
                job.attempts += 1
                job.last_error = ''
                job.save(update_fields=['status', 'attempts', 'last_error', 'updated_at'])

            try:
                campaign = materialize_job_as_campaign(job)
            except Exception as exc:
                logger.exception('Content marketing conversion job %s failed', job.pk)
                job.status = 'failed'
                job.last_error = str(exc)[:4000]
                job.run_after = timezone.now() + timedelta(minutes=retry_delay)
                job.save(update_fields=['status', 'last_error', 'run_after', 'updated_at'])
                self.stderr.write(self.style.WARNING(f'Content job {job.pk} failed: {exc}'))
            else:
                if campaign is None:
                    self.stdout.write(self.style.WARNING(
                        f'Content job {job.pk} was skipped because the content is no longer marketable.'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'Content job {job.pk} -> marketing campaign #{campaign.pk} ({campaign.subject})'
                    ))
            processed += 1

            # Only one automatic content broadcast may exist at once. This keeps
            # newer content from creating overlapping 6,000-recipient campaigns.
            if active_auto_content_campaign_exists():
                break

        self.stdout.write(
            f'Converted {processed} content queue row(s). Run process_marketing_queue for controlled recipient delivery.'
        )
