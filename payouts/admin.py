from django.contrib import admin
from .models import PayoutTransfer, PayoutWebhookReceipt, PayoutAuditEvent


class ImmutableAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)
    def has_delete_permission(self, request, obj=None):
        return False
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)


@admin.register(PayoutTransfer)
class PayoutTransferAdmin(ImmutableAdmin):
    list_display = ('payout_request_id', 'amount_tzs', 'status', 'recipient_masked', 'provider_reference', 'attempted_at')
    list_filter = ('status',)
    search_fields = ('payout_request_id', 'provider_reference')
    exclude = ('recipient_encrypted', 'recipient_fingerprint', 'idempotency_key')
    actions = None


@admin.register(PayoutAuditEvent)
class PayoutAuditEventAdmin(ImmutableAdmin):
    list_display = ('transfer', 'action', 'actor_user_id', 'reference', 'created_at')
    actions = None


@admin.register(PayoutWebhookReceipt)
class PayoutWebhookReceiptAdmin(ImmutableAdmin):
    list_display = ('event_id', 'event_type', 'provider_reference', 'processed', 'received_at')
    actions = None
