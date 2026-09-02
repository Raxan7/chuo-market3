from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    NewsletterJob, NewsletterDelivery, MarketingCampaign, MarketingDelivery, MarketingSuppression,
)


class Command(BaseCommand):
    help = 'Show safe email configuration diagnostics and optionally send a real test email.'

    def add_arguments(self, parser):
        parser.add_argument('--to', dest='recipient')
        parser.add_argument('--send', action='store_true')

    def handle(self, *args, **options):
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        rows = {
            'DEBUG': getattr(settings, 'DEBUG', None),
            'EMAIL_BACKEND': backend,
            'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', ''),
            'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', ''),
            'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', False),
            'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', False),
            'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', ''),
            'EMAIL_PASSWORD_CONFIGURED': bool(password),
            'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
        }
        for key, value in rows.items():
            self.stdout.write(f'{key}={value}')

        pending_jobs = NewsletterJob.objects.filter(status='pending').count()
        failed_jobs = NewsletterJob.objects.filter(status='failed').count()
        pending_deliveries = NewsletterDelivery.objects.filter(status='pending').count()
        failed_deliveries = NewsletterDelivery.objects.filter(status='failed').count()
        oldest_pending = NewsletterJob.objects.filter(status='pending').order_by('created_at').first()
        self.stdout.write(f'NEWSLETTER_PENDING_JOBS={pending_jobs}')
        self.stdout.write(f'NEWSLETTER_FAILED_JOBS={failed_jobs}')
        self.stdout.write(f'NEWSLETTER_PENDING_DELIVERIES={pending_deliveries}')
        self.stdout.write(f'NEWSLETTER_FAILED_DELIVERIES={failed_deliveries}')
        if oldest_pending:
            age = timezone.now() - oldest_pending.created_at
            self.stdout.write(f'NEWSLETTER_OLDEST_PENDING_MINUTES={int(age.total_seconds() // 60)}')
            if age.total_seconds() > 15 * 60:
                self.stderr.write(self.style.WARNING(
                    'Newsletter queue has been pending for more than 15 minutes. '
                    'Ensure run_email_marketing_engine is running from cron.'
                ))

        self.stdout.write(f"MARKETING_EMAIL_BACKEND={getattr(settings, 'MARKETING_EMAIL_BACKEND', settings.EMAIL_BACKEND)}")
        self.stdout.write(f"MARKETING_EMAIL_HOST={getattr(settings, 'MARKETING_EMAIL_HOST', settings.EMAIL_HOST)}")
        self.stdout.write(f"MARKETING_EMAIL_PORT={getattr(settings, 'MARKETING_EMAIL_PORT', settings.EMAIL_PORT)}")
        self.stdout.write(f"MARKETING_EMAIL_HOST_USER={getattr(settings, 'MARKETING_EMAIL_HOST_USER', settings.EMAIL_HOST_USER)}")
        self.stdout.write(f"MARKETING_EMAIL_PASSWORD_CONFIGURED={bool(getattr(settings, 'MARKETING_EMAIL_HOST_PASSWORD', ''))}")
        self.stdout.write(f"MARKETING_EMAIL_USE_SSL={getattr(settings, 'MARKETING_EMAIL_USE_SSL', settings.EMAIL_USE_SSL)}")
        self.stdout.write(f"MARKETING_EMAIL_USE_TLS={getattr(settings, 'MARKETING_EMAIL_USE_TLS', settings.EMAIL_USE_TLS)}")
        self.stdout.write(f"MARKETING_FROM_EMAIL={getattr(settings, 'MARKETING_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)}")
        self.stdout.write(f"MARKETING_BURST_CAP={getattr(settings, 'MARKETING_EMAIL_BURST_CAP', '')}")
        self.stdout.write(f"MARKETING_TEN_MINUTE_CAP={getattr(settings, 'MARKETING_EMAIL_TEN_MINUTE_CAP', '')}")
        self.stdout.write(f"MARKETING_HOURLY_CAP={getattr(settings, 'MARKETING_EMAIL_HOURLY_CAP', '')}")
        self.stdout.write(f"MARKETING_DAILY_CAP={getattr(settings, 'MARKETING_EMAIL_DAILY_CAP', '')}")
        self.stdout.write(f"CONTENT_MARKETING_CAMPAIGN_GAP_HOURS={getattr(settings, 'CONTENT_MARKETING_CAMPAIGN_GAP_HOURS', '')}")
        self.stdout.write(f"CONTENT_MARKETING_DIGEST_SIZE={getattr(settings, 'CONTENT_MARKETING_DIGEST_SIZE', '')}")

        marketing_active = MarketingCampaign.objects.filter(status__in=['scheduled', 'queued', 'sending']).count()
        marketing_pending = MarketingDelivery.objects.filter(status='pending').count()
        marketing_failed = MarketingDelivery.objects.filter(status='failed').count()
        marketing_suppressed = MarketingSuppression.objects.filter(is_active=True).count()
        oldest_marketing = MarketingDelivery.objects.filter(status='pending').order_by('created_at').first()
        self.stdout.write(f'MARKETING_ACTIVE_CAMPAIGNS={marketing_active}')
        self.stdout.write(f'MARKETING_PENDING_DELIVERIES={marketing_pending}')
        self.stdout.write(f'MARKETING_FAILED_DELIVERIES={marketing_failed}')
        self.stdout.write(f'MARKETING_ACTIVE_SUPPRESSIONS={marketing_suppressed}')
        if oldest_marketing:
            age = timezone.now() - oldest_marketing.created_at
            self.stdout.write(f'MARKETING_OLDEST_PENDING_MINUTES={int(age.total_seconds() // 60)}')
            if age.total_seconds() > 15 * 60:
                self.stderr.write(self.style.WARNING(
                    'Marketing queue has been pending for more than 15 minutes. '
                    'Ensure run_email_marketing_engine is running from cron.'
                ))

        if 'console.EmailBackend' in backend:
            self.stderr.write(self.style.WARNING('Console email backend is active; messages will not leave the server.'))

        if options['send']:
            recipient = options['recipient']
            if not recipient:
                raise CommandError('--to EMAIL is required with --send')
            sent = send_mail(
                'ChuoSmart email diagnostics',
                'If you received this message, Django successfully handed one email to the configured backend.',
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
            if sent != 1:
                raise CommandError(f'Email backend returned {sent}; expected 1')
            self.stdout.write(self.style.SUCCESS(f'Test email accepted for delivery to {recipient}.'))
