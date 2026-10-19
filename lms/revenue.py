from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum


MONEY = Decimal('0.01')


def instructor_share_percent():
    value = Decimal(str(getattr(settings, 'INSTRUCTOR_REVENUE_SHARE_PERCENT', '80')))
    if value < 0 or value > 100:
        raise ValueError('INSTRUCTOR_REVENUE_SHARE_PERCENT must be between 0 and 100')
    return value


def payout_threshold():
    value = Decimal(str(getattr(settings, 'INSTRUCTOR_PAYOUT_THRESHOLD_TZS', '100000')))
    if value < 0:
        raise ValueError('INSTRUCTOR_PAYOUT_THRESHOLD_TZS cannot be negative')
    return value.quantize(MONEY)


def _split_amount(gross_amount, percent):
    gross = Decimal(str(gross_amount)).quantize(MONEY)
    instructor_amount = (gross * percent / Decimal('100')).quantize(MONEY, rounding=ROUND_HALF_UP)
    platform_amount = gross - instructor_amount
    return gross, instructor_amount, platform_amount


def revenue_owner_for_course(course):
    if course.revenue_owner_id:
        return course.revenue_owner

    # Backward-safe fallback only when ownership is unambiguous. A legacy
    # multi-instructor course must have an explicit revenue_owner selected;
    # never guess who should receive money.
    instructors = list(course.instructors.order_by('id')[:2])
    if len(instructors) == 1:
        return instructors[0]
    return None


def recognize_payment_revenue(payment):
    """Create exactly one instructor earning for a completed course-related payment.

    The Snippe payment flow is not changed: this only records the accounting split.
    Replays/admin retries are idempotent because each source payment can appear once.
    """
    from .models import CoursePayment, ModulePayment, CertificatePayment, InstructorRevenue

    if payment.status != 'completed':
        return None

    if isinstance(payment, CoursePayment):
        course = payment.course
        if course.is_free or Decimal(str(payment.amount or 0)) <= 0:
            return None
        source_kwargs = {'course_payment': payment}
        module = None
    elif isinstance(payment, ModulePayment):
        module = payment.module
        course = module.course
        if course.is_free or Decimal(str(payment.amount or 0)) <= 0:
            return None
        source_kwargs = {'module_payment': payment}
    elif isinstance(payment, CertificatePayment):
        module = None
        course = payment.certificate.course
        # Certificate sales are revenue even when the underlying course is free.
        # Only the certificate payment itself must be a positive confirmed charge.
        if Decimal(str(payment.amount or 0)) <= 0:
            return None
        source_kwargs = {'certificate_payment': payment}
    else:
        raise TypeError('Unsupported payment type')

    owner = revenue_owner_for_course(course)
    if owner is None:
        # Do not invent a payee. Admin can assign a revenue owner and run backfill.
        return None

    percent = instructor_share_percent()
    gross, instructor_amount, platform_amount = _split_amount(payment.amount, percent)
    defaults = {
        'instructor': owner,
        'student': payment.user,
        'course': course,
        'module': module,
        'gross_amount': gross,
        'instructor_share_percent': percent,
        'instructor_amount': instructor_amount,
        'platform_amount': platform_amount,
    }
    revenue, _ = InstructorRevenue.objects.get_or_create(defaults=defaults, **source_kwargs)
    return revenue


def instructor_balance(instructor):
    from .models import InstructorRevenue
    return (
        InstructorRevenue.objects.filter(instructor=instructor, payout_request__isnull=True)
        .aggregate(total=Sum('instructor_amount'))['total']
        or Decimal('0.00')
    )


def create_payout_request(instructor):
    """Reserve eligible, distinct earning rows up to the single-payout cap."""
    from .models import InstructorRevenue, PayoutProfile, PayoutRequest

    threshold = payout_threshold()
    with transaction.atomic():
        profile = PayoutProfile.objects.select_for_update().filter(instructor=instructor).first()
        if not profile or not profile.is_complete:
            raise ValueError('Save a complete payout method before requesting a payout.')

        rows = list(
            InstructorRevenue.objects.select_for_update()
            .filter(instructor=instructor, payout_request__isnull=True)
            .order_by('earned_at', 'id')
        )
        # Reserve at most one authorized transfer's configured limit. The
        # legacy ledger attaches WHOLE earnings entries to a request, so select
        # a disjoint group without splitting / duplicating revenue rows.
        limit = Decimal(str(getattr(settings, 'INSTRUCTOR_PAYOUT_MAX_SINGLE_TZS', 500000)))
        if limit < threshold:
            raise ValueError('Instructor payout limit is below the payout threshold; contact support.')
        selected = []
        amount = Decimal('0.00')
        for row in rows:
            value = row.instructor_amount
            if value > 0 and amount + value <= limit:
                selected.append(row)
                amount += value
        amount = amount.quantize(MONEY)
        if amount < threshold:
            raise ValueError(
                f'At least TSh {threshold:,.0f} in earnings must fit within the per-payout limit. '
                'Contact support if an individual earning exceeds the limit.'
            )

        # Encrypt at rest when a Fernet key is configured. Live sending always
        # requires this key, including for pre-existing (legacy) requests.
        from payouts.service import encrypt_request_snapshot
        private_snapshot = encrypt_request_snapshot(profile.snapshot)
        payout = PayoutRequest.objects.create(
            instructor=instructor,
            amount=amount,
            payout_method=profile.payout_method,
            payout_details_snapshot=profile.masked_snapshot,
            payout_details_private=private_snapshot,
            status='pending',
        )
        InstructorRevenue.objects.filter(pk__in=[row.pk for row in selected]).update(payout_request=payout)
        transaction.on_commit(lambda: send_payout_request_alert(payout.pk))
        return payout


def send_payout_request_alert(payout_id):
    from .models import PayoutRequest

    payout = PayoutRequest.objects.select_related('instructor__user').get(pk=payout_id)
    recipients = list(getattr(settings, 'INSTRUCTOR_PAYOUT_ALERT_EMAILS', []))
    recipients = [str(email).strip() for email in recipients if str(email).strip()]
    if not recipients:
        return

    instructor_name = payout.instructor.display_legal_name or payout.instructor.user.get_full_name() or payout.instructor.user.username
    subject = f'ChuoSmart payout request #{payout.pk} — TSh {payout.amount:,.0f}'
    body = (
        f'Instructor: {instructor_name}\n'
        f'Email: {payout.instructor.user.email}\n'
        f'Amount requested: TSh {payout.amount:,.0f}\n'
        f'Payout method: {payout.get_payout_method_display()}\n'
        f'Payout details: {payout.payout_details_snapshot}\n'
        f'Request ID: {payout.pk}\n\n'
        'Review this request in the ChuoSmart Django admin under Instructor payout requests.'
    )
    import logging
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:
        # The payout remains safely visible in admin even if SMTP is temporarily down.
        logging.getLogger(__name__).exception('Failed to send payout alert for request %s', payout_id)


def set_payout_status(payout, new_status, admin_user=None, note=''):
    """Apply only human review transitions under lock; never mark money paid.

    Paid requires verified Snippe status via payouts.service.reconcile_transfer.
    This also fixes the legacy pre-lock status-check race.
    """
    from .models import InstructorRevenue
    from payouts.models import PayoutTransfer
    from django.utils import timezone

    allowed = {
        'pending': {'approved', 'rejected'},
        'approved': {'rejected'},
        'paid': set(),
        'rejected': set(),
    }
    if new_status == 'paid':
        raise ValueError('Only authenticated Snippe reconciliation may mark a payout paid.')
    with transaction.atomic():
        payout = type(payout).objects.select_for_update().get(pk=payout.pk)
        if new_status not in allowed.get(payout.status, set()):
            raise ValueError(f'Invalid payout transition {payout.status} -> {new_status}.')
        if new_status == 'rejected' and PayoutTransfer.objects.filter(payout_request_id=payout.pk).exists():
            raise ValueError('An authorized transfer cannot be rejected; escalate for controlled reconciliation.')
        payout.status = new_status
        payout.reviewed_by = admin_user
        payout.admin_note = note or payout.admin_note
        payout.reviewed_at = timezone.now()
        payout.save(update_fields=['status', 'reviewed_by', 'admin_note', 'reviewed_at', 'updated_at'])
        if new_status == 'rejected':
            InstructorRevenue.objects.filter(payout_request=payout).update(payout_request=None)
    return payout
