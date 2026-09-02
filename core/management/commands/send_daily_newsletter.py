"""Queue (never directly bulk-send) the ChuoSmart daily digest."""

from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import MarketingCampaign
from core.newsletter import get_daily_digest_data, get_site_root_url


class Command(BaseCommand):
    help = 'Queue the daily digest through the throttled marketing engine.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format (default: today)')
        parser.add_argument('--dry-run', action='store_true', help='Show the digest without queueing a campaign')

    def handle(self, *args, **options):
        if options.get('date'):
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Date must be in YYYY-MM-DD format')
        else:
            target_date = timezone.localdate()

        digest = get_daily_digest_data(target_date=target_date)
        if not digest['categories']:
            self.stdout.write(self.style.WARNING('No qualifying new content. No digest campaign queued.'))
            return

        lines = []
        for category in digest['categories']:
            lines.append(f"{category['label']}:")
            for item in category['items'][:5]:
                lines.append(f"- {item['title']}")
            lines.append('')
        body = '\n'.join(lines).strip()
        self.stdout.write(body)
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('Dry run complete. No recipient email sent or queued.'))
            return

        name = f'[AUTO-DIGEST:{target_date.isoformat()}] ChuoSmart updates'
        campaign, created = MarketingCampaign.objects.get_or_create(
            name=name,
            defaults={
                'kind': 'announcement',
                'audience': 'all_opted_in',
                'subject': "What's new on ChuoSmart",
                'preheader': 'Fresh opportunities, learning and useful ChuoSmart updates',
                'headline': 'Fresh on ChuoSmart',
                'body': body,
                'cta_text': 'Open ChuoSmart',
                'cta_url': get_site_root_url(),
                'status': 'queued',
                'scheduled_for': timezone.now(),
                'minimum_gap_hours': max(1, int(getattr(settings, 'CONTENT_MARKETING_RECIPIENT_GAP_HOURS', 48))),
                'max_attempts': max(1, int(getattr(settings, 'MARKETING_EMAIL_MAX_ATTEMPTS', 5))),
                'last_test_sent_at': timezone.now(),
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Digest queued as marketing campaign #{campaign.pk}; process_marketing_queue will deliver it safely.'
            ))
        else:
            self.stdout.write(f'Digest campaign #{campaign.pk} already exists; duplicate queueing was prevented.')
