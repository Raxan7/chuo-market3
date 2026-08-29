# affiliates/admin.py
from django.contrib import admin
from .models import Affiliate, Referral, ClickTracking, PayoutRequest
from django.db import transaction
from django.utils import timezone

@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ('user', 'affiliate_code', 'status', 'balance', 'total_earnings', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'affiliate_code')
    readonly_fields = ('total_earnings', 'total_paid')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'affiliate_code', 'status')
        }),
        ('Financial Information', {
            'fields': ('balance', 'total_earnings', 'total_paid')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_details', 'phone_number')
        }),
    )

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'referred_user', 'referral_type', 'commission_earned', 'is_paid', 'created_at')
    list_filter = ('referral_type', 'is_paid', 'created_at')
    search_fields = ('affiliate__user__username', 'referred_user__username')
    readonly_fields = ('referral_id',)
    
    fieldsets = (
        ('Referral Information', {
            'fields': ('affiliate', 'referred_user', 'referral_id', 'referral_type')
        }),
        ('Content Information', {
            'fields': ('content_type', 'object_id')
        }),
        ('Financial Information', {
            'fields': ('purchase_amount', 'commission_earned', 'is_paid')
        }),
        ('Dates', {
            'fields': ('created_at', 'converted_at')
        }),
    )

@admin.register(ClickTracking)
class ClickTrackingAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'timestamp', 'ip_address', 'converted')
    list_filter = ('converted', 'timestamp')
    search_fields = ('affiliate__user__username', 'ip_address')

@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'amount', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at', 'processed_at')
    search_fields = ('affiliate__user__username',)
    actions = ['approve_payouts', 'mark_as_paid', 'reject_payouts']
    
    def approve_payouts(self, request, queryset):
        pending = queryset.filter(status=PayoutRequest.PayoutStatus.PENDING)
        count = pending.update(status=PayoutRequest.PayoutStatus.APPROVED)
        self.message_user(request, f"{count} pending payout requests have been approved.")
    approve_payouts.short_description = "Approve selected payout requests"
    
    def mark_as_paid(self, request, queryset):
        paid_count = 0
        with transaction.atomic():
            for payout in queryset.select_related('affiliate').select_for_update():
                if payout.status != PayoutRequest.PayoutStatus.APPROVED:
                    continue
                affiliate = Affiliate.objects.select_for_update().get(pk=payout.affiliate_id)
                if payout.amount > affiliate.balance:
                    self.message_user(
                        request,
                        f"Skipped payout #{payout.pk}: amount exceeds current affiliate balance.",
                        level='warning',
                    )
                    continue
                payout.status = PayoutRequest.PayoutStatus.PAID
                payout.processed_at = timezone.now()
                payout.save(update_fields=['status', 'processed_at'])
                affiliate.balance -= payout.amount
                affiliate.total_paid += payout.amount
                affiliate.save(update_fields=['balance', 'total_paid'])
                paid_count += 1
        self.message_user(request, f"{paid_count} payout requests have been marked as paid.")
    mark_as_paid.short_description = "Mark selected payout requests as paid"
    
    def reject_payouts(self, request, queryset):
        rejectable = queryset.exclude(status=PayoutRequest.PayoutStatus.PAID)
        count = rejectable.update(status=PayoutRequest.PayoutStatus.REJECTED)
        self.message_user(request, f"{count} payout requests have been rejected.")
    reject_payouts.short_description = "Reject selected payout requests"