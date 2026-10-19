"""Snippe payout webhook: authenticate before touching money, verify by API GET."""
import hashlib
import hmac
import json
import time

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PayoutTransfer, PayoutWebhookReceipt
from .service import PayoutSafetyError, reconcile_transfer


@csrf_exempt
@require_POST
def payout_webhook(request):
    secret = str(getattr(settings, 'SNIPPE_WEBHOOK_SECRET', '') or '')
    timestamp = request.headers.get('X-Webhook-Timestamp', '')
    signature = request.headers.get('X-Webhook-Signature', '')
    if not secret or not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 16:
        return HttpResponse(status=400)
    if not signature or len(signature) != 64:
        return HttpResponse(status=400)
    if abs(int(time.time()) - int(timestamp)) > 300:
        return HttpResponse(status=400)
    expected = hmac.new(secret.encode(), timestamp.encode() + b'.' + request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.lower()):
        return HttpResponse(status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError('Invalid payload')
        event_type = payload.get('type') or payload.get('event')
        if event_type not in ('payout.completed', 'payout.failed', 'payout.reversed'):
            return HttpResponse(status=200)
        event_data = payload.get('data', payload)
        if not isinstance(event_data, dict):
            return HttpResponse(status=400)
        reference = event_data.get('reference')
        if not isinstance(reference, str) or not reference or len(reference) > 120:
            return HttpResponse(status=400)
        event_id = str(payload.get('id') or '') or hashlib.sha256(request.body).hexdigest()
        if len(event_id) > 150:
            return HttpResponse(status=400)
    except (ValueError, TypeError, UnicodeDecodeError):
        return HttpResponse(status=400)
    try:
        receipt, _ = PayoutWebhookReceipt.objects.get_or_create(
            event_id=event_id,
            defaults={'provider_reference': reference, 'event_type': event_type},
        )
    except IntegrityError:
        receipt = PayoutWebhookReceipt.objects.get(event_id=event_id)
    if receipt.provider_reference != reference or receipt.event_type != event_type:
        return HttpResponse(status=409)
    if receipt.processed:
        return HttpResponse(status=200)
    transfer = PayoutTransfer.objects.filter(provider_reference=reference).first()
    if not transfer:
        # Some providers emit a webhook before POST /send returns. Retry later;
        # never create a payout or credit money from an unrecognised webhook.
        return HttpResponse(status=503)
    try:
        reconcile_transfer(transfer.payout_request_id, expected_reference=reference)
    except (PayoutSafetyError, ValueError, OSError, KeyError):
        # Respond non-2xx so Snippe retries; local periodic reconciliation is
        # also required if provider webhook retry attempts are exhausted.
        return HttpResponse(status=503)
    receipt.processed = True
    receipt.save(update_fields=['processed'])
    return HttpResponse(status=200)
