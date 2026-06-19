"""Shared newsletter helpers for content announcement emails."""

import logging
import threading
import traceback
import os
from collections import OrderedDict
from datetime import datetime, timedelta

from django.utils import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator

User = get_user_model()
logger = logging.getLogger(__name__)

NEWSLETTER_CONFIRM_SALT = 'core.newsletter.confirmation'

CATEGORY_CONFIG = OrderedDict([
    ('talents', {
        'label': 'Talents',
        'model_path': 'talents.models.Talent',
        'date_field': 'created_at',
        'title_field': 'title',
        'description_field': 'description',
        'image_field': 'media',
        'url_name': 'talent_detail',
        'url_kwarg': 'pk',
    }),
    ('jobs', {
        'label': 'Jobs',
        'model_path': 'jobs.models.Job',
        'date_field': 'posted_date',
        'title_field': 'title',
        'description_field': 'description',
        'image_field': None,
        'url_name': 'jobs:job_detail',
        'url_kwarg': 'job_id',
        'status_filter': {'is_active': True},
        'popularity_field': 'views_count',
    }),
    ('courses', {
        'label': 'Courses',
        'model_path': 'lms.models.models.Course',
        'date_field': 'created_at',
        'title_field': 'title',
        'description_field': 'summary',
        'image_field': 'image',
        'url_name': 'lms:course_detail',
        'url_kwarg': 'slug',
    }),
    ('blogs', {
        'label': 'Blogs',
        'model_path': 'core.models.Blog',
        'date_field': 'created_at',
        'title_field': 'title',
        'description_field': 'content',
        'image_field': 'thumbnail',
        'url_name': 'blog_detail',
        'url_kwarg': 'slug',
        'author_field': 'author',
    }),
    ('products', {
        'label': 'Products',
        'model_path': 'core.models.Product',
        'date_field': 'created_at',
        'title_field': 'title',
        'description_field': 'description',
        'image_field': 'image',
        'url_name': 'product-detail',
        'url_kwarg': 'slug',
    }),
])


def _get_model(config):
    from django.apps import apps

    module_path = config['model_path']
    parts = module_path.split('.')
    app_label = parts[0]
    model_name = parts[-1]

    model = apps.get_model(app_label, model_name)
    if model is not None:
        return model

    for model in apps.get_models():
        if model.__name__ == model_name:
            return model

    logger.error('Newsletter model not found: app=%s model=%s path=%s', app_label, model_name, module_path)
    return None


def _build_item_dict(item, config):
    """Build a dict of useful fields from a model instance for newsletter display."""
    d = {'id': item.pk, 'title': getattr(item, config['title_field'], str(item))}

    # Description/summary
    desc = getattr(item, config.get('description_field', ''), '')
    if not desc:
        desc = getattr(item, 'content', '') or getattr(item, 'requirements', '') or ''
    d['description'] = Truncator(strip_tags(str(desc))).chars(200) if desc else ''

    # Image
    image_field_name = config.get('image_field')
    if image_field_name:
        image_file = getattr(item, image_field_name, None)
        if image_file and getattr(image_file, 'url', None):
            d['image_url'] = build_absolute_url(image_file.url)
        else:
            d['image_url'] = None
    else:
        d['image_url'] = None

    # URL
    try:
        url = item.get_absolute_url()
        d['url'] = build_absolute_url(url)
    except Exception:
        try:
            url_kwarg_name = config.get('url_kwarg', 'pk')
            url_kwarg_value = getattr(item, url_kwarg_name, item.pk)
            d['url'] = build_absolute_url(reverse(config['url_name'], kwargs={url_kwarg_name: url_kwarg_value}))
        except Exception:
            d['url'] = '#'

    # Extra fields per category
    if config['label'] == 'Talents':
        d['category'] = getattr(item, 'category', '')
        d['location'] = getattr(item, 'location', '')
    elif config['label'] == 'Jobs':
        company = getattr(item, 'company', None)
        d['company'] = company.name if company else ''
        d['location'] = getattr(item, 'location', '')
        d['job_type'] = getattr(item, 'job_type', '')
        d['deadline'] = getattr(item, 'application_deadline', None)
    elif config['label'] == 'Courses':
        try:
            instructors_mgr = getattr(item, 'instructors', None)
            instructors = list(instructors_mgr.all()[:2]) if instructors_mgr is not None else []
        except Exception:
            instructors = []
        d['instructor'] = instructors[0].user.get_full_name() or instructors[0].user.username if instructors else ''
        d['price'] = str(getattr(item, 'price', '0.00'))
        d['is_free'] = getattr(item, 'is_free', True)
    elif config['label'] == 'Blogs':
        author = getattr(item, 'author', None)
        d['author'] = author.get_full_name() or author.username if author else ''
        d['published_date'] = getattr(item, 'created_at', None)
    elif config['label'] == 'Products':
        seller = getattr(item, 'user', None)
        d['seller'] = seller.get_full_name() or seller.username if seller else ''
        d['price'] = str(getattr(item, 'price', '0'))
        d['discount_price'] = str(getattr(item, 'discount_price', '')) if getattr(item, 'discount_price', None) else ''

    return d


def get_daily_digest_data(target_date=None, selected_categories=None):
    """Build digest data for the daily newsletter.

    Args:
        target_date: The date to check for new content (default: today).
        selected_categories: Optional list of category keys to include (for debug mode).
                            If None, only categories with new content today are included.

    Returns:
        dict with 'date', 'categories' (list of qualifying category dicts),
        'qualifying_categories' (list of category keys).
    """
    if target_date is None:
        target_date = timezone.now().date()

    digest = {
        'date': target_date,
        'categories': [],
        'qualifying_categories': [],
    }

    categories_to_check = selected_categories if selected_categories else list(CATEGORY_CONFIG.keys())

    for cat_key in categories_to_check:
        config = CATEGORY_CONFIG[cat_key]
        model = _get_model(config)
        date_field = config['date_field']

        if model is None or not date_field:
            continue

        # Base queryset
        qs = model.objects.all()

        # Published status filter
        status_filter = config.get('status_filter', {})
        if status_filter:
            qs = qs.filter(**status_filter)

        # New today
        day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        filter_kwargs = {f'{date_field}__gte': day_start, f'{date_field}__lt': day_end}
        new_today = list(qs.filter(**filter_kwargs).order_by(f'-{date_field}')[:10])

        # Most recent (up to 5)
        recent = list(qs.order_by(f'-{date_field}')[:5])

        # Most popular (up to 5)
        if config.get('popularity_field'):
            popular = list(qs.order_by(f'-{config["popularity_field"]}')[:5])
        elif cat_key == 'talents':
            popular = list(qs.annotate(popularity=Count('likes')).order_by('-popularity')[:5])
        else:
            popular = list(qs.order_by(f'-{date_field}')[:5])

        # Deduplicate: combine all items, preserve order, remove duplicates by pk
        seen = set()
        all_items = []
        for item in new_today + recent + popular:
            if item.pk not in seen:
                seen.add(item.pk)
                all_items.append(item)

        # Limit to 10 items total per section
        all_items = all_items[:10]

        if not all_items and selected_categories is None:
            continue

        items_data = [_build_item_dict(item, config) for item in all_items]

        # Tag items with their source labels
        new_today_ids = {item.pk for item in new_today}
        recent_ids = {item.pk for item in recent}
        for item_data in items_data:
            item_data['is_new_today'] = item_data['id'] in new_today_ids
            item_data['is_recent'] = item_data['id'] in recent_ids
            item_data['is_popular'] = item_data['id'] in {item.pk for item in popular}

        section = {
            'key': cat_key,
            'label': config['label'],
            'items': items_data,
            'has_new_today': len(new_today) > 0,
            'item_count': len(all_items),
        }

        if selected_categories is not None or len(new_today) > 0:
            digest['categories'].append(section)
            digest['qualifying_categories'].append(cat_key)

    return digest


def send_daily_digest(digest_data, subscriber_email, subscriber_name=''):
    """Send a daily digest email to a single subscriber.

    Returns True on success, False on failure.
    """
    from .models import NewsletterSendLog

    cat_count = len(digest_data['categories'])
    if cat_count == 0:
        return False

    # Determine subject
    if cat_count == 1:
        cat_label = digest_data['categories'][0]['label']
        subject = f'New {cat_label} on ChuoSmart'
    else:
        subject = "Today's ChuoSmart Updates"

    context = {
        'subject': subject,
        'site_name': 'ChuoSmart',
        'site_url': get_site_root_url(),
        'display_name': subscriber_name or 'there',
        'categories': digest_data['categories'],
        'has_talents': any(c['key'] == 'talents' for c in digest_data['categories']),
        'has_jobs': any(c['key'] == 'jobs' for c in digest_data['categories']),
        'has_courses': any(c['key'] == 'courses' for c in digest_data['categories']),
        'has_blogs': any(c['key'] == 'blogs' for c in digest_data['categories']),
        'has_products': any(c['key'] == 'products' for c in digest_data['categories']),
        'date': digest_data['date'],
    }

    try:
        html_message = render_to_string('emails/newsletter/daily_digest.html', context)
        plain_message = strip_tags(html_message)

        delivery_emails = get_newsletter_delivery_emails(subscriber_email)
        msg = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, delivery_emails)
        msg.attach_alternative(html_message, 'text/html')
        msg.send(fail_silently=True)

        # Log the send
        categories_str = ','.join(digest_data['qualifying_categories'])
        NewsletterSendLog.objects.create(
            subscriber_email=subscriber_email,
            sent_date=digest_data['date'],
            categories=categories_str,
            status='sent',
        )
        logger.info('Daily digest sent to %s (categories: %s)', subscriber_email, categories_str)
        return True
    except Exception as e:
        logger.error('Failed to send daily digest to %s: %s', subscriber_email, e)
        try:
            NewsletterSendLog.objects.create(
                subscriber_email=subscriber_email,
                sent_date=digest_data['date'],
                categories=','.join(digest_data['qualifying_categories']),
                status='failed',
            )
        except Exception:
            pass
        return False


def send_daily_digest_all_subscribers(target_date=None):
    """Send daily digest to all active subscribers.

    Returns dict with counts of sent, skipped, failed.
    """
    from .models import NewsletterSendLog, NewsletterSubscriber

    if target_date is None:
        target_date = timezone.now().date()

    # First check if there is any new content today
    digest_data = get_daily_digest_data(target_date=target_date)
    if not digest_data['categories']:
        logger.info('No new content today (%s) - no digest sent', target_date)
        return {'sent': 0, 'skipped': 0, 'failed': 0, 'reason': 'no_new_content'}

    # Get all active subscribers
    subscribers = NewsletterSubscriber.objects.filter(is_active=True)

    # Also get users with newsletter preference
    newsletter_users = get_newsletter_recipients()

    # Combine: use NewsletterSubscriber as primary, add newsletter users
    all_emails = set()
    for sub in subscribers:
        all_emails.add(sub.email.lower())
    for user in newsletter_users:
        if user.email:
            all_emails.add(user.email.lower())

    # Get already-sent for today
    already_sent = set(
        NewsletterSendLog.objects.filter(
            sent_date=target_date, status='sent'
        ).values_list('subscriber_email', flat=True)
    )
    already_sent = {e.lower() for e in already_sent}

    results = {'sent': 0, 'skipped': 0, 'failed': 0, 'already_sent': 0}
    for email in all_emails:
        if email.lower() in already_sent:
            results['already_sent'] += 1
            continue
        success = send_daily_digest(digest_data, email)
        if success:
            results['sent'] += 1
        else:
            results['failed'] += 1

    return results


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
    # Always write a local copy for diagnostics
    try:
        base_dir = getattr(settings, 'BASE_DIR', None) or os.getcwd()
        logs_dir = os.path.join(base_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, 'newsletter_failures.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{timezone.now().isoformat()} - {subject}\n")
            f.write(details + '\n\n')
    except Exception:
        logger.exception('Failed to write newsletter failure log file')

    # Try to email the log; don't swallow exceptions silently
    try:
        message = EmailMultiAlternatives(
            subject,
            details,
            settings.DEFAULT_FROM_EMAIL,
            [log_email],
        )
        message.send(fail_silently=False)
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
            'summary': Truncator(strip_tags(
                getattr(item, 'summary', '')
                or getattr(item, 'description', '')
                or getattr(item, 'content', '')
                or getattr(item, 'text_content', '')
                or getattr(item, 'requirements', '')
            )).chars(120),
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
        or getattr(instance, 'text_content', None)
        or getattr(instance, 'requirements', None)
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


def send_course_content_newsletter(content, related_contents):
    return _run_content_newsletter_async(
        content,
        'course lesson',
        'emails/newsletter/content_announcement.html',
        f'New lesson in {content.module.course.title}: {content.title}',
        related_contents,
    )


def send_job_newsletter(job, related_jobs):
    return _run_content_newsletter_async(
        job,
        'job post',
        'emails/newsletter/content_announcement.html',
        f'New job post: {job.title}',
        related_jobs,
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
