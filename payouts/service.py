"""Fail-closed Snippe instructor disbursement service.

Approval and beneficiary authorization require distinct privileged users. A
transfer can be submitted only ONCE; any ambiguous network result is quarantined
for reconciliation, never automatically retried. Live sending is OFF by default.
"""
import hashlib
import json
import logging
import re
import uuid
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from lms.models import (CoursePayment, ModulePayment, CertificatePayment,
                        InstructorRevenue, PayoutProfile, PayoutRequest, SnippeWebhookEvent)
from lms.revenue import payout_threshold
from .models import PayoutAuditEvent, PayoutControl, PayoutTransfer

LOG = logging.getLogger(__name__)
BANK_CODES = frozenset('ABSA ACCESS AKIBA AMANA AZANIA BANCABC BARODA BOA BOI CANARA CITI CRDB DASHENG DCB DTB ECOBANK EQUITY EXIM FNB HABIB ICB IMBANK KCB KILIMANJARO MAENDELEO MKOMBOZI MWALIMU MWANGA NBC NCBA NMB PBZ SCB SELCOMPESA STANBIC TCB UBA UCHUMI YETU'.split())


class PayoutSafetyError(ValueError):
    pass


def _whole_tzs(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
        raise PayoutSafetyError('Payout amount must be a positive whole TZS value.')
    return int(amount)


def _crypto():
    key = str(getattr(settings, 'SNIPPE_PAYOUT_ENCRYPTION_KEY', '') or '')
    if not key:
        raise PayoutSafetyError('Encrypted payout recipient storage is not configured.')
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeError) as exc:
        raise PayoutSafetyError('Invalid payout encryption key.') from exc


def _profile_recipient(profile):
    if not profile or not profile.is_complete:
        raise PayoutSafetyError('A complete payout account is required.')
    name = profile.account_name.strip()
    if not re.fullmatch(r'[^|\r\n\x00-\x1f]{2,150}', name):
        raise PayoutSafetyError('Invalid recipient name.')
    if profile.payout_method == 'mobile_money':
        phone = re.sub(r'[\s()\-]', '', profile.phone_number or '')
        if phone.startswith('+'):
            phone = phone[1:]
        if not re.fullmatch(r'255[67]\d{8}', phone):
            raise PayoutSafetyError('Mobile money phone must be a valid 255XXXXXXXXX number.')
        # The provider infers network from the number. Reject unknown network
        # labels rather than trusting arbitrary client-defined routing strings.
        network = re.sub(r'\s+', ' ', profile.mobile_network.strip()).lower()
        if network not in {'m-pesa', 'mpesa', 'vodacom', 'airtel', 'airtel money', 'mixx', 'mixx by yas', 'tigo', 'tigo pesa', 'halopesa', 'halotel'}:
            raise PayoutSafetyError('Unsupported mobile money network.')
        return {'channel': 'mobile', 'recipient_phone': phone, 'recipient_name': name}
    if profile.payout_method == 'bank':
        bank = profile.bank_name.strip().upper()
        account = re.sub(r'\s+', '', profile.bank_account_number or '')
        if (bank not in BANK_CODES and bank != 'GT BANK') or not re.fullmatch(r'[0-9A-Za-z]{5,32}', account):
            raise PayoutSafetyError('Invalid bank code or account number; use a supported Snippe bank code.')
        return {'channel': 'bank', 'recipient_bank': bank, 'recipient_account': account, 'recipient_name': name}
    raise PayoutSafetyError('Unknown payout method.')


def _recipient_fingerprint(recipient):
    return hashlib.sha256(json.dumps(recipient, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _ledger_checks(payout):
    amount = _whole_tzs(payout.amount)
    threshold = _whole_tzs(payout_threshold())
    if amount < threshold:
        raise PayoutSafetyError('Payout below instructor withdrawal minimum.')
    if amount > int(getattr(settings, 'INSTRUCTOR_PAYOUT_MAX_SINGLE_TZS', 500000)):
        raise PayoutSafetyError('Payout exceeds the configured per-transfer limit.')
    rows = list(InstructorRevenue.objects.filter(payout_request=payout).select_related(
        'course_payment', 'module_payment', 'certificate_payment'
    ))
    if not rows or sum((_whole_tzs(r.instructor_amount) for r in rows)) != amount:
        raise PayoutSafetyError('Reserved instructor earnings do not match requested amount.')
    oldest = timezone.now() - timedelta(days=int(getattr(settings, 'INSTRUCTOR_PAYOUT_SETTLEMENT_DAYS', 7)))
    for entry in rows:
        if entry.instructor_id != payout.instructor_id or entry.earned_at > oldest:
            raise PayoutSafetyError('Earnings are not settled or do not belong to the instructor.')
        sources = [p for p in (entry.course_payment, entry.module_payment, entry.certificate_payment) if p is not None]
        if len(sources) != 1 or sources[0].status != 'completed':
            raise PayoutSafetyError('Unconfirmed or reversed payment included in earnings.')
        source = sources[0]
        # An admin can manually mark a customer payment completed in the legacy
        # site. Never disburse that unverified revenue: demand evidence from an
        # authenticated, processed customer-payment webhook.
        if Decimal(str(source.amount)) != entry.gross_amount:
            raise PayoutSafetyError('Underlying payment differs from recognized gross revenue.')
        shared_reference_count = sum(model.objects.filter(
            snippe_reference=source.snippe_reference
        ).count() for model in (CoursePayment, ModulePayment, CertificatePayment))
        if shared_reference_count != 1:
            raise PayoutSafetyError('Collection reference reused across payment records.')
        if not source.snippe_reference or not source.webhook_event_id or not SnippeWebhookEvent.objects.filter(
            event_id=source.webhook_event_id, event_type='payment.completed',
            provider_reference=source.snippe_reference, status='processed',
        ).exists():
            raise PayoutSafetyError('Payment lacks signed, processed Snippe collection evidence.')
    return amount


def encrypt_request_snapshot(snapshot):
    """Encrypt newly reserved snapshots when key configured, without breaking old requests."""
    if not getattr(settings, 'SNIPPE_PAYOUT_ENCRYPTION_KEY', ''):
        if getattr(settings, 'INSTRUCTOR_DISBURSEMENTS_ENABLED', False):
            raise PayoutSafetyError('Encryption must be configured before enabling payout requests.')
        return snapshot  # legacy compatibility while disbursements are OFF
    return 'fernet:v1:' + _crypto().encrypt(snapshot.encode()).decode('ascii')


def _request_snapshot(private):
    if private.startswith('fernet:v1:'):
        try:
            return _crypto().decrypt(private[len('fernet:v1:'):].encode()).decode()
        except (InvalidToken, UnicodeError) as exc:
            raise PayoutSafetyError('Cannot decrypt payout request snapshot.') from exc
    return private  # pre-existing legacy rows only


def authorize_transfer(payout_id, authorized_by):
    """Second administrator verifies recipient (out of band) and authorizes payment.

    Must be run ONLY after a human verifies beneficiary account ownership. The
    associated approval step must already have been performed by another admin.
    """
    if not (authorized_by and authorized_by.is_active and authorized_by.is_superuser):
        raise PayoutSafetyError('Only a superuser can authorize outgoing transfers.')
    crypto = _crypto()
    with transaction.atomic():
        payout = PayoutRequest.objects.select_for_update().get(pk=payout_id)
        if payout.status != 'approved' or not payout.reviewed_by_id:
            raise PayoutSafetyError('Payout must first be approved by an administrator.')
        if getattr(settings, 'INSTRUCTOR_PAYOUT_REQUIRE_DUAL_CONTROL', True) and payout.reviewed_by_id == authorized_by.pk:
            raise PayoutSafetyError('A different administrator must authorize this transfer.')
        if PayoutTransfer.objects.filter(payout_request_id=payout.pk).exists():
            raise PayoutSafetyError('This payout has already been authorized; it cannot be re-authorized.')
        amount = _ledger_checks(payout)
        profile = PayoutProfile.objects.select_for_update().filter(instructor=payout.instructor).first()
        if not profile or profile.payout_method != payout.payout_method or profile.snapshot != _request_snapshot(payout.payout_details_private):
            raise PayoutSafetyError('Payout beneficiary changed since the withdrawal request; reject and request again.')
        recipient = _profile_recipient(profile)
        # PayoutRequest already freezes a (legacy) recipient snapshot at request
        # time. Outbound data is additionally encrypted and never exposed to admin.
        envelope = crypto.encrypt(json.dumps(recipient, sort_keys=True).encode()).decode('ascii')
        transfer = PayoutTransfer.objects.create(
            payout_request_id=payout.pk, amount_tzs=amount,
            channel=recipient['channel'], recipient_encrypted=envelope,
            recipient_fingerprint=_recipient_fingerprint(recipient),
            recipient_masked=payout.payout_details_snapshot[:220],
            idempotency_key=uuid.uuid4().hex[:30], authorized_by_id=authorized_by.pk,
        )
        PayoutAuditEvent.objects.create(transfer=transfer, action='authorized', actor_user_id=authorized_by.pk)
        return transfer


def _provider_config():
    if not getattr(settings, 'INSTRUCTOR_DISBURSEMENTS_ENABLED', False):
        raise PayoutSafetyError('Live disbursements are disabled.')
    key = getattr(settings, 'SNIPPE_PAYOUT_API_KEY', '')
    base = str(getattr(settings, 'SNIPPE_PAYOUT_BASE_URL', 'https://api.snippe.sh')).rstrip('/')
    webhook = str(getattr(settings, 'SNIPPE_PAYOUT_WEBHOOK_URL', '') or '')
    parsed = urlparse(base)
    if not key or parsed.scheme != 'https' or parsed.hostname not in {'api.snippe.sh'}:
        raise PayoutSafetyError('A restricted payout API key and trusted Snippe HTTPS API URL are required.')
    pwh = urlparse(webhook)
    if pwh.scheme != 'https' or not pwh.hostname or pwh.username or pwh.password or pwh.query or pwh.fragment:
        raise PayoutSafetyError('A public HTTPS payout webhook URL must be configured.')
    if not getattr(settings, 'SNIPPE_WEBHOOK_SECRET', ''):
        raise PayoutSafetyError('A webhook signing secret is required.')
    return base, key, webhook


def _extract_amount(data):
    amount = data.get('amount')
    if isinstance(amount, dict):
        if amount.get('currency') != 'TZS':
            raise PayoutSafetyError('Provider returned unexpected currency.')
        amount = amount.get('value')
    if amount is None or _whole_tzs(amount) <= 0:
        raise PayoutSafetyError('Provider amount is missing or invalid.')
    return _whole_tzs(amount)


def _verify_provider_payload(data, transfer, recipient):
    if _extract_amount(data) != transfer.amount_tzs:
        raise PayoutSafetyError('Provider payout amount does not match reserved earnings.')
    returned = data.get('recipient')
    if not isinstance(returned, dict):
        raise PayoutSafetyError('Provider response missing recipient verification.')
    if recipient['channel'] == 'mobile':
        if re.sub(r'\D', '', str(returned.get('phone', ''))) != recipient['recipient_phone']:
            raise PayoutSafetyError('Provider response recipient phone mismatch.')
    else:
        if str(returned.get('bank', '')).upper() != recipient['recipient_bank'] or str(returned.get('account', '')) != recipient['recipient_account']:
            raise PayoutSafetyError('Provider response bank recipient mismatch.')


def _provider_call(method, path, **kwargs):
    base, key, _ = _provider_config()
    url = base + path
    headers = {'Authorization': f'Bearer {key}', 'Accept': 'application/json'}
    headers.update(kwargs.pop('headers', {}))
    response = requests.request(method, url, headers=headers, timeout=(5, 15), allow_redirects=False, **kwargs)
    if response.status_code < 200 or response.status_code >= 300:
        response.raise_for_status()
        raise PayoutSafetyError('Unexpected Snippe HTTP response.')
    data = response.json()
    if not isinstance(data, dict) or data.get('status') != 'success' or not isinstance(data.get('data'), dict):
        raise PayoutSafetyError('Provider returned an invalid response.')
    return data['data']


def _audit(transfer, action, ref=''):
    PayoutAuditEvent.objects.create(transfer=transfer, action=action, reference=str(ref)[:120])


def dispatch_transfer(payout_id):
    """Dispatch one authorized transfer exactly once; never auto-retry a POST."""
    _provider_config()  # fail before any state is changed
    crypto = _crypto()
    with transaction.atomic():
        control, _ = PayoutControl.objects.get_or_create(pk=1)
        PayoutControl.objects.select_for_update().get(pk=control.pk)
        transfer = PayoutTransfer.objects.select_for_update().get(payout_request_id=payout_id)
        payout = PayoutRequest.objects.select_for_update().get(pk=payout_id)
        if transfer.status != 'ready' or payout.status != 'approved' or not payout.reviewed_by_id:
            raise PayoutSafetyError('Transfer is not ready or has already been attempted.')
        _ledger_checks(payout)
        if transfer.amount_tzs != _whole_tzs(payout.amount):
            raise PayoutSafetyError('Reserved payout amount has changed.')
        try:
            recipient = json.loads(crypto.decrypt(transfer.recipient_encrypted.encode()))
        except (InvalidToken, ValueError, UnicodeError) as exc:
            raise PayoutSafetyError('Recipient envelope cannot be decrypted.') from exc
        if _recipient_fingerprint(recipient) != transfer.recipient_fingerprint:
            raise PayoutSafetyError('Recipient envelope mismatch.')
        if getattr(settings, 'INSTRUCTOR_PAYOUT_REQUIRE_DUAL_CONTROL', True) and transfer.authorized_by_id == payout.reviewed_by_id:
            raise PayoutSafetyError('Independent approval is required.')
        start = timezone.now() - timedelta(hours=24)
        reserved = PayoutTransfer.objects.filter(attempted_at__gte=start, status__in=[
            'fee_check', 'sending', 'unknown', 'pending', 'completed', 'reversed',
        ]).exclude(pk=transfer.pk).aggregate(total=Sum('amount_tzs'))['total'] or 0
        if reserved + transfer.amount_tzs > int(getattr(settings, 'INSTRUCTOR_PAYOUT_MAX_DAILY_TZS', 1000000)):
            raise PayoutSafetyError('Payout daily platform limit reached.')
        transfer.status = 'fee_check'
        transfer.attempted_at = timezone.now()
        transfer.save(update_fields=['status', 'attempted_at', 'updated_at'])
        _audit(transfer, 'fee_check')

    try:
        fee = _provider_call('GET', '/v1/payouts/fee', params={'amount': transfer.amount_tzs})
        if str(fee.get('currency')) != 'TZS' or _whole_tzs(fee.get('amount')) != transfer.amount_tzs:
            raise PayoutSafetyError('Provider fee quote amount/currency mismatch.')
        fee_tzs = int(fee['fee_amount'])
        total_tzs = int(fee['total_amount'])
        if fee_tzs < 0 or total_tzs != transfer.amount_tzs + fee_tzs:
            raise PayoutSafetyError('Provider fee quote inconsistent.')
    except (requests.RequestException, ValueError, KeyError, TypeError, PayoutSafetyError):
        # GET-only failure is safe to retry. NO payout POST has happened.
        with transaction.atomic():
            transfer = PayoutTransfer.objects.select_for_update().get(pk=transfer.pk)
            if transfer.status == 'fee_check':
                transfer.status = 'ready'
                transfer.attempted_at = None
                transfer.last_error_code = 'fee_unavailable'
                transfer.save(update_fields=['status', 'attempted_at', 'last_error_code', 'updated_at'])
                _audit(transfer, 'fee_unavailable')
        raise PayoutSafetyError('Fee check failed; no payout was sent.')

    with transaction.atomic():
        transfer = PayoutTransfer.objects.select_for_update().get(pk=transfer.pk)
        payout = PayoutRequest.objects.select_for_update().get(pk=payout_id)
        if transfer.status != 'fee_check' or payout.status != 'approved':
            raise PayoutSafetyError('Payout was modified during fee verification.')
        transfer.status = 'sending'  # durable marker BEFORE any network POST
        transfer.fee_tzs = fee_tzs
        transfer.save(update_fields=['status', 'fee_tzs', 'updated_at'])
        _audit(transfer, 'send_started')

    body = dict(recipient, amount=transfer.amount_tzs, narration=f'ChuoSmart instructor payout #{payout_id}',
                webhook_url=_provider_config()[2], metadata={'payout_id': str(payout_id)})
    # The exact body and idempotency key are stable; but local records prohibit
    # another automatic POST even if the provider's 24-hour cache has expired.
    try:
        provider = _provider_call('POST', '/v1/payouts/send', json=body,
                                  headers={'Idempotency-Key': transfer.idempotency_key,
                                           'Content-Type': 'application/json'})
        reference = str(provider.get('reference') or '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,120}', reference):
            raise PayoutSafetyError('Provider returned no valid payout reference.')
        _verify_provider_payload(provider, transfer, recipient)
    except (requests.RequestException, PayoutSafetyError, ValueError, KeyError, TypeError):
        with transaction.atomic():
            transfer = PayoutTransfer.objects.select_for_update().get(pk=transfer.pk)
            if transfer.status == 'sending':
                transfer.status = 'unknown'
                transfer.last_error_code = 'unverified_post_result'
                transfer.save(update_fields=['status', 'last_error_code', 'updated_at'])
                _audit(transfer, 'unknown_send_result')
        raise PayoutSafetyError('Payout submission result is uncertain. RECONCILE; do not retry.')

    with transaction.atomic():
        transfer = PayoutTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.status != 'sending':
            raise PayoutSafetyError('Payout state changed while sending; manual investigation required.')
        transfer.provider_reference = reference
        transfer.status = 'pending'
        transfer.last_error_code = ''
        transfer.save(update_fields=['provider_reference', 'status', 'last_error_code', 'updated_at'])
        _audit(transfer, 'submitted', reference)
    return transfer


def reconcile_transfer(payout_id, *, expected_reference=None):
    """GET authoritative status. Only a verified completed status marks paid."""
    _provider_config()
    crypto = _crypto()
    transfer = PayoutTransfer.objects.get(payout_request_id=payout_id)
    if transfer.status in ('ready', 'fee_check', 'cancelled'):
        raise PayoutSafetyError('This payout has not been submitted to the provider.')
    if not transfer.provider_reference:
        raise PayoutSafetyError('No provider reference: reconcile the Snippe ledger manually; do not resend.')
    if expected_reference and expected_reference != transfer.provider_reference:
        raise PayoutSafetyError('Webhook payout reference does not match the recorded transfer.')
    try:
        recipient = json.loads(crypto.decrypt(transfer.recipient_encrypted.encode()))
    except (InvalidToken, ValueError, UnicodeError) as exc:
        raise PayoutSafetyError('Payout recipient cannot be decrypted.') from exc
    try:
        provider = _provider_call('GET', '/v1/payouts/' + transfer.provider_reference)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise PayoutSafetyError('Snippe status unavailable; funds remain reserved.') from exc
    if str(provider.get('reference')) != transfer.provider_reference:
        raise PayoutSafetyError('Provider reference mismatch.')
    _verify_provider_payload(provider, transfer, recipient)
    state = str(provider.get('status', '')).lower()
    if state not in {'pending', 'completed', 'failed', 'reversed'}:
        raise PayoutSafetyError('Unrecognized provider payout status.')
    with transaction.atomic():
        transfer = PayoutTransfer.objects.select_for_update().get(pk=transfer.pk)
        payout = PayoutRequest.objects.select_for_update().get(pk=payout_id)
        if transfer.provider_reference != provider.get('reference'):
            raise PayoutSafetyError('Provider reference changed during verification.')
        if transfer.status == 'completed' and state == 'pending':
            return transfer  # never regress completed funds
        if transfer.status in {'failed', 'cancelled'}:
            return transfer  # must not re-credit or resend
        if state == 'completed':
            if payout.status != 'approved' and payout.status != 'paid':
                raise PayoutSafetyError('Internal payout state mismatch: escalate.')
            if payout.status == 'approved':
                payout.status = 'paid'
                payout.paid_at = timezone.now()
                payout.save(update_fields=['status', 'paid_at', 'updated_at'])
            transfer.status = 'completed'
        elif state == 'failed':
            if payout.status != 'approved' or transfer.status == 'completed':
                raise PayoutSafetyError('Terminal failure conflicts with paid ledger.')
            # Release only after provider GET confirms terminal failure.
            payout.status = 'rejected'
            payout.admin_note = 'Snippe confirmed payout failure; funds released.'
            payout.save(update_fields=['status', 'admin_note', 'updated_at'])
            InstructorRevenue.objects.filter(payout_request=payout).update(payout_request=None)
            transfer.status = 'failed'
        elif state == 'reversed':
            transfer.status = 'reversed'  # keep instructor earnings unavailable pending investigation
        else:
            if transfer.status not in {'completed', 'reversed'}:
                transfer.status = 'pending'
        transfer.save(update_fields=['status', 'updated_at'])
        _audit(transfer, 'provider_' + state, transfer.provider_reference)
    return transfer
