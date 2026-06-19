import logging
import socket
import traceback
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import strip_tags

email_logger = logging.getLogger('core.email')

from .forms import ComposeEmailForm, NewsletterDigestTestForm
from .models import (
    AccountDeletionRequest, Banners, Blog, Cart, Customer, NewsletterSubscriber,
    NewsletterSendLog, NewsletterTestSend,
    OrderPlaced, Product, SentEmail, Subscription, SubscriptionPayment,
    UserNewsletterPreference,
)
from .newsletter import get_daily_digest_data, get_site_root_url, send_daily_digest


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
admin.site.register(NewsletterSubscriber)


@admin.register(NewsletterSendLog)
class NewsletterSendLogAdmin(admin.ModelAdmin):
    list_display = ('subscriber_email', 'sent_date', 'categories', 'status', 'sent_at')
    list_filter = ('status', 'sent_date')
    search_fields = ('subscriber_email',)
    date_hierarchy = 'sent_date'


@admin.register(NewsletterTestSend)
class NewsletterTestSendAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'categories', 'sent_by', 'sent_at', 'status')
    list_filter = ('status', 'sent_at')
    search_fields = ('recipient_email',)
    readonly_fields = ('sent_at', 'sent_by', 'recipient_email', 'categories', 'status')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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
            path('newsletter-digest-test/', self.admin_site.admin_view(self.newsletter_digest_test_view), name='core_sentemail_newsletter_digest_test'),
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

                smtp_host = settings.EMAIL_HOST
                smtp_port = settings.EMAIL_PORT

                email_logger.info('SMTP config — host=%s port=%s user=%s use_ssl=%s timeout=%s',
                                  smtp_host, smtp_port, settings.EMAIL_HOST_USER,
                                  settings.EMAIL_USE_SSL, settings.EMAIL_TIMEOUT)

                # Phase 1: DNS resolution
                email_logger.info('PHASE 1 — DNS resolution of %s ...', smtp_host)
                try:
                    dns_start = datetime.now(dt_timezone.utc)
                    addrs = socket.getaddrinfo(smtp_host, smtp_port)
                    dns_duration = (datetime.now(dt_timezone.utc) - dns_start).total_seconds()
                    ips = sorted(set(addr[4][0] for addr in addrs))
                    email_logger.info('DNS OK — %s resolves to %s in %.2fs', smtp_host, ips, dns_duration)
                except Exception as e:
                    email_logger.error('DNS FAILED — %s: %s', smtp_host, e)

                # Build the email message (HTML with plain-text fallback)
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=from_email,
                    to=[recipient_email],
                    cc=[request.user.email] if cc_self and request.user.email else [],
                )
                msg.attach_alternative(body, 'text/html')

                # Phase 2-5: connect, auth, send, close — all via the SMTP backend
                backend = EmailBackend(
                    host=smtp_host,
                    port=smtp_port,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_ssl=settings.EMAIL_USE_SSL,
                    use_tls=settings.EMAIL_USE_TLS,
                    timeout=getattr(settings, 'EMAIL_TIMEOUT', 30),
                    fail_silently=False,
                )

                send_start = datetime.now(dt_timezone.utc)
                try:
                    # Phase 2 & 3: TCP connect + SSL handshake + SMTP login
                    email_logger.info('PHASE 2/3 — TCP connect + SSL handshake + login ...')
                    conn_start = datetime.now(dt_timezone.utc)
                    backend.open()
                    conn_duration = (datetime.now(dt_timezone.utc) - conn_start).total_seconds()
                    email_logger.info('CONNECTION OK — connected and authenticated in %.2fs', conn_duration)

                    # Phase 4: send
                    email_logger.info('PHASE 4 — sending message ...')
                    send_start_inner = datetime.now(dt_timezone.utc)
                    sent = backend.send_messages([msg])
                    send_duration = (datetime.now(dt_timezone.utc) - send_start_inner).total_seconds()
                    email_logger.info('SEND OK — message dispatched in %.2fs (result=%s)', send_duration, sent)

                    # Phase 5: close
                    email_logger.info('PHASE 5 — closing connection ...')
                    backend.close()
                    email_logger.info('CONNECTION CLOSED')

                    total_duration = (datetime.now(dt_timezone.utc) - send_start).total_seconds()
                    email_logger.info(
                        'EMAIL SENT SUCCESSFULLY — to=%s subject="%s" total_duration=%.2fs',
                        recipient_list, subject, total_duration,
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

                except (BadHeaderError, Exception) as e:
                    total_duration = (datetime.now(dt_timezone.utc) - send_start).total_seconds()
                    tb = traceback.format_exc()
                    exc_name = type(e).__name__
                    email_logger.error(
                        'EMAIL SEND FAILURE — to=%s subject="%s" total_duration=%.2fs\n'
                        '  Exception type: %s\n'
                        '  Exception args: %s\n'
                        '  Traceback:\n%s',
                        recipient_list, subject, total_duration,
                        exc_name, e.args, tb,
                    )
                    try:
                        backend.close()
                    except Exception:
                        pass
                    SentEmail.objects.create(
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        subject=subject,
                        body=body,
                        sent_by=request.user,
                        status='failed',
                    )
                    email_logger.info('SentEmail record created (status=failed — %s)', exc_name)
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

    def newsletter_digest_test_view(self, request):
        timestamp = datetime.now(dt_timezone.utc).isoformat()
        admin_user = request.user.get_username() if request.user.is_authenticated else 'anonymous'
        email_logger.info('=== Newsletter digest test view loaded [%s] by %s ===', timestamp, admin_user)

        initial_data = {}
        if request.method == 'GET':
            test_email = getattr(settings, 'NEWSLETTER_TEST_EMAIL', '')
            if test_email:
                initial_data['recipient_email'] = test_email
        form = NewsletterDigestTestForm(request.POST or None, initial=initial_data)
        preview_html = None

        if request.method == 'POST':
            email_logger.info('Newsletter digest test POST from %s', admin_user)
            if form.is_valid():
                selected_categories = form.cleaned_data['categories']
                recipient_email = form.cleaned_data['recipient_email']
                email_logger.info('Categories: %s, Recipient: %s', selected_categories, recipient_email)

                try:
                    # Build digest data using the selected categories
                    digest_data = get_daily_digest_data(selected_categories=selected_categories)
                except Exception as e:
                    email_logger.error('Error building digest data: %s', e, exc_info=True)
                    self.message_user(request, f'Error building digest data: {e}', level='ERROR')
                    return HttpResponseRedirect(reverse('admin:core_sentemail_newsletter_digest_test'))

                if not digest_data['categories']:
                    email_logger.warning('No content found for selected categories: %s', selected_categories)
                    self.message_user(request, 'No content found for the selected categories.', level='WARNING')
                    return HttpResponseRedirect(reverse('admin:core_sentemail_newsletter_digest_test'))

                if '_preview' in request.POST:
                    try:
                        cat_count = len(digest_data['categories'])
                        if cat_count == 1:
                            cat_label = digest_data['categories'][0]['label']
                            subject = f'[TEST] New {cat_label} on ChuoSmart'
                        else:
                            subject = "[TEST] Today's ChuoSmart Updates"

                        site_url = get_site_root_url()
                        context = {
                            'subject': subject,
                            'site_name': 'ChuoSmart',
                            'site_url': site_url,
                            'display_name': 'Admin',
                            'categories': digest_data['categories'],
                            'has_talents': any(c['key'] == 'talents' for c in digest_data['categories']),
                            'has_jobs': any(c['key'] == 'jobs' for c in digest_data['categories']),
                            'has_courses': any(c['key'] == 'courses' for c in digest_data['categories']),
                            'has_blogs': any(c['key'] == 'blogs' for c in digest_data['categories']),
                            'has_products': any(c['key'] == 'products' for c in digest_data['categories']),
                            'date': digest_data['date'],
                        }
                        from django.template.loader import render_to_string
                        preview_html = render_to_string('emails/newsletter/daily_digest.html', context)
                        self.message_user(request, 'Preview generated. Scroll down to see it.', level='INFO')
                    except Exception as e:
                        email_logger.error('Preview generation failed: %s', e, exc_info=True)
                        self.message_user(request, f'Preview failed: {e}', level='ERROR')

                elif '_send' in request.POST:
                    # Build context with test prefix
                    cat_count = len(digest_data['categories'])
                    if cat_count == 1:
                        cat_label = digest_data['categories'][0]['label']
                        subject = f'[TEST] New {cat_label} on ChuoSmart'
                    else:
                        subject = "[TEST] Today's ChuoSmart Updates"

                    from django.template.loader import render_to_string
                    from django.utils.html import strip_tags
                    from django.core.mail import EmailMultiAlternatives

                    site_url = get_site_root_url()

                    context = {
                        'subject': subject,
                        'site_name': 'ChuoSmart',
                        'site_url': site_url,
                        'display_name': 'Admin',
                        'categories': digest_data['categories'],
                        'has_talents': any(c['key'] == 'talents' for c in digest_data['categories']),
                        'has_jobs': any(c['key'] == 'jobs' for c in digest_data['categories']),
                        'has_courses': any(c['key'] == 'courses' for c in digest_data['categories']),
                        'has_blogs': any(c['key'] == 'blogs' for c in digest_data['categories']),
                        'has_products': any(c['key'] == 'products' for c in digest_data['categories']),
                        'date': digest_data['date'],
                    }

                    try:
                        html_message = render_to_string('emails/newsletter/daily_digest.html', context)
                        plain_message = strip_tags(html_message)

                        msg = EmailMultiAlternatives(
                            subject=subject,
                            body=plain_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[recipient_email],
                        )
                        msg.attach_alternative(html_message, 'text/html')
                        msg.send(fail_silently=False)

                        # Log the test send
                        NewsletterTestSend.objects.create(
                            recipient_email=recipient_email,
                            categories=','.join(selected_categories),
                            sent_by=request.user,
                            status='sent',
                        )

                        email_logger.info(
                            'Newsletter test digest sent to %s (categories: %s)',
                            recipient_email, selected_categories,
                        )
                        self.message_user(
                            request,
                            f'Test newsletter sent successfully to {recipient_email}.',
                            level='SUCCESS',
                        )
                        return HttpResponseRedirect(
                            reverse('admin:core_sentemail_newsletter_digest_test')
                        )

                    except Exception as e:
                        email_logger.error(
                            'Newsletter test digest failed for %s: %s',
                            recipient_email, e,
                        )
                        NewsletterTestSend.objects.create(
                            recipient_email=recipient_email,
                            categories=','.join(selected_categories),
                            sent_by=request.user,
                            status='failed',
                        )
                        self.message_user(
                            request,
                            f'Failed to send test email: {e}',
                            level='ERROR',
                        )
            else:
                email_logger.warning(
                    'Newsletter digest test form invalid: %s',
                    dict(form.errors),
                )

        context = {
            'title': 'Newsletter Digest Test',
            'form': form,
            'preview_html': preview_html,
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
        email_logger.debug('Rendering newsletter digest test template')
        return TemplateResponse(request, 'admin/core/sent_email/newsletter_digest_test.html', context)
