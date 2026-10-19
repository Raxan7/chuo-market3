"""One-shot outbound disbursements. Separate from the legacy instructor ledger.

All money is in *integer* TZS. No client-supplied amount or recipient reaches Snippe.
"""
from django.db import models


class PayoutControl(models.Model):
    """Single row locked to enforce institution-wide caps across workers."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)


class PayoutTransfer(models.Model):
    STATUS = [(s, s) for s in (
        'ready', 'fee_check', 'sending', 'unknown', 'pending', 'completed',
        'failed', 'reversed', 'cancelled',
    )]
    # Existing LMS app deliberately has no migrations. An integer reference keeps
    # this new, independently migrated app deployable against that legacy schema.
    payout_request_id = models.PositiveBigIntegerField(unique=True, db_index=True)
    amount_tzs = models.PositiveBigIntegerField()
    channel = models.CharField(max_length=10)
    recipient_encrypted = models.TextField()  # Fernet; never display in admin
    recipient_fingerprint = models.CharField(max_length=64)
    recipient_masked = models.CharField(max_length=220)
    idempotency_key = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=15, choices=STATUS, default='ready')
    authorized_by_id = models.PositiveBigIntegerField()
    authorized_at = models.DateTimeField(auto_now_add=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    provider_reference = models.CharField(max_length=120, null=True, blank=True, unique=True)
    fee_tzs = models.PositiveBigIntegerField(null=True, blank=True)
    last_error_code = models.CharField(max_length=100, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'attempted_at'], name='payouts_pay_status_9caf91_idx')]

    def __str__(self):
        return f'Payout #{self.payout_request_id} ({self.status})'


class PayoutAuditEvent(models.Model):
    transfer = models.ForeignKey(PayoutTransfer, on_delete=models.PROTECT, related_name='events')
    action = models.CharField(max_length=70)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)


class PayoutWebhookReceipt(models.Model):
    event_id = models.CharField(max_length=150, unique=True)
    provider_reference = models.CharField(max_length=120, blank=True, default='')
    event_type = models.CharField(max_length=60)
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
