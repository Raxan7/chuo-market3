import logging
import smtplib
import time
from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.marketing import queue_due_campaigns, refresh_campaign_stats, send_delivery, suppress_email
from core.models import MarketingCampaign, MarketingDelivery, NewsletterDelivery, NewsletterSendLog

logger = logging.getLogger('core.email')


class Command(BaseCommand):
    help = 'Prepare due ChuoSmart marketing campaigns and send a controlled batch of queued deliveries.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=getattr(settings, 'MARKETING_EMAIL_MAX_PER_RUN', 100),
            help='Maximum recipient emails sent in this run.',
        )
        parser.add_argument(
            '--campaign-limit',
            type=int,
            default=10,
            help='Maximum due campaigns to materialize in this run.',
        )
        parser.add_argument(
            '--retry-base-minutes',
            type=int,
            default=getattr(settings, 'MARKETING_EMAIL_RETRY_BASE_MINUTES', 10),
        )

    def _recover_stale(self):
        stale_minutes = getattr(settings, 'MARKETING_EMAIL_STALE_MINUTES', 30)
        cutoff = timezone.now() - timedelta(minutes=max(5, stale_minutes))
        return MarketingDelivery.objects.filter(
            status='sending',
            updated_at__lt=cutoff,
            campaign__status__in=['sending', 'queued'],
        ).update(
            status='failed',
            run_after=timezone.now(),
            last_error='Recovered stale delivery after interrupted worker.',
        )

    def _claim_next(self):
        """Claim one delivery safely so overlapping cron runs cannot double-send it."""
        while True:
            with transaction.atomic():
                delivery = (
                    MarketingDelivery.objects.select_for_update()
                    .select_related('campaign')
                    .filter(
                        status__in=['pending', 'failed'],
                        attempts__lt=F('max_attempts'),
                        run_after__lte=timezone.now(),
                        campaign__status__in=['sending', 'queued'],
                    )
                    .order_by('run_after', 'created_at')
                    .first()
                )
                if delivery is None:
                    return None
                delivery.status = 'sending'
                delivery.attempts += 1
                delivery.last_error = ''
                delivery.save(update_fields=['status', 'attempts', 'last_error', 'updated_at'])
                return delivery

    def _rate_budget(self, requested_limit):
        """Apply a domain-wide warm-up budget before touching SMTP."""
        now = timezone.now()
        burst_cap = max(1, int(getattr(settings, 'MARKETING_EMAIL_BURST_CAP', 3)))
        ten_minute_cap = max(1, int(getattr(settings, 'MARKETING_EMAIL_TEN_MINUTE_CAP', 15)))
        hourly_cap = max(1, int(getattr(settings, 'MARKETING_EMAIL_HOURLY_CAP', 100)))
        daily_cap = max(1, int(getattr(settings, 'MARKETING_EMAIL_DAILY_CAP', 1500)))
        ten_cutoff = now - timedelta(minutes=10)
        hour_cutoff = now - timedelta(hours=1)
        sent_ten_minutes = (
            MarketingDelivery.objects.filter(status='sent', sent_at__gte=ten_cutoff).count()
            + NewsletterDelivery.objects.filter(status='sent', sent_at__gte=ten_cutoff).count()
            + NewsletterSendLog.objects.filter(status='sent', sent_at__gte=ten_cutoff).count()
        )
        sent_hour = (
            MarketingDelivery.objects.filter(status='sent', sent_at__gte=hour_cutoff).count()
            + NewsletterDelivery.objects.filter(status='sent', sent_at__gte=hour_cutoff).count()
            + NewsletterSendLog.objects.filter(status='sent', sent_at__gte=hour_cutoff).count()
        )
        local_now = timezone.localtime(now) if timezone.is_aware(now) else now
        day_start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_start = day_start_local.astimezone(dt_timezone.utc) if timezone.is_aware(day_start_local) else day_start_local
        sent_day = (
            MarketingDelivery.objects.filter(status='sent', sent_at__gte=day_start).count()
            + NewsletterDelivery.objects.filter(status='sent', sent_at__gte=day_start).count()
            + NewsletterSendLog.objects.filter(status='sent', sent_at__gte=day_start).count()
        )
        remaining_ten_minutes = max(0, ten_minute_cap - sent_ten_minutes)
        remaining_hour = max(0, hourly_cap - sent_hour)
        remaining_day = max(0, daily_cap - sent_day)
        return min(requested_limit, burst_cap, remaining_ten_minutes, remaining_hour, remaining_day), {
            'burst_cap': burst_cap, 'ten_minute_cap': ten_minute_cap,
            'hourly_cap': hourly_cap, 'daily_cap': daily_cap,
            'sent_ten_minutes': sent_ten_minutes, 'sent_hour': sent_hour, 'sent_day': sent_day,
            'remaining_ten_minutes': remaining_ten_minutes,
            'remaining_hour': remaining_hour, 'remaining_day': remaining_day,
        }

    def handle(self, *args, **options):
        requested_limit = max(1, min(int(options['limit']), 1000))
        limit, budget = self._rate_budget(requested_limit)
        if limit <= 0:
            self.stdout.write(
                'Marketing rate cap reached: '
                f"10m={budget['sent_ten_minutes']}/{budget['ten_minute_cap']}, "
                f"hour={budget['sent_hour']}/{budget['hourly_cap']}, "
                f"day={budget['sent_day']}/{budget['daily_cap']}. No SMTP connection opened."
            )
            return
        campaign_limit = max(1, min(int(options['campaign_limit']), 50))
        retry_base = max(1, int(options['retry_base_minutes']))

        recovered = self._recover_stale()
        prepared = queue_due_campaigns(limit=campaign_limit)
        # Reconcile campaigns left in sending state by a previous interrupted run.
        for campaign_id in MarketingCampaign.objects.filter(status='sending').values_list('id', flat=True)[:200]:
            refresh_campaign_stats(campaign_id)
        self.stdout.write(f'Prepared {prepared} campaign(s); recovered {recovered} stale delivery row(s).')
        self.stdout.write(
            f"Rate budget this run: {limit} message(s); "
            f"10m={budget['sent_ten_minutes']}/{budget['ten_minute_cap']}, "
            f"hour={budget['sent_hour']}/{budget['hourly_cap']}, "
            f"day={budget['sent_day']}/{budget['daily_cap']}."
        )

        connection = get_connection(fail_silently=False)
        processed = 0
        sent = 0
        failed = 0
        suppressed = 0
        touched_campaigns = set()

        try:
            try:
                connection.open()
            except (AttributeError, NotImplementedError):
                pass
            except smtplib.SMTPAuthenticationError as exc:
                raise CommandError(
                    f'SMTP authentication failed before queue processing started: {exc}'
                )
            except (smtplib.SMTPException, OSError) as exc:
                raise CommandError(f'Unable to open SMTP connection: {exc}')
            while processed < limit:
                delivery = self._claim_next()
                if delivery is None:
                    break
                touched_campaigns.add(delivery.campaign_id)
                processed += 1

                try:
                    delivered = send_delivery(delivery, connection=connection)
                except smtplib.SMTPAuthenticationError as exc:
                    # A bad SMTP password is global infrastructure failure. Stop immediately
                    # rather than burning an attempt for thousands of recipients.
                    delay = timezone.now() + timedelta(minutes=max(30, retry_base))
                    delivery.status = 'failed'
                    delivery.run_after = delay
                    delivery.last_error = f'SMTP authentication failed: {exc}'[:4000]
                    delivery.save(update_fields=['status', 'run_after', 'last_error', 'updated_at'])
                    refresh_campaign_stats(delivery.campaign_id)
                    raise CommandError('SMTP authentication failed. Marketing queue halted; remaining recipients were not attempted.')
                except smtplib.SMTPRecipientsRefused as exc:
                    refusal_codes = [value[0] for value in exc.recipients.values() if value]
                    if refusal_codes and all(int(code) >= 500 for code in refusal_codes):
                        suppress_email(delivery.recipient_email, reason='bounce', source='smtp_hard_bounce')
                        delivery.status = 'suppressed'
                        delivery.last_error = f'Permanent recipient rejection: {exc}'[:4000]
                        delivery.save(update_fields=['status', 'last_error', 'updated_at'])
                        suppressed += 1
                        self.stderr.write(self.style.WARNING(
                            f'Hard bounce suppressed {delivery.recipient_email}; it will not be retried.'
                        ))
                        continue
                    failed += 1
                    backoff_minutes = min(24 * 60, retry_base * (2 ** max(0, delivery.attempts - 1)))
                    delivery.status = 'failed'
                    delivery.run_after = timezone.now() + timedelta(minutes=backoff_minutes)
                    delivery.last_error = str(exc)[:4000]
                    delivery.save(update_fields=['status', 'run_after', 'last_error', 'updated_at'])
                except Exception as exc:
                    failed += 1
                    backoff_minutes = min(24 * 60, retry_base * (2 ** max(0, delivery.attempts - 1)))
                    delivery.status = 'failed'
                    delivery.run_after = timezone.now() + timedelta(minutes=backoff_minutes)
                    delivery.last_error = str(exc)[:4000]
                    delivery.save(update_fields=['status', 'run_after', 'last_error', 'updated_at'])
                    logger.exception('Marketing delivery %s failed', delivery.pk)
                    self.stderr.write(self.style.WARNING(
                        f'Delivery {delivery.pk} to {delivery.recipient_email} failed; retry in {backoff_minutes} minute(s).'
                    ))
                    # Reset the SMTP connection after an unexpected transport failure.
                    try:
                        connection.close()
                    except Exception:
                        pass
                    try:
                        connection.open()
                    except Exception:
                        pass
                else:
                    if delivered:
                        sent += 1
                    else:
                        suppressed += 1

                pause_seconds = max(0.0, float(getattr(settings, 'MARKETING_EMAIL_SECONDS_BETWEEN_SENDS', 1)))
                if pause_seconds and processed < limit:
                    time.sleep(min(pause_seconds, 10.0))

            for campaign_id in touched_campaigns:
                refresh_campaign_stats(campaign_id)
        finally:
            try:
                connection.close()
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            f'Processed {processed} marketing delivery(s): sent={sent}, failed={failed}, suppressed={suppressed}.'
        ))
