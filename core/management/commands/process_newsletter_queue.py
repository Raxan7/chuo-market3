import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone

from core.content_marketing import (
    active_auto_content_campaign_exists,
    due_content_jobs,
    materialize_jobs_as_digest,
    rebalance_content_schedule,
    sync_content_jobs,
)
from core.models import NewsletterJob

logger = logging.getLogger('core.email')


class Command(BaseCommand):
    help = (
        'Reconcile published ChuoSmart content and convert due rows into '
        'throttled digest marketing campaigns. Recipient SMTP delivery is '
        'handled by process_marketing_queue.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=1,
            help='Maximum digest campaigns to materialize in this run. Serial safety normally limits this to one.',
        )
        parser.add_argument(
            '--digest-size', type=int,
            default=getattr(settings, 'CONTENT_MARKETING_DIGEST_SIZE', 12),
            help='Maximum content items grouped into one automatic digest.',
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
        digest_size = max(1, min(int(options['digest_size']), 30))
        retry_delay = max(1, int(options['retry_delay_minutes']))
        reconcile_limit = None if options['backfill_all'] else max(1, int(options['reconcile_limit']))

        sync = sync_content_jobs(limit=reconcile_limit)
        schedule = rebalance_content_schedule()
        self.stdout.write(
            f"Content reconciliation: created={sync['created']}, existing={sync['existing']}; "
            f"scheduled backlog={schedule['scheduled']} across {schedule['campaign_slots']} digest slot(s) "
            f"(up to {schedule['digest_size']} items each)."
        )

        # Recover content rows abandoned by a killed cron process. This stage
        # never sends recipient email itself.
        NewsletterJob.objects.filter(
            status='processing',
            updated_at__lt=timezone.now() - timedelta(minutes=30),
            attempts__lt=models.F('max_attempts'),
        ).update(status='pending', run_after=timezone.now(), last_error='Recovered stale content conversion job')

        if active_auto_content_campaign_exists():
            self.stdout.write(
                'An automatic content campaign is already scheduled/queued/sending/paused; '
                'the remaining content inventory stays queued and will advance after it finishes.'
            )
            return

        processed_campaigns = 0
        consumed_rows = 0
        while processed_campaigns < limit:
            entries = due_content_jobs(limit=digest_size)
            if not entries:
                break

            ids = [job.pk for job, _ in entries]
            with transaction.atomic():
                jobs = list(NewsletterJob.objects.select_for_update().filter(pk__in=ids))
                locked = {job.pk: job for job in jobs}
                eligible_entries = []
                for job, instance in entries:
                    current = locked.get(job.pk)
                    if not current:
                        continue
                    if current.status not in ('pending', 'failed') or current.run_after > timezone.now():
                        continue
                    current.status = 'processing'
                    current.attempts += 1
                    current.last_error = ''
                    current.save(update_fields=['status', 'attempts', 'last_error', 'updated_at'])
                    eligible_entries.append((current, instance))

            if not eligible_entries:
                break

            try:
                campaign = materialize_jobs_as_digest(eligible_entries)
            except Exception as exc:
                logger.exception('Content marketing digest conversion failed for rows %s', ids)
                NewsletterJob.objects.filter(pk__in=[job.pk for job, _ in eligible_entries]).update(
                    status='failed',
                    last_error=str(exc)[:4000],
                    run_after=timezone.now() + timedelta(minutes=retry_delay),
                )
                self.stderr.write(self.style.WARNING(f'Content digest failed: {exc}'))
            else:
                consumed_rows += len(eligible_entries)
                if campaign is None:
                    self.stdout.write(self.style.WARNING(
                        f'Skipped {len(eligible_entries)} content row(s) because none remained marketable.'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'{len(eligible_entries)} content row(s) -> marketing campaign #{campaign.pk} ({campaign.subject})'
                    ))
            processed_campaigns += 1

            # Only one automatic broadcast may exist at once. The delivery
            # worker drains it before the next digest is created.
            if active_auto_content_campaign_exists():
                break

        self.stdout.write(
            f'Converted {consumed_rows} content queue row(s) into {processed_campaigns} digest campaign(s). '
            'Run process_marketing_queue for controlled recipient delivery.'
        )
