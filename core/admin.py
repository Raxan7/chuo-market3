from django.contrib import admin
from django.utils import timezone
from .models import Customer, Product, OrderPlaced, Cart, Banners, Blog, Subscription, SubscriptionPayment, AccountDeletionRequest

class OrderPlacedAdmin(admin.ModelAdmin):
    list_display = ('user', 'customer', 'product', 'quantity', 'ordered_date', 'status')

admin.site.register(OrderPlaced, OrderPlacedAdmin)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Banners)
admin.site.register(Blog)
admin.site.register(Subscription)

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'subscription', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['mark_as_verified', 'mark_as_rejected']

    def mark_as_verified(self, request, queryset):
        queryset.update(status='Verified')
    mark_as_verified.short_description = "Mark selected payments as Verified"

    def mark_as_rejected(self, request, queryset):
        queryset.update(status='Rejected')
    mark_as_rejected.short_description = "Mark selected payments as Rejected"


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'status',
        'user',
        'email',
        'requested_at',
        'reviewed_at',
        'reviewed_by',
    )
    list_filter = ('product', 'status', 'requested_at')
    search_fields = ('email', 'full_name', 'phone_number', 'user__username', 'user__email')
    readonly_fields = ('requested_at',)
    actions = ['mark_in_review', 'mark_completed', 'mark_rejected']

    def _mark_status(self, request, queryset, status):
        queryset.update(status=status, reviewed_by=request.user, reviewed_at=timezone.now())

    def mark_in_review(self, request, queryset):
        self._mark_status(request, queryset, 'in_review')
    mark_in_review.short_description = 'Mark selected requests as In Review'

    def mark_completed(self, request, queryset):
        self._mark_status(request, queryset, 'completed')
    mark_completed.short_description = 'Mark selected requests as Completed'

    def mark_rejected(self, request, queryset):
        self._mark_status(request, queryset, 'rejected')
    mark_rejected.short_description = 'Mark selected requests as Rejected'

