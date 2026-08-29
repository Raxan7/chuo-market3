import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone

from core.models import NewsletterJob
from core.newsletter import process_newsletter_job

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process durable ChuoSmart content-newsletter jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20)
        parser.add_argument('--retry-delay-minutes', type=int, default=10)

    def handle(self, *args, **options):
        limit = max(1, min(options['limit'], 500))
        retry_delay = max(1, options['retry_delay_minutes'])
        processed = 0

        # Recover jobs abandoned by a killed web/cron process.
        NewsletterJob.objects.filter(
            status='processing',
            updated_at__lt=timezone.now() - timedelta(minutes=30),
            attempts__lt=models.F('max_attempts'),
        ).update(status='pending', run_after=timezone.now(), last_error='Recovered stale processing job')

        while processed < limit:
            with transaction.atomic():
                job = (
                    NewsletterJob.objects.select_for_update()
                    .filter(status__in=['pending', 'failed'], run_after__lte=timezone.now())
                    .filter(attempts__lt=models.F('max_attempts'))
                    .order_by('created_at')
                    .first()
                )
                if not job:
                    break
                job.status = 'processing'
                job.attempts += 1
                job.last_error = ''
                job.save(update_fields=['status', 'attempts', 'last_error', 'updated_at'])

            try:
                delivered = process_newsletter_job(job)
            except Exception as exc:
                logger.exception('Newsletter job %s failed', job.pk)
                job.status = 'failed'
                job.last_error = str(exc)[:4000]
                job.run_after = timezone.now() + timedelta(minutes=retry_delay)
                job.save(update_fields=['status', 'last_error', 'run_after', 'updated_at'])
                self.stderr.write(self.style.WARNING(f'Job {job.pk} failed: {exc}'))
            else:
                job.status = 'sent'
                job.processed_at = timezone.now()
                job.last_error = ''
                job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'Job {job.pk}: delivered {delivered} email(s)'))
            processed += 1

        self.stdout.write(f'Processed {processed} newsletter job(s).')
