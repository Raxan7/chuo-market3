"""Content-to-marketing orchestration for ChuoSmart.

The content queue is intentionally two-stage:

1. ``NewsletterJob`` stores one durable row per published content object.
2. Due rows are grouped newest-first into a useful digest ``MarketingCampaign``.
3. Recipient delivery is handled separately by the throttled marketing worker.

Publishing content therefore never sends thousands of emails inside a web
request. New content moves to the front of the unsent inventory, historical
content is grouped instead of producing hundreds of individual broadcasts, and
all marketing consent/rate limits still apply at recipient send time.
"""

from datetime import datetime, timedelta
import logging

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import MarketingCampaign, NewsletterJob
from .newsletter import build_absolute_url

logger = logging.getLogger('core.email')

AUTO_CONTENT_PREFIX = '[AUTO-CONTENT:'
AUTO_DIGEST_PREFIX = '[AUTO-DIGEST:'

CONTENT_CONFIG = {
    'blog': {
        'app': 'core', 'model': 'Blog', 'date': 'created_at', 'kind': 'announcement',
        'subject': 'New on ChuoSmart: {title}', 'cta': 'Read the update',
    },
    'product': {
        'app': 'core', 'model': 'Product', 'date': 'created_at', 'kind': 'product',
        'subject': 'Fresh on the ChuoSmart marketplace: {title}', 'cta': 'View listing',
    },
    'course': {
        'app': 'lms', 'model': 'Course', 'date': 'created_at', 'kind': 'course',
        'subject': 'Build a new skill with ChuoSmart: {title}', 'cta': 'Explore course',
    },
    'course_content': {
        'app': 'lms', 'model': 'CourseContent', 'date': 'date_added', 'kind': 'course',
        'subject': 'New learning content on ChuoSmart: {title}', 'cta': 'Continue learning',
    },
    'job': {
        'app': 'jobs', 'model': 'Job', 'date': 'posted_date', 'kind': 'career',
        'subject': 'New opportunity on ChuoSmart: {title}', 'cta': 'View opportunity',
    },
    'material': {
        'app': 'materials', 'model': 'Material', 'date': 'created_at', 'kind': 'service',
        'subject': 'New useful resource on ChuoSmart: {title}', 'cta': 'Open resource',
    },
}

DIGEST_LABELS = {
    'job': 'Jobs & opportunities',
    'course': 'Courses',
    'course_content': 'Learning updates',
    'material': 'Resources',
    'blog': 'Updates',
    'product': 'Marketplace',
}


def _aware_floor():
    value = datetime(1970, 1, 1)
    if settings.USE_TZ:
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _model(job_type):
    config = CONTENT_CONFIG[job_type]
    return apps.get_model(config['app'], config['model'])


def content_marketing_types():
    types = ['blog', 'product', 'course', 'job', 'material']
    if getattr(settings, 'CONTENT_MARKETING_INCLUDE_COURSE_CONTENT', False):
        types.append('course_content')
    return tuple(types)


def digest_size():
    return max(1, min(int(getattr(settings, 'CONTENT_MARKETING_DIGEST_SIZE', 12)), 30))


def is_content_marketable(job_type, instance):
    if instance is None or job_type not in CONTENT_CONFIG:
        return False
    if job_type == 'job':
        return bool(getattr(instance, 'is_public', False)) and not instance.is_expired()
    if job_type == 'material':
        return bool(getattr(instance, 'is_active', False))
    if job_type == 'course_content':
        return bool(getattr(settings, 'CONTENT_MARKETING_INCLUDE_COURSE_CONTENT', False))
    return True


def get_content_instance(job_type, object_id):
    if job_type not in CONTENT_CONFIG:
        return None
    model = _model(job_type)
    if job_type == 'job':
        return model.public_queryset().filter(pk=object_id).first()
    if job_type == 'material':
        return model.objects.filter(pk=object_id, is_active=True).first()
    return model.objects.filter(pk=object_id).first()


def content_published_at(job_type, instance):
    config = CONTENT_CONFIG[job_type]
    value = getattr(instance, config['date'], None)
    return value or _aware_floor()


def _candidate_rows(job_type):
    model = _model(job_type)
    date_field = CONTENT_CONFIG[job_type]['date']
    if job_type == 'job':
        queryset = model.public_queryset().filter(application_deadline__gt=timezone.now())
    elif job_type == 'material':
        queryset = model.objects.filter(is_active=True)
    else:
        queryset = model.objects.all()
    return list(queryset.values_list('pk', date_field))


def discover_content_newest_first(include_types=None, limit=None):
    """Return eligible content identifiers sorted by publication date descending."""
    include_types = tuple(include_types or content_marketing_types())
    rows = []
    floor = _aware_floor()
    for job_type in include_types:
        if job_type not in CONTENT_CONFIG:
            continue
        for object_id, published_at in _candidate_rows(job_type):
            rows.append((published_at or floor, job_type, object_id))
    rows.sort(key=lambda value: (value[0], value[2]), reverse=True)
    if limit:
        rows = rows[:max(0, int(limit))]
    return rows


def sync_content_jobs(include_types=None, limit=None):
    """Backfill missing durable content jobs from the actual database.

    Already-processed content is never reset. This keeps reconciliation safe to
    run every minute while still discovering newly-published database rows.
    """
    if include_types is None and not getattr(settings, 'CONTENT_MARKETING_INCLUDE_COURSE_CONTENT', False):
        NewsletterJob.objects.filter(
            job_type='course_content', status__in=['pending', 'failed', 'processing']
        ).update(
            status='sent', processed_at=timezone.now(),
            last_error='Skipped: course lesson broadcasts are disabled by CONTENT_MARKETING_INCLUDE_COURSE_CONTENT.',
        )
    created = 0
    existing = 0
    for _, job_type, object_id in discover_content_newest_first(include_types=include_types, limit=limit):
        _, was_created = NewsletterJob.objects.get_or_create(
            job_type=job_type,
            object_id=object_id,
            defaults={'related_ids': [], 'status': 'pending', 'run_after': timezone.now()},
        )
        created += int(was_created)
        existing += int(not was_created)
    return {'created': created, 'existing': existing}


def _pending_content_jobs_newest_first():
    """Resolve queue rows to current objects so stale/private content is excluded."""
    result = []
    queryset = NewsletterJob.objects.filter(
        job_type__in=content_marketing_types(),
        status__in=['pending', 'failed'],
    ).order_by('id')
    for job in queryset.iterator(chunk_size=500):
        if job.attempts >= job.max_attempts:
            continue
        instance = get_content_instance(job.job_type, job.object_id)
        if not is_content_marketable(job.job_type, instance):
            job.status = 'sent'
            job.processed_at = timezone.now()
            job.last_error = 'Skipped: content is no longer eligible for public marketing.'
            job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])
            continue
        result.append((content_published_at(job.job_type, instance), job, instance))
    result.sort(key=lambda value: (value[0], value[1].pk), reverse=True)
    return result


def auto_content_campaigns():
    return MarketingCampaign.objects.filter(
        Q(name__startswith=AUTO_CONTENT_PREFIX) | Q(name__startswith=AUTO_DIGEST_PREFIX)
    )


def active_auto_content_campaign_exists():
    return auto_content_campaigns().filter(status__in=['scheduled', 'queued', 'sending', 'paused']).exists()


def rebalance_content_schedule(now=None):
    """Schedule unsent inventory in digest-sized batches, newest first.

    Every item is still durable in ``NewsletterJob``, but a batch shares one
    planned campaign slot. This prevents a 700-item backlog from turning into
    years of one-email-per-item broadcasts.
    """
    now = now or timezone.now()
    gap_hours = max(1, int(getattr(settings, 'CONTENT_MARKETING_CAMPAIGN_GAP_HOURS', 24)))
    gap = timedelta(hours=gap_hours)
    batch_size = digest_size()

    latest = auto_content_campaigns().exclude(status='cancelled').order_by('-scheduled_for', '-created_at').first()
    anchor = now
    if latest:
        reference = latest.scheduled_for or latest.created_at
        anchor = max(anchor, reference + gap)

    rows = _pending_content_jobs_newest_first()
    changed = 0
    for position, (_, job, _) in enumerate(rows):
        planned = anchor + (gap * (position // batch_size))
        if job.run_after != planned:
            job.run_after = planned
            job.save(update_fields=['run_after', 'updated_at'])
            changed += 1
    return {
        'scheduled': len(rows),
        'changed': changed,
        'anchor': anchor,
        'digest_size': batch_size,
        'campaign_slots': (len(rows) + batch_size - 1) // batch_size,
    }


def _image_url(instance):
    cloud_url = getattr(instance, 'thumbnail_cloudinary', '') or ''
    if cloud_url:
        return cloud_url
    for field_name in ('image', 'thumbnail', 'media'):
        value = getattr(instance, field_name, None)
        try:
            url = value.url if value else ''
        except Exception:
            url = ''
        if url:
            if str(url).startswith(('http://', 'https://')):
                return str(url)
            return build_absolute_url(str(url))
    return ''


def _detail_url(instance):
    try:
        path = instance.get_absolute_url()
    except Exception:
        return build_absolute_url('/')
    if str(path).startswith(('http://', 'https://')):
        return str(path)
    return build_absolute_url(str(path))


def _summary(instance):
    source = (
        getattr(instance, 'summary', '')
        or getattr(instance, 'description', '')
        or getattr(instance, 'content', '')
        or getattr(instance, 'text_content', '')
        or getattr(instance, 'requirements', '')
        or ''
    )
    return Truncator(strip_tags(str(source))).chars(520)


def _campaign_body(job_type, instance):
    summary = _summary(instance)
    extras = []
    if job_type == 'job':
        location = getattr(instance, 'location', '')
        deadline = getattr(instance, 'application_deadline', None)
        if location:
            extras.append(f'Location: {location}')
        if deadline:
            value = timezone.localtime(deadline) if timezone.is_aware(deadline) else deadline
            extras.append(f'Apply before: {value.strftime("%d %b %Y")}')
    elif job_type == 'course':
        if getattr(instance, 'is_free', False):
            extras.append('This course is currently available free on ChuoSmart.')
        elif getattr(instance, 'price', None) is not None:
            extras.append(f'Course price: TZS {instance.price}')
    elif job_type == 'product' and getattr(instance, 'price', None) is not None:
        extras.append(f'Listed price: TZS {instance.price}')

    intro = {
        'blog': 'A fresh ChuoSmart update is ready for you.',
        'product': 'A new marketplace listing has just been added.',
        'course': 'A new learning opportunity is available on ChuoSmart.',
        'course_content': 'Fresh learning content has been added.',
        'job': 'A new career opportunity is now available on ChuoSmart.',
        'material': 'A new resource has been added to ChuoSmart.',
    }[job_type]
    parts = [intro]
    if summary:
        parts.append(summary)
    if extras:
        parts.append('\n'.join(extras))
    return '\n\n'.join(parts)


def _auto_campaign_name(job):
    return f'{AUTO_CONTENT_PREFIX}{job.job_type}:{job.object_id}]'


def find_auto_campaign_for_job(job):
    marker = _auto_campaign_name(job)
    return MarketingCampaign.objects.filter(name__startswith=marker).order_by('id').first()


def materialize_job_as_campaign(job):
    """Backward-compatible single-content materializer used by older callers/tests."""
    instance = get_content_instance(job.job_type, job.object_id)
    if not is_content_marketable(job.job_type, instance):
        job.status = 'sent'
        job.processed_at = timezone.now()
        job.last_error = 'Skipped: content is no longer eligible for public marketing.'
        job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])
        return None

    existing = find_auto_campaign_for_job(job)
    if existing:
        job.status = 'sent'
        job.processed_at = timezone.now()
        job.last_error = f'Already represented by marketing campaign #{existing.pk}.'
        job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])
        return existing

    config = CONTENT_CONFIG[job.job_type]
    title = str(getattr(instance, 'title', instance))
    campaign_name = f'{_auto_campaign_name(job)} {title}'[:180]
    scheduled_for = max(job.run_after or timezone.now(), timezone.now())

    with transaction.atomic():
        campaign = MarketingCampaign.objects.create(
            name=campaign_name,
            kind=config['kind'],
            audience='all_opted_in',
            subject=config['subject'].format(title=title)[:255],
            preheader=f'Fresh {job.job_type.replace("_", " ")} content from ChuoSmart'[:255],
            headline=title[:255],
            body=_campaign_body(job.job_type, instance),
            hero_image_url=_image_url(instance),
            cta_text=config['cta'],
            cta_url=_detail_url(instance),
            status='queued' if scheduled_for <= timezone.now() else 'scheduled',
            scheduled_for=scheduled_for,
            minimum_gap_hours=max(1, int(getattr(settings, 'CONTENT_MARKETING_RECIPIENT_GAP_HOURS', 48))),
            max_attempts=max(1, int(getattr(settings, 'MARKETING_EMAIL_MAX_ATTEMPTS', 5))),
            last_test_sent_at=timezone.now(),
        )
        job.status = 'sent'
        job.processed_at = timezone.now()
        job.last_error = f'Queued as throttled marketing campaign #{campaign.pk}.'
        job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])
    return campaign


def due_content_jobs(limit=None):
    """Return the newest due batch of eligible content jobs."""
    if active_auto_content_campaign_exists():
        return []
    now = timezone.now()
    size = max(1, min(int(limit or digest_size()), 30))
    due = []
    for _, job, instance in _pending_content_jobs_newest_first():
        if job.run_after <= now:
            due.append((job, instance))
            if len(due) >= size:
                break
    return due


def due_content_job():
    """Backward-compatible single due job accessor."""
    rows = due_content_jobs(limit=1)
    return rows[0][0] if rows else None


def _digest_subject(entries):
    types = [job.job_type for job, _ in entries]
    count = len(entries)
    if types and all(value == 'job' for value in types):
        return f'{count} fresh opportunities on ChuoSmart'
    if types and all(value == 'course' for value in types):
        return f'{count} learning opportunities on ChuoSmart'
    if types and all(value == 'product' for value in types):
        return f'{count} fresh marketplace picks on ChuoSmart'
    return "What's new on ChuoSmart: opportunities, learning and resources"


def _digest_body(entries):
    grouped = {}
    for job, instance in entries:
        grouped.setdefault(job.job_type, []).append(instance)

    parts = [
        'Here are the newest useful things on ChuoSmart. We group updates into one digest so you get value without unnecessary email noise.'
    ]
    for job_type in ('job', 'course', 'material', 'blog', 'product', 'course_content'):
        instances = grouped.get(job_type) or []
        if not instances:
            continue
        lines = [DIGEST_LABELS[job_type]]
        for instance in instances:
            title = Truncator(str(getattr(instance, 'title', instance))).chars(110)
            lines.append(f'• {title}')
        parts.append('\n'.join(lines))
    parts.append('Open ChuoSmart to see the full details and the latest additions.')
    return '\n\n'.join(parts)


def materialize_jobs_as_digest(entries):
    """Convert a due content batch into one campaign and consume all rows atomically."""
    valid = []
    now = timezone.now()
    for job, instance in entries:
        if is_content_marketable(job.job_type, instance):
            valid.append((job, instance))
        else:
            job.status = 'sent'
            job.processed_at = now
            job.last_error = 'Skipped: content is no longer eligible for public marketing.'
            job.save(update_fields=['status', 'processed_at', 'last_error', 'updated_at'])

    if not valid:
        return None

    job_ids = [job.pk for job, _ in valid]
    first_id, last_id = max(job_ids), min(job_ids)
    marker = f'{AUTO_DIGEST_PREFIX}{first_id}-{last_id}:{len(valid)}]'
    existing = MarketingCampaign.objects.filter(name__startswith=marker).order_by('id').first()
    if existing:
        NewsletterJob.objects.filter(pk__in=job_ids).update(
            status='sent', processed_at=now,
            last_error=f'Already represented by marketing campaign #{existing.pk}.',
            updated_at=now,
        )
        return existing

    types = {job.job_type for job, _ in valid}
    kind = CONTENT_CONFIG[next(iter(types))]['kind'] if len(types) == 1 else 'announcement'
    newest_instance = valid[0][1]
    scheduled_for = max(min(job.run_after for job, _ in valid), now)
    subject = _digest_subject(valid)[:255]

    with transaction.atomic():
        campaign = MarketingCampaign.objects.create(
            name=f'{marker} {subject}'[:180],
            kind=kind,
            audience='all_opted_in',
            subject=subject,
            preheader=f'{len(valid)} fresh ChuoSmart updates in one useful digest'[:255],
            headline='Fresh opportunities and resources for you',
            body=_digest_body(valid),
            hero_image_url=_image_url(newest_instance),
            cta_text='Explore ChuoSmart',
            cta_url=build_absolute_url('/'),
            status='queued' if scheduled_for <= now else 'scheduled',
            scheduled_for=scheduled_for,
            minimum_gap_hours=max(1, int(getattr(settings, 'CONTENT_MARKETING_RECIPIENT_GAP_HOURS', 48))),
            max_attempts=max(1, int(getattr(settings, 'MARKETING_EMAIL_MAX_ATTEMPTS', 5))),
            last_test_sent_at=now,
        )
        NewsletterJob.objects.filter(pk__in=job_ids).update(
            status='sent',
            processed_at=now,
            last_error=f'Queued in digest marketing campaign #{campaign.pk}.',
            updated_at=now,
        )
    return campaign
