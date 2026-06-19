import logging
import traceback
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import strip_tags

email_logger = logging.getLogger('core.email')

from .forms import ComposeEmailForm
from .models import (
    AccountDeletionRequest, Banners, Blog, Cart, Customer, NewsletterSubscriber,
    OrderPlaced, Product, SentEmail, Subscription, SubscriptionPayment,
    UserNewsletterPreference,
)


class OrderPlacedAdmin(admin.ModelAdmin):
    list_display = ('user', 'customer', 'product', 'quantity', 'ordered_date', 'status')

admin.site.register(OrderPlaced, OrderPlacedAdmin)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Banners)
admin.site.register(Blog)
admin.site.register(Subscription)
admin.site.register(UserNewsletterPreference)


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


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'subject', 'sent_by', 'sent_at', 'status')
    list_filter = ('status', 'sent_at')
    search_fields = ('recipient_email', 'recipient_name', 'subject')
    readonly_fields = ('sent_at', 'sent_by', 'recipient_email', 'recipient_name', 'subject', 'body', 'status')
    date_hierarchy = 'sent_at'
    change_list_template = 'admin/core/sent_email/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('compose/', self.admin_site.admin_view(self.compose_email_view), name='core_sentemail_compose'),
        ]
        return custom_urls + urls

    def compose_email_view(self, request):
        timestamp = datetime.now(dt_timezone.utc).isoformat()
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        admin_user = request.user.get_username() if request.user.is_authenticated else 'anonymous'

        email_logger.info('=== Compose email view loaded [%s] by %s from %s ===', timestamp, admin_user, ip)

        form = ComposeEmailForm(request.POST or None)

        if request.method == 'POST':
            email_logger.info('POST received from %s — validating form', admin_user)
            if form.is_valid():
                recipient_email = form.cleaned_data['recipient_email']
                recipient_name = form.cleaned_data['recipient_name']
                subject = form.cleaned_data['subject']
                body = form.cleaned_data['body']
                cc_self = form.cleaned_data['cc_self']

                email_logger.info(
                    'Form valid — to="%s" name="%s" subject="%s" cc_self=%s body_length=%d',
                    recipient_email, recipient_name, subject, cc_self, len(body),
                )

                from_email = 'ChuoSmart <support@chuosmart.com>'
                plain_body = strip_tags(body)
                recipient_list = [recipient_email]
                if cc_self and request.user.email:
                    recipient_list.append(request.user.email)
                    email_logger.info('CC-ing sender at %s', request.user.email)

                smtp_settings = {
                    'host': getattr(settings, 'EMAIL_HOST', 'NOT SET'),
                    'port': getattr(settings, 'EMAIL_PORT', 'NOT SET'),
                    'user': getattr(settings, 'EMAIL_HOST_USER', 'NOT SET'),
                    'use_ssl': getattr(settings, 'EMAIL_USE_SSL', 'NOT SET'),
                    'backend': getattr(settings, 'EMAIL_BACKEND', 'NOT SET'),
                }
                email_logger.info('SMTP config: %s', smtp_settings)
                email_logger.info('Attempting send_mail to %s ...', recipient_list)

                send_start = datetime.now(dt_timezone.utc)
                try:
                    send_mail(
                        subject=subject,
                        message=plain_body,
                        from_email=from_email,
                        recipient_list=recipient_list,
                        html_message=body,
                        fail_silently=False,
                    )
                    send_end = datetime.now(dt_timezone.utc)
                    duration = (send_end - send_start).total_seconds()
                    email_logger.info(
                        'EMAIL SENT SUCCESSFULLY to %s — subject="%s" duration=%.2fs',
                        recipient_list, subject, duration,
                    )

                    SentEmail.objects.create(
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        subject=subject,
                        body=body,
                        sent_by=request.user,
                        status='sent',
                    )
                    email_logger.info('SentEmail record created (status=sent)')
                    self.message_user(request, f'Email sent successfully to {recipient_email}.')
                    return HttpResponseRedirect(reverse('admin:core_sentemail_changelist'))

                except BadHeaderError as e:
                    send_end = datetime.now(dt_timezone.utc)
                    duration = (send_end - send_start).total_seconds()
                    email_logger.error(
                        'BADHEADER ERROR — to=%s subject="%s" duration=%.2fs error=%s',
                        recipient_list, subject, duration, e,
                    )
                    SentEmail.objects.create(
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        subject=subject,
                        body=body,
                        sent_by=request.user,
                        status='failed',
                    )
                    email_logger.info('SentEmail record created (status=failed — BadHeaderError)')
                    self.message_user(request, f'Failed to send email: {e}', level='ERROR')

                except Exception as e:
                    send_end = datetime.now(dt_timezone.utc)
                    duration = (send_end - send_start).total_seconds()
                    tb = traceback.format_exc()
                    email_logger.error(
                        'EMAIL SEND FAILURE — to=%s subject="%s" duration=%.2fs\n'
                        '  Exception type: %s\n'
                        '  Exception args: %s\n'
                        '  Traceback:\n%s',
                        recipient_list, subject, duration,
                        type(e).__name__, e.args, tb,
                    )
                    SentEmail.objects.create(
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        subject=subject,
                        body=body,
                        sent_by=request.user,
                        status='failed',
                    )
                    email_logger.info('SentEmail record created (status=failed — %s)', type(e).__name__)
                    self.message_user(request, f'Failed to send email: {e}', level='ERROR')
            else:
                email_logger.warning(
                    'Form invalid — errors: %s, submitted data: %s',
                    dict(form.errors), form.cleaned_data if hasattr(form, 'cleaned_data') else 'N/A',
                )

        context = {
            'title': 'Compose Email',
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': True,
            'add': False,
            'change': False,
            'is_popup': False,
            'save_as': False,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'has_delete_permission': self.has_delete_permission(request),
            'has_editable_inline_admin_formsets': False,
        }
        email_logger.debug('Rendering compose email template')
        return TemplateResponse(request, 'admin/core/sent_email/compose_email.html', context)
