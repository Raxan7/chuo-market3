from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.marketing import classify_smtp_refusal_data, refresh_campaign_stats
from core.models import MarketingCampaign, MarketingDelivery, MarketingSuppression


class Command(BaseCommand):
    help = (
        'Review suppressions created by the older broad SMTP hard-bounce logic. '
        'Ambiguous/policy rejections can be safely released and retried.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually release ambiguous legacy suppressions.')

    @staticmethod
    def _classify_error(text):
        value = (text or '').lower()
        # Older rows store the SMTP exception in plain text. Pull common status
        # codes out loosely; classification remains conservative.
        codes = []
        for token in value.replace(',', ' ').replace('(', ' ').replace(')', ' ').split():
            cleaned = token.strip("'\"b:{}[]")
            if cleaned.isdigit() and len(cleaned) == 3:
                codes.append(int(cleaned))
        return classify_smtp_refusal_data(codes, [value])

    def handle(self, *args, **options):
        apply_changes = bool(options['apply'])
        queryset = MarketingSuppression.objects.filter(
            is_active=True,
            reason='bounce',
            source='smtp_hard_bounce',
        ).order_by('email')

        reviewed = 0
        releasable = 0
        retained = 0
        affected_campaigns = set()

        for suppression in queryset.iterator(chunk_size=500):
            delivery = MarketingDelivery.objects.filter(
                recipient_email__iexact=suppression.email,
                status='suppressed',
            ).order_by('-updated_at').first()
            classification = self._classify_error(delivery.last_error if delivery else '')
            reviewed += 1
            if classification == 'hard_bounce':
                retained += 1
                self.stdout.write(f'KEEP {suppression.email} | explicit hard-bounce evidence')
                continue

            releasable += 1
            self.stdout.write(f'RELEASE {suppression.email} | legacy {classification or "ambiguous"} rejection')
            if not apply_changes:
                continue

            with transaction.atomic():
                suppression.is_active = False
                suppression.source = 'smtp_hard_bounce_reclassified'
                suppression.save(update_fields=['is_active', 'source', 'updated_at'])
                if delivery:
                    delivery.status = 'failed'
                    delivery.attempts = 0
                    delivery.run_after = timezone.now()
                    delivery.last_error = 'Released from legacy broad hard-bounce suppression; retry with Patch 11 classifier.'
                    delivery.save(update_fields=[
                        'status', 'attempts', 'run_after', 'last_error', 'updated_at'
                    ])
                    affected_campaigns.add(delivery.campaign_id)
                    MarketingCampaign.objects.filter(
                        pk=delivery.campaign_id,
                        status='completed',
                    ).update(status='sending', completed_at=None, updated_at=timezone.now())

        if apply_changes:
            for campaign_id in affected_campaigns:
                refresh_campaign_stats(campaign_id)

        self.stdout.write(
            f'Reviewed={reviewed}, releasable={releasable}, retained_confirmed_hard_bounces={retained}, '
            f'mode={"APPLY" if apply_changes else "DRY-RUN"}.'
        )
        if not apply_changes and releasable:
            self.stdout.write('Run again with --apply to release only the ambiguous legacy suppressions.')
