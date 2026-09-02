"""Durable, consent-aware marketing email engine for ChuoSmart.

This module is deliberately separate from transactional email. Marketing
campaign failures must never interfere with password resets, receipts, or job
application notifications.
"""

import logging
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify

from .models import (
    MarketingCampaign,
    MarketingDelivery,
    MarketingSuppression,
    NewsletterDelivery,
    NewsletterSendLog,
    NewsletterSubscriber,
)
from .newsletter import build_one_click_unsubscribe_url, get_newsletter_delivery_emails, get_site_root_url

logger = logging.getLogger('core.email')
User = get_user_model()

HARD_BOUNCE_MARKERS = (
    '5.1.1', '5.1.0', 'user unknown', 'unknown user', 'no such user',
    'mailbox does not exist', 'address does not exist', 'recipient does not exist',
    'invalid recipient', 'recipient not found', 'account that you tried to reach does not exist',
)

SENDER_SUSPENSION_MARKERS = (
    'outgoing mail from', 'has been suspended', 'sending has been suspended',
    'outbound mail suspended', 'sender suspended', 'domain suspended',
)

POLICY_MARKERS = (
    'spam', 'policy', 'reputation', 'blocked', 'blacklist', 'relay', 'authentication',
    'unauthenticated', 'rate limit', 'too many', 'quota', 'prohibited', 'suspicious',
    'temporarily deferred', 'try again later',
)


def classify_smtp_refusal_data(codes, messages):
    """Conservatively classify SMTP refusal metadata.

    Only explicit nonexistent-mailbox signals are considered hard bounces. A
    generic 5xx is a sender/policy problem until proven otherwise.
    """
    normalized_codes = [int(code) for code in codes if code is not None]
    text = ' | '.join(str(message or '').lower() for message in messages)
    if ('suspend' in text and ('outgoing mail' in text or 'outbound mail' in text or 'sender' in text or 'domain' in text)) \
            or ('outgoing mail from' in text and 'suspended' in text):
        return 'sender_suspended'
    if any(marker in text for marker in HARD_BOUNCE_MARKERS):
        return 'hard_bounce'
    if any(code and code < 500 for code in normalized_codes):
        return 'transient'
    if any(marker in text for marker in POLICY_MARKERS):
        return 'policy'
    if normalized_codes and all(code >= 500 for code in normalized_codes):
        return 'policy'
    return 'transient'


def classify_smtp_recipient_refusal(exc):
    values = list(getattr(exc, 'recipients', {}).values())
    codes = []
    messages = []
    for value in values:
        if not value:
            continue
        code = int(value[0]) if value[0] is not None else 0
        raw = value[1] if len(value) > 1 else ''
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='replace')
        codes.append(code)
        messages.append(str(raw))
    return classify_smtp_refusal_data(codes, messages), codes, ' | '.join(messages).lower()




SAFE_LOCAL_EMAIL_BACKENDS = {
    'django.core.mail.backends.locmem.EmailBackend',
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
}
SMTP_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


def get_marketing_connection(fail_silently=False):
    """Return the email connection used by marketing mail.

    Production may use a dedicated MARKETING_EMAIL_* SMTP transport. During
    development/tests, however, Django often overrides EMAIL_BACKEND to a safe
    local backend. Marketing must follow that runtime override instead of using
    the SMTP value that base settings computed earlier; otherwise a test run can
    accidentally send real email.
    """
    base_backend = getattr(settings, 'EMAIL_BACKEND', SMTP_EMAIL_BACKEND)
    backend = getattr(settings, 'MARKETING_EMAIL_BACKEND', '') or base_backend

    # Never let a test/development process escape to SMTP while Django itself
    # is configured for an in-memory, console, or dummy backend. Production
    # uses the SMTP backend, so dedicated marketing SMTP remains unaffected.
    if base_backend in SAFE_LOCAL_EMAIL_BACKENDS:
        backend = base_backend

    if backend != SMTP_EMAIL_BACKEND:
        return get_connection(backend=backend, fail_silently=fail_silently)

    return get_connection(
        backend=backend,
        fail_silently=fail_silently,
        host=getattr(settings, 'MARKETING_EMAIL_HOST', settings.EMAIL_HOST),
        port=getattr(settings, 'MARKETING_EMAIL_PORT', settings.EMAIL_PORT),
        username=getattr(settings, 'MARKETING_EMAIL_HOST_USER', settings.EMAIL_HOST_USER),
        password=getattr(settings, 'MARKETING_EMAIL_HOST_PASSWORD', settings.EMAIL_HOST_PASSWORD),
        use_tls=getattr(settings, 'MARKETING_EMAIL_USE_TLS', settings.EMAIL_USE_TLS),
        use_ssl=getattr(settings, 'MARKETING_EMAIL_USE_SSL', settings.EMAIL_USE_SSL),
        timeout=getattr(settings, 'MARKETING_EMAIL_TIMEOUT', settings.EMAIL_TIMEOUT),
    )

def normalize_email(email):
    return (email or '').strip().lower()


def marketing_from_email():
    """Use a separately configurable From identity for promotional mail."""
    return getattr(settings, 'MARKETING_FROM_EMAIL', '').strip() or settings.DEFAULT_FROM_EMAIL


def marketing_list_id():
    return getattr(settings, 'MARKETING_LIST_ID', 'updates.chuosmart.com').strip() or 'updates.chuosmart.com'


def suppress_email(email, reason='unsubscribed', source='marketing'):
    email = normalize_email(email)
    if not email:
        return None
    suppression, _ = MarketingSuppression.objects.update_or_create(
        email=email,
        defaults={'reason': reason, 'source': source, 'is_active': True},
    )
    return suppression


def unsuppress_email(email):
    """Remove active suppression only after an explicit re-subscription action."""
    email = normalize_email(email)
    if not email:
        return 0
    return MarketingSuppression.objects.filter(email__iexact=email, is_active=True).update(
        is_active=False, updated_at=timezone.now()
    )


def is_marketing_allowed(email):
    """Re-check consent immediately before sending a queued marketing email."""
    email = normalize_email(email)
    if not email:
        return False
    if MarketingSuppression.objects.filter(email__iexact=email, is_active=True).exists():
        return False

    user_opted_in = User.objects.filter(
        is_active=True,
        email__iexact=email,
        newsletter_preference__newsletter=True,
    ).exists()
    subscriber_opted_in = NewsletterSubscriber.objects.filter(
        email__iexact=email,
        is_active=True,
    ).exists()
    return user_opted_in or subscriber_opted_in


def get_campaign_recipients(campaign):
    """Return deduplicated opted-in recipients for the selected audience."""
    recipients = {}

    if campaign.audience in ('all_opted_in', 'registered_users'):
        users = User.objects.filter(
            is_active=True,
            newsletter_preference__newsletter=True,
        ).exclude(email='').exclude(email__isnull=True).only('id', 'email', 'first_name', 'username')
        for user in users.iterator(chunk_size=1000):
            email = normalize_email(user.email)
            if not email:
                continue
            recipients[email] = {
                'email': email,
                'name': user.first_name or user.username or '',
                'user_id': user.pk,
            }

    if campaign.audience in ('all_opted_in', 'website_subscribers'):
        subscribers = NewsletterSubscriber.objects.filter(is_active=True).exclude(email='').only('email', 'name')
        for subscriber in subscribers.iterator(chunk_size=1000):
            email = normalize_email(subscriber.email)
            if not email:
                continue
            existing = recipients.get(email)
            if existing:
                if not existing['name'] and subscriber.name:
                    existing['name'] = subscriber.name
                continue
            recipients[email] = {
                'email': email,
                'name': subscriber.name or '',
                'user_id': None,
            }

    return list(recipients.values())


def was_recently_marketed(email, minimum_gap_hours, exclude_campaign_id=None):
    """Check the frequency cap against every ChuoSmart broadcast path.

    This is called both while materializing an audience and immediately before
    SMTP delivery so a long-running campaign cannot become stale relative to a
    newer send.
    """
    email = normalize_email(email)
    if not email or not minimum_gap_hours:
        return False
    cutoff = timezone.now() - timedelta(hours=minimum_gap_hours)
    marketing_qs = MarketingDelivery.objects.filter(
        recipient_email__iexact=email, status='sent', sent_at__gte=cutoff,
    )
    if exclude_campaign_id:
        marketing_qs = marketing_qs.exclude(campaign_id=exclude_campaign_id)
    if marketing_qs.exists():
        return True
    if NewsletterDelivery.objects.filter(
        recipient_email__iexact=email, status='sent', sent_at__gte=cutoff,
    ).exists():
        return True
    return NewsletterSendLog.objects.filter(
        subscriber_email__iexact=email, status='sent', sent_at__gte=cutoff,
    ).exists()


def prepare_campaign(campaign):
    """Materialize a campaign audience into durable delivery rows once."""
    campaign = MarketingCampaign.objects.get(pk=campaign.pk)
    if campaign.prepared_at:
        return campaign.deliveries.count()
    if campaign.status in ('cancelled', 'completed'):
        return 0

    recipients = get_campaign_recipients(campaign)
    emails = [item['email'] for item in recipients]
    suppressed = set(
        MarketingSuppression.objects.filter(email__in=emails, is_active=True).values_list('email', flat=True)
    )

    recent = set()
    if campaign.minimum_gap_hours:
        cutoff = timezone.now() - timedelta(hours=campaign.minimum_gap_hours)
        recent = set(
            MarketingDelivery.objects.filter(
                recipient_email__in=emails,
                status='sent',
                sent_at__gte=cutoff,
            ).values_list('recipient_email', flat=True)
        )
        recent.update(
            NewsletterDelivery.objects.filter(
                recipient_email__in=emails,
                status='sent',
                sent_at__gte=cutoff,
            ).values_list('recipient_email', flat=True)
        )
        recent.update(
            NewsletterSendLog.objects.filter(
                subscriber_email__in=emails,
                status='sent',
                sent_at__gte=cutoff,
            ).values_list('subscriber_email', flat=True)
        )
        recent = {normalize_email(email) for email in recent}

    now = timezone.now()
    rows = []
    for item in recipients:
        email = item['email']
        if email in suppressed:
            status = 'suppressed'
            error = 'Suppressed from marketing email.'
        elif email in recent:
            status = 'skipped'
            error = 'Skipped by campaign frequency cap.'
        else:
            status = 'pending'
            error = ''
        rows.append(MarketingDelivery(
            campaign=campaign,
            user_id=item['user_id'],
            recipient_email=email,
            recipient_name=item['name'],
            status=status,
            max_attempts=campaign.max_attempts,
            run_after=max(campaign.scheduled_for or now, now),
            last_error=error,
        ))

    if rows:
        MarketingDelivery.objects.bulk_create(rows, batch_size=1000, ignore_conflicts=True)

    campaign.prepared_at = now
    campaign.started_at = campaign.started_at or now
    campaign.status = 'sending' if rows else 'completed'
    campaign.total_recipients = campaign.deliveries.count()
    campaign.skipped_count = campaign.deliveries.filter(status__in=['skipped', 'suppressed']).count()
    if not rows:
        campaign.completed_at = now
    campaign.save(update_fields=[
        'prepared_at', 'started_at', 'status', 'total_recipients', 'skipped_count',
        'completed_at', 'updated_at',
    ])
    return campaign.total_recipients




def build_campaign_cta_url(campaign):
    """Add aggregate campaign UTM tags without attaching recipient identity."""
    if not campaign.cta_url:
        return ''
    parts = urlsplit(campaign.cta_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault('utm_source', 'chuosmart')
    query.setdefault('utm_medium', 'email')
    query.setdefault('utm_campaign', slugify(campaign.name)[:80] or f'campaign-{campaign.pk}')
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

def render_campaign_message(campaign, email, display_name='there', connection=None):
    unsubscribe_url = build_one_click_unsubscribe_url(email)
    context = {
        'campaign': campaign,
        'subject': campaign.subject,
        'preheader': campaign.preheader,
        'headline': campaign.headline,
        'body': campaign.body,
        'hero_image_url': campaign.hero_image_url,
        'cta_text': campaign.cta_text,
        'cta_url': build_campaign_cta_url(campaign),
        'display_name': display_name or 'there',
        'site_name': 'ChuoSmart',
        'site_url': get_site_root_url(),
        'business_address': getattr(settings, 'MARKETING_BUSINESS_ADDRESS', 'ChuoSmart, Tanzania'),
        'unsubscribe_url': unsubscribe_url,
    }
    html_message = render_to_string('emails/marketing/campaign.html', context)
    plain_message = strip_tags(html_message)
    message = EmailMultiAlternatives(
        campaign.subject,
        plain_message,
        marketing_from_email(),
        get_newsletter_delivery_emails(email),
        connection=connection,
        reply_to=[getattr(settings, 'MARKETING_REPLY_TO', '').strip()] if getattr(settings, 'MARKETING_REPLY_TO', '').strip() else None,
        headers={
            'List-Unsubscribe': f'<{unsubscribe_url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
            'List-ID': f'ChuoSmart Updates <{marketing_list_id()}>',
            'Precedence': 'bulk',
            'X-ChuoSmart-Campaign-ID': str(campaign.pk),
        },
    )
    message.attach_alternative(html_message, 'text/html')
    return message


def send_test_campaign(campaign, email, display_name='Team'):
    connection = get_marketing_connection(fail_silently=False)
    message = render_campaign_message(
        campaign, normalize_email(email), display_name=display_name, connection=connection
    )
    sent = message.send(fail_silently=False)
    if sent != 1:
        raise RuntimeError('Email backend did not confirm the marketing test send.')
    return sent


def send_delivery(delivery, connection=None):
    """Send one delivery after re-checking suppression and current consent."""
    email = normalize_email(delivery.recipient_email)
    if not is_marketing_allowed(email):
        delivery.status = 'suppressed'
        delivery.last_error = 'Recipient unsubscribed or is suppressed before send.'
        delivery.save(update_fields=['status', 'last_error', 'updated_at'])
        return False

    if was_recently_marketed(
        email, delivery.campaign.minimum_gap_hours, exclude_campaign_id=delivery.campaign_id
    ):
        delivery.status = 'skipped'
        delivery.last_error = 'Skipped by send-time marketing frequency cap.'
        delivery.save(update_fields=['status', 'last_error', 'updated_at'])
        return False

    message = render_campaign_message(
        delivery.campaign,
        email,
        display_name=delivery.recipient_name or 'there',
        connection=connection,
    )
    sent = message.send(fail_silently=False)
    if sent != 1:
        raise RuntimeError(f'Email backend reported {sent} deliveries for {email}')

    delivery.status = 'sent'
    delivery.sent_at = timezone.now()
    delivery.last_error = ''
    delivery.save(update_fields=['status', 'sent_at', 'last_error', 'updated_at'])
    return True


def refresh_campaign_stats(campaign_id):
    """Recalculate counters and complete campaigns when no retryable work remains."""
    with transaction.atomic():
        campaign = MarketingCampaign.objects.select_for_update().get(pk=campaign_id)
        counts = dict(
            campaign.deliveries.values('status').annotate(total=Count('id')).values_list('status', 'total')
        )
        campaign.total_recipients = sum(counts.values())
        campaign.sent_count = counts.get('sent', 0)
        campaign.failed_count = counts.get('failed', 0)
        campaign.skipped_count = counts.get('skipped', 0) + counts.get('suppressed', 0)

        retryable_failed = campaign.deliveries.filter(status='failed', attempts__lt=campaign.max_attempts).exists()
        active_work = campaign.deliveries.filter(status__in=['pending', 'sending']).exists() or retryable_failed
        if not active_work and campaign.status not in ('paused', 'cancelled', 'draft', 'scheduled'):
            campaign.status = 'completed'
            campaign.completed_at = campaign.completed_at or timezone.now()

        campaign.save(update_fields=[
            'total_recipients', 'sent_count', 'failed_count', 'skipped_count',
            'status', 'completed_at', 'updated_at',
        ])
        return campaign


def queue_due_campaigns(limit=10):
    """Move due campaigns into delivery, serializing broadcasts by default.

    Serial preparation is an important deliverability guard: frequency caps are
    evaluated after the previous broadcast has actually finished, instead of
    preparing several overlapping 6,000-recipient audiences at once.
    """
    if getattr(settings, 'MARKETING_SERIALIZE_CAMPAIGNS', True):
        if MarketingCampaign.objects.filter(status='sending').exists():
            return 0
        limit = 1
    now = timezone.now()
    ids = list(
        MarketingCampaign.objects.filter(
            Q(status='queued') | Q(status='scheduled', scheduled_for__lte=now)
        ).filter(
            prepared_at__isnull=True,
            last_test_sent_at__isnull=False,
        ).order_by('scheduled_for', 'created_at').values_list('id', flat=True)[:limit]
    )
    prepared = 0
    for campaign_id in ids:
        with transaction.atomic():
            campaign = MarketingCampaign.objects.select_for_update().get(pk=campaign_id)
            if campaign.prepared_at or campaign.status not in ('queued', 'scheduled'):
                continue
            prepare_campaign(campaign)
            prepared += 1
    return prepared
