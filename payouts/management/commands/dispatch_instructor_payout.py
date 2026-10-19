from django.core.management.base import BaseCommand, CommandError
from payouts.service import PayoutSafetyError, dispatch_transfer


class Command(BaseCommand):
    help = 'Send ONE independently approved instructor payout to Snippe (disabled by default).'

    def add_arguments(self, parser):
        parser.add_argument('--payout-id', type=int, required=True)
        parser.add_argument('--execute', action='store_true', help='Required to authorize a real provider request')

    def handle(self, *args, **opts):
        if not opts['execute']:
            raise CommandError('No transfer sent. --execute is required.')
        try:
            result = dispatch_transfer(opts['payout_id'])
        except PayoutSafetyError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Payout #{result.payout_request_id}: {result.status} (verify via reconcile_instructor_payouts)')
