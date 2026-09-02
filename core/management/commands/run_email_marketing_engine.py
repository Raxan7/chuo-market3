import logging

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('core.email')


class Command(BaseCommand):
    help = (
        'Run one complete ChuoSmart marketing-engine tick: reconcile database content, '
        'create the next due digest when possible, then deliver a rate-limited SMTP batch.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-limit', type=int,
            default=getattr(settings, 'MARKETING_EMAIL_MAX_PER_RUN', 10),
            help='Requested delivery count; global safety caps still apply.',
        )
        parser.add_argument(
            '--digest-size', type=int,
            default=getattr(settings, 'CONTENT_MARKETING_DIGEST_SIZE', 12),
        )
        parser.add_argument(
            '--reconcile-limit', type=int,
            default=getattr(settings, 'CONTENT_MARKETING_RECONCILE_LIMIT', 250),
        )
        parser.add_argument('--backfill-all', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write('=== ChuoSmart email marketing engine tick ===')
        newsletter_options = {
            'limit': 1,
            'digest_size': max(1, min(int(options['digest_size']), 30)),
            'reconcile_limit': max(1, int(options['reconcile_limit'])),
        }
        if options['backfill_all']:
            newsletter_options['backfill_all'] = True

        try:
            call_command('process_newsletter_queue', stdout=self.stdout, stderr=self.stderr, **newsletter_options)
            call_command(
                'process_marketing_queue',
                limit=max(1, min(int(options['send_limit']), 1000)),
                campaign_limit=1,
                stdout=self.stdout,
                stderr=self.stderr,
            )
        except CommandError:
            logger.exception('Marketing engine tick halted by a controlled command error')
            raise
        except Exception as exc:
            logger.exception('Unexpected marketing engine tick failure')
            raise CommandError(f'Marketing engine tick failed safely: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Marketing engine tick completed.'))
