import smtplib

from django.core.management.base import BaseCommand, CommandError

from core.marketing import classify_smtp_recipient_refusal, get_marketing_connection, render_campaign_message
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
        connection = get_marketing_connection(fail_silently=False)
        message = render_campaign_message(campaign, recipient, display_name='there', connection=connection)
        try:
            sent = message.send(fail_silently=False)
        except smtplib.SMTPRecipientsRefused as exc:
            classification, codes, text = classify_smtp_recipient_refusal(exc)
            if classification == 'sender_suspended':
                raise CommandError(
                    'Marketing SMTP provider has suspended outbound mail for this sender/domain. '
                    f'codes={codes} response={text}. Configure MARKETING_EMAIL_* with an approved '
                    'marketing SMTP provider or ask the current provider to lift the suspension.'
                ) from exc
            raise CommandError(f'Marketing SMTP recipient refusal: codes={codes} response={text}') from exc
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as exc:
            code = getattr(exc, 'smtp_code', 0) or 0
            raw_error = getattr(exc, 'smtp_error', '') or str(exc)
            if isinstance(raw_error, bytes):
                raw_error = raw_error.decode('utf-8', errors='replace')
            raise CommandError(
                f'Marketing SMTP rejected the sender/message: code={code} response={raw_error}. '
                'Verify sender/domain approval with the configured MARKETING_EMAIL_* provider.'
            ) from exc
        except smtplib.SMTPAuthenticationError as exc:
            raise CommandError(f'Marketing SMTP authentication failed: {exc}') from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise CommandError(f'Marketing SMTP transport failed: {exc}') from exc
        if sent != 1:
            raise CommandError(f'Marketing email backend returned {sent}; expected 1.')
        self.stdout.write(self.style.SUCCESS(
            f'Marketing-shaped test email accepted for delivery to {recipient}.'
        ))
