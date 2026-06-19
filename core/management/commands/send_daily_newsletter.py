"""
Management command to send the daily newsletter digest.

Sends one daily digest email per subscribed user if there is new content.
Safe to run multiple times per day - prevents duplicate sends via NewsletterSendLog.

Usage:
    python manage.py send_daily_newsletter
    python manage.py send_daily_newsletter --date 2026-01-15
    python manage.py send_daily_newsletter --dry-run
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.newsletter import get_daily_digest_data, send_daily_digest_all_subscribers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily newsletter digest to all active subscribers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date in YYYY-MM-DD format (default: today)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        from datetime import datetime

        dry_run = options.get('dry_run', False)

        if options.get('date'):
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Date must be in YYYY-MM-DD format')
        else:
            target_date = timezone.now().date()

        self.stdout.write(f'Newsletter digest for date: {target_date}')

        # Check what content is available
        digest_data = get_daily_digest_data(target_date=target_date)
        qualifying = digest_data['qualifying_categories']

        if not qualifying:
            self.stdout.write(self.style.WARNING('No qualifying categories with new content today. No digest will be sent.'))
            return

        self.stdout.write(f'Qualifying categories: {", ".join(qualifying)}')

        if qualifying:
            for cat in digest_data['categories']:
                self.stdout.write(f'  {cat["label"]}: {cat["item_count"]} item(s)')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete. No emails sent.'))
            return

        results = send_daily_digest_all_subscribers(target_date=target_date)

        self.stdout.write(f'Sent: {results["sent"]}')
        self.stdout.write(f'Skipped (already sent today): {results.get("already_sent", 0)}')
        self.stdout.write(f'Failed: {results["failed"]}')
        self.stdout.write(f'Skipped (other): {results.get("skipped", 0)}')

        if results['failed'] > 0:
            self.stdout.write(self.style.ERROR(f'{results["failed"]} digest(s) failed to send'))
        elif results['sent'] > 0:
            self.stdout.write(self.style.SUCCESS(f'{results["sent"]} digest(s) sent successfully'))
        else:
            self.stdout.write(self.style.WARNING('No digests sent'))
