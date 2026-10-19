from django.core.management.base import BaseCommand
from payouts.models import PayoutTransfer
from payouts.service import reconcile_transfer, PayoutSafetyError


class Command(BaseCommand):
    help = 'Independently verify submitted Snippe payout references; safe to schedule regularly.'

    def add_arguments(self, parser):
        parser.add_argument('--payout-id', type=int)

    def handle(self, *args, **opts):
        qs = PayoutTransfer.objects.all()
        if opts['payout_id']:
            qs = qs.filter(payout_request_id=opts['payout_id'])
        else:
            qs = qs.filter(status__in=['sending', 'unknown', 'pending', 'completed'])
        for transfer in qs.order_by('id').iterator():
            try:
                result = reconcile_transfer(transfer.payout_request_id)
                self.stdout.write(f'Payout #{result.payout_request_id}: {result.status}')
            except PayoutSafetyError as exc:
                # A failed GET or missing reference NEVER authorizes another send.
                self.stderr.write(f'Payout #{transfer.payout_request_id}: manual attention required ({exc})')
