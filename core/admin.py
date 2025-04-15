from django.contrib import admin
from .models import Customer, Product, OrderPlaced, Cart, Banners, Blog, Subscription, SubscriptionPayment

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

