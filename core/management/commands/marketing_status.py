from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from core.content_marketing import active_auto_content_campaign_exists
from core.models import (
    MarketingCampaign,
    MarketingDelivery,
    MarketingSuppression,
    NewsletterJob,
    NewsletterSubscriber,
    UserNewsletterPreference,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Read-only operational status for the ChuoSmart email marketing engine.'

    def handle(self, *args, **options):
        opted_in_users = UserNewsletterPreference.objects.filter(
            newsletter=True, user__is_active=True
        ).exclude(user__email='').exclude(user__email__isnull=True).count()
        active_subscribers = NewsletterSubscriber.objects.filter(is_active=True).exclude(email='').count()
        suppressions = MarketingSuppression.objects.filter(is_active=True).count()
        content_pending = NewsletterJob.objects.filter(status__in=['pending', 'failed', 'processing']).count()

        self.stdout.write('=== ChuoSmart marketing status ===')
        self.stdout.write(f'OPTED_IN_REGISTERED_USERS={opted_in_users}')
        self.stdout.write(f'ACTIVE_NEWSLETTER_SUBSCRIBERS={active_subscribers}')
        self.stdout.write(f'ACTIVE_SUPPRESSIONS={suppressions}')
        self.stdout.write(f'CONTENT_QUEUE_OPEN={content_pending}')
        self.stdout.write(f'AUTO_CONTENT_CAMPAIGN_ACTIVE={active_auto_content_campaign_exists()}')

        self.stdout.write('CAMPAIGNS_BY_STATUS:')
        campaign_rows = MarketingCampaign.objects.values('status').annotate(total=Count('id')).order_by('status')
        for row in campaign_rows:
            self.stdout.write(f"  {row['status']}={row['total']}")

        self.stdout.write('DELIVERIES_BY_STATUS:')
        delivery_rows = MarketingDelivery.objects.values('status').annotate(total=Count('id')).order_by('status')
        for row in delivery_rows:
            self.stdout.write(f"  {row['status']}={row['total']}")

        active = MarketingCampaign.objects.filter(
            status__in=['scheduled', 'queued', 'sending', 'paused']
        ).order_by('scheduled_for', 'created_at').first()
        if active:
            active.refresh_from_db()
            pending = active.deliveries.filter(status__in=['pending', 'sending']).count()
            retryable = active.deliveries.filter(status='failed', attempts__lt=active.max_attempts).count()
            self.stdout.write(f'ACTIVE_CAMPAIGN_ID={active.pk}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_STATUS={active.status}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_SUBJECT={active.subject}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_TOTAL={active.total_recipients}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_SENT={active.sent_count}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_PENDING={pending}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_RETRYABLE_FAILED={retryable}')
            self.stdout.write(f'ACTIVE_CAMPAIGN_SKIPPED={active.skipped_count}')

            latest_sent = active.deliveries.filter(status='sent', sent_at__isnull=False).order_by('-sent_at').first()
            if latest_sent:
                self.stdout.write(f'LAST_SUCCESSFUL_SEND={latest_sent.sent_at.isoformat()}')
            recent_errors = active.deliveries.exclude(last_error='').order_by('-updated_at')[:5]
            if recent_errors:
                self.stdout.write('RECENT_DELIVERY_ERRORS:')
                for delivery in recent_errors:
                    self.stdout.write(
                        f'  {delivery.recipient_email} | {delivery.status} | {delivery.last_error[:350]}'
                    )
        else:
            self.stdout.write('ACTIVE_CAMPAIGN_ID=NONE')

        next_job = NewsletterJob.objects.filter(status__in=['pending', 'failed']).order_by('run_after').first()
        if next_job:
            self.stdout.write(
                f'NEXT_CONTENT_QUEUE_ITEM={next_job.job_type}:{next_job.object_id} at {next_job.run_after.isoformat()}'
            )

        if active and active.status == 'paused':
            self.stdout.write(self.style.WARNING('NEXT_ACTION=Resume the paused campaign in Django admin.'))
        elif active:
            self.stdout.write('NEXT_ACTION=Run `python manage.py run_email_marketing_engine --send-limit 10` or ensure its cron runs every minute.')
        elif content_pending:
            self.stdout.write('NEXT_ACTION=Run the unified engine; it will create the next due digest automatically.')
        else:
            self.stdout.write('NEXT_ACTION=No queued marketing work. New eligible content will be discovered on the next engine tick.')
