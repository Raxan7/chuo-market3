from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import NewsletterJob, NewsletterDelivery


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
                    'Ensure process_newsletter_queue is running from cron.'
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
