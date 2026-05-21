"""Shared newsletter helpers for content announcement emails."""

import logging
import threading
import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator

User = get_user_model()
logger = logging.getLogger(__name__)

NEWSLETTER_CONFIRM_SALT = 'core.newsletter.confirmation'


def get_site_root_url():
    domain = getattr(settings, 'CANONICAL_DOMAIN', None) or getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
    return f'https://{domain}'.rstrip('/')


def build_absolute_url(path):
    return f'{get_site_root_url()}{path}'


def newsletter_debug_enabled():
    return bool(getattr(settings, 'NEWSLETTER_DEBUG', False))


def get_newsletter_delivery_emails(recipient_email):
    if newsletter_debug_enabled():
        test_email = getattr(settings, 'NEWSLETTER_TEST_EMAIL', '').strip()
        if not test_email:
            raise RuntimeError('NEWSLETTER_DEBUG is enabled but NEWSLETTER_TEST_EMAIL is not set.')
        return [test_email]

    return [recipient_email]


def get_newsletter_log_email():
    return getattr(settings, 'NEWSLETTER_LOG_EMAIL', '').strip()


def send_newsletter_log_email(subject, details):
    log_email = get_newsletter_log_email()
    if not log_email:
        return

    try:
        message = EmailMultiAlternatives(
            subject,
            details,
            settings.DEFAULT_FROM_EMAIL,
            [log_email],
        )
        message.send(fail_silently=True)
    except Exception:
        logger.exception('Failed to send newsletter log email')


def get_newsletter_recipients(exclude_user_id=None):
    recipients = User.objects.filter(
        is_active=True,
        email__isnull=False,
    ).exclude(email='').filter(newsletter_preference__newsletter=True).distinct()

    if exclude_user_id:
        recipients = recipients.exclude(pk=exclude_user_id)

    return recipients


def build_related_items(items):
    related_items = []
    for item in items:
        try:
            item_url = item.get_absolute_url()
        except Exception:
            item_url = '#'

        related_items.append({
            'title': getattr(item, 'title', str(item)),
            'url': build_absolute_url(item_url) if item_url != '#' else item_url,
            'summary': Truncator(strip_tags(getattr(item, 'summary', '') or getattr(item, 'description', '') or getattr(item, 'content', ''))).chars(120),
        })
    return related_items


def send_newsletter_email(recipient, subject, template_name, context):
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    delivery_emails = get_newsletter_delivery_emails(recipient.email)
    message = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, delivery_emails)
    message.attach_alternative(html_message, 'text/html')
    message.send(fail_silently=True)


def _send_content_newsletter_sync(instance, content_type, template_name, subject, related_items):
    owner = getattr(instance, 'user', None) or getattr(instance, 'author', None)
    owner_id = owner.id if owner and owner.pk else None
    recipients = get_newsletter_recipients(exclude_user_id=owner_id)

    if not recipients.exists():
        return 0

    detail_url = getattr(instance, 'get_absolute_url', lambda: '#')()
    absolute_detail_url = build_absolute_url(detail_url) if detail_url != '#' else '#'
    image_url = None
    for image_attr in ('image', 'thumbnail', 'media'):
        image_file = getattr(instance, image_attr, None)
        if image_file and getattr(image_file, 'url', None):
            image_url = build_absolute_url(image_file.url)
            break

    summary_source = (
        getattr(instance, 'summary', None)
        or getattr(instance, 'description', None)
        or getattr(instance, 'content', None)
        or ''
    )
    summary = Truncator(strip_tags(summary_source)).chars(180)

    sent_count = 0
    for recipient in recipients:
        context = {
            'recipient': recipient,
            'display_name': recipient.first_name or recipient.username,
            'content_type': content_type,
            'item': instance,
            'detail_url': absolute_detail_url,
            'image_url': image_url,
            'summary': summary,
            'related_items': build_related_items(related_items),
            'site_name': 'ChuoSmart',
            'site_url': get_site_root_url(),
        }
        try:
            send_newsletter_email(recipient, subject, template_name, context)
            sent_count += 1
        except RuntimeError as exc:
            logger.warning('Newsletter delivery skipped: %s', exc)

    return sent_count


def _queue_newsletter_log(instance, content_type, error):
    error_trace = traceback.format_exc()
    details = (
        f'Newsletter delivery failed for {content_type}\n\n'
        f'Object: {instance!r}\n'
        f'Error: {error}\n'
        f'Traceback:\n{error_trace}\n'
    )
    logger.error('Newsletter delivery failed for %s', content_type, exc_info=True)
    send_newsletter_log_email(f'Newsletter delivery failure: {content_type}', details)


def _run_content_newsletter_async(instance, content_type, template_name, subject, related_items):
    def worker():
        close_old_connections()
        try:
            _send_content_newsletter_sync(instance, content_type, template_name, subject, related_items)
        except Exception as exc:
            _queue_newsletter_log(instance, content_type, exc)
        finally:
            close_old_connections()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def send_blog_newsletter(blog, related_blogs):
    return _run_content_newsletter_async(
        blog,
        'blog post',
        'emails/newsletter/content_announcement.html',
        f'New blog post: {blog.title}',
        related_blogs,
    )


def send_product_newsletter(product, related_products):
    return _run_content_newsletter_async(
        product,
        'product listing',
        'emails/newsletter/content_announcement.html',
        f'New marketplace listing: {product.title}',
        related_products,
    )


def send_course_newsletter(course, related_courses):
    return _run_content_newsletter_async(
        course,
        'course',
        'emails/newsletter/content_announcement.html',
        f'New course available: {course.title}',
        related_courses,
    )


def send_talent_newsletter(talent, related_talents):
    return _run_content_newsletter_async(
        talent,
        'talent',
        'emails/newsletter/content_announcement.html',
        f'New talent featured: {talent.title}',
        related_talents,
    )


def build_newsletter_confirmation_token(user_id, action):
    return signing.dumps({'user_id': user_id, 'action': action}, salt=NEWSLETTER_CONFIRM_SALT)


def decode_newsletter_confirmation_token(token, max_age=60 * 60 * 24 * 3):
    return signing.loads(token, salt=NEWSLETTER_CONFIRM_SALT, max_age=max_age)


def send_unsubscribe_confirmation_email(user):
    confirmation_token = build_newsletter_confirmation_token(user.id, 'unsubscribe')
    confirmation_url = build_absolute_url(reverse('newsletter_confirm_unsubscribe', args=[confirmation_token]))
    context = {
        'recipient': user,
        'display_name': user.first_name or user.username,
        'confirmation_url': confirmation_url,
        'site_name': 'ChuoSmart',
        'site_url': get_site_root_url(),
    }
    send_newsletter_email(
        user,
        'Confirm your newsletter unsubscribe request',
        'emails/newsletter/unsubscribe_confirmation.html',
        context,
    )
    return confirmation_url