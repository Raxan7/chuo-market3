from django.core.management.base import BaseCommand, CommandError

from core.marketing import render_campaign_message
from core.models import MarketingCampaign


class Command(BaseCommand):
    help = 'Send one real marketing-shaped ChuoSmart email without queueing a bulk campaign.'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Recipient email address for the production marketing-path test.')

    def handle(self, *args, **options):
        recipient = (options['to'] or '').strip().lower()
        if '@' not in recipient:
            raise CommandError('Provide a valid --to email address.')

        campaign = MarketingCampaign(
            name='Production marketing path diagnostic',
            kind='announcement',
            audience='all_opted_in',
            subject='ChuoSmart marketing email test',
            preheader='This is a one-recipient production marketing-path diagnostic.',
            headline='Your ChuoSmart marketing engine is connected',
            body=(
                'This message uses the same template, sender identity, unsubscribe headers and SMTP path '
                'as ChuoSmart marketing campaigns. It was sent only to the address supplied to the command.'
            ),
            cta_text='Open ChuoSmart',
            cta_url='https://chuosmart.com/',
        )
        message = render_campaign_message(campaign, recipient, display_name='there')
        sent = message.send(fail_silently=False)
        if sent != 1:
            raise CommandError(f'Marketing email backend returned {sent}; expected 1.')
        self.stdout.write(self.style.SUCCESS(
            f'Marketing-shaped test email accepted for delivery to {recipient}.'
        ))
