from unittest import mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone


class CorePageSmokeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/home.html')

    def test_search_page_loads(self):
        response = self.client.get(reverse('search'), {'q': 'django'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/global_search.html')

    def test_dashboard_loads_for_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('user_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/dashboard.html')

    def test_dashboard_shows_materials_tab(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('user_dashboard'))
        self.assertContains(response, 'My Materials')


class SecurityRegressionTests(TestCase):
    def setUp(self):
        from core.models import Product

        self.user = User.objects.create_user(
            username='buyer', email='buyer@example.com', password='password12345'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='password12345'
        )
        # Product.save() generates a WebP derivative. The regression tests do
        # not need filesystem image processing, so isolate that side effect.
        with mock.patch('core.image_utils.optimize_image', return_value=None):
            self.product = Product.objects.create(
                user=self.other,
                title='Test product',
                category='El',
                description='Test',
                price=1000,
                image='product_images/test.jpg',
            )
        self.client.login(username='buyer', password='password12345')

    def test_newsletter_is_opt_in_by_default(self):
        self.assertFalse(self.user.newsletter_preference.newsletter)

    def test_add_to_cart_rejects_get(self):
        response = self.client.get(reverse('add-to-cart'), {'product_id': self.product.pk})
        self.assertEqual(response.status_code, 405)

    def test_order_cannot_use_another_users_customer_profile(self):
        response = self.client.post(reverse('order_placed'), {
            'customer_id': self.other.customer.pk,
            'product_id': self.product.pk,
            'quantity': 1,
        })
        self.assertEqual(response.status_code, 404)

    def test_non_staff_cannot_target_another_user_notification(self):
        response = self.client.post(
            reverse('send_notification_to_user', kwargs={'user_id': self.other.pk}),
            {'head': 'Nope', 'body': 'Nope'},
        )
        self.assertEqual(response.status_code, 403)


class PasswordResetEmailRegressionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reset-user', email='reset@example.com', password='password12345'
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_uses_project_email_template_and_sends(self):
        from django.core import mail
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset/', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.user.email])


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    MARKETING_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    NEWSLETTER_DEBUG=False,
    CANONICAL_DOMAIN='testserver',
)
class MarketingEngineRegressionTests(TestCase):
    def setUp(self):
        from core.models import NewsletterSubscriber, UserNewsletterPreference

        self.opted_in = User.objects.create_user(
            username='market-user', email='market@example.com', password='password12345'
        )
        UserNewsletterPreference.objects.update_or_create(
            user=self.opted_in, defaults={'newsletter': True}
        )
        self.opted_out = User.objects.create_user(
            username='no-market-user', email='no-market@example.com', password='password12345'
        )
        UserNewsletterPreference.objects.update_or_create(
            user=self.opted_out, defaults={'newsletter': False}
        )
        NewsletterSubscriber.objects.create(
            email='subscriber@example.com', name='Subscriber', source='test', is_active=True
        )

    def _campaign(self, **overrides):
        from core.models import MarketingCampaign

        data = {
            'name': 'September launch',
            'kind': 'promotion',
            'audience': 'all_opted_in',
            'subject': 'Something useful from ChuoSmart',
            'preheader': 'A short update for the ChuoSmart community',
            'headline': 'A better way to move from campus to opportunity',
            'body': 'Explore new opportunities, courses and services available on ChuoSmart.',
            'cta_text': 'Open ChuoSmart',
            'cta_url': 'https://chuosmart.com/',
            'status': 'queued',
            'last_test_sent_at': timezone.now(),
            'minimum_gap_hours': 0,
        }
        data.update(overrides)
        return MarketingCampaign.objects.create(**data)

    def test_prepare_campaign_uses_opt_in_contacts_and_suppression(self):
        from core.marketing import prepare_campaign, suppress_email
        from core.models import MarketingDelivery

        suppress_email('subscriber@example.com', source='test')
        campaign = self._campaign()
        prepare_campaign(campaign)

        deliveries = {d.recipient_email: d.status for d in MarketingDelivery.objects.filter(campaign=campaign)}
        self.assertEqual(deliveries['market@example.com'], 'pending')
        self.assertEqual(deliveries['subscriber@example.com'], 'suppressed')
        self.assertNotIn('no-market@example.com', deliveries)

    def test_delivery_rechecks_consent_after_queueing(self):
        from django.core import mail
        from core.marketing import prepare_campaign, send_delivery, suppress_email

        campaign = self._campaign(audience='registered_users')
        prepare_campaign(campaign)
        delivery = campaign.deliveries.get(recipient_email='market@example.com')
        suppress_email('market@example.com', source='test-after-queue')

        self.assertFalse(send_delivery(delivery))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, 'suppressed')
        self.assertEqual(len(mail.outbox), 0)

    def test_frequency_cap_skips_recent_marketing_recipient(self):
        from core.marketing import prepare_campaign
        from core.models import MarketingDelivery
        from django.utils import timezone

        old_campaign = self._campaign(name='Earlier campaign', audience='registered_users')
        MarketingDelivery.objects.create(
            campaign=old_campaign,
            user=self.opted_in,
            recipient_email=self.opted_in.email,
            recipient_name='Market',
            status='sent',
            sent_at=timezone.now(),
        )
        new_campaign = self._campaign(
            name='Too soon', audience='registered_users', minimum_gap_hours=24
        )
        prepare_campaign(new_campaign)
        delivery = new_campaign.deliveries.get(recipient_email='market@example.com')
        self.assertEqual(delivery.status, 'skipped')

    def test_worker_sends_queued_campaign_and_marks_complete(self):
        from django.core import mail
        from django.core.management import call_command

        campaign = self._campaign(audience='registered_users')
        call_command('process_marketing_queue', limit=10, campaign_limit=5)

        campaign.refresh_from_db()
        delivery = campaign.deliveries.get(recipient_email='market@example.com')
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(campaign.status, 'completed')
        self.assertEqual(campaign.sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('List-Unsubscribe', mail.outbox[0].extra_headers)
        self.assertIn('Open ChuoSmart', mail.outbox[0].alternatives[0].content)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    NEWSLETTER_DEBUG=False,
    CANONICAL_DOMAIN='testserver',
    CONTENT_MARKETING_CAMPAIGN_GAP_HOURS=48,
    CONTENT_MARKETING_RECIPIENT_GAP_HOURS=48,
    CONTENT_MARKETING_DIGEST_SIZE=12,
    CONTENT_MARKETING_INCLUDE_COURSE_CONTENT=False,
)
class ContentMarketingOrchestrationTests(TestCase):
    def setUp(self):
        from core.models import UserNewsletterPreference

        self.author = User.objects.create_user(
            username='content-author', email='author@example.com', password='password12345'
        )
        self.recipient = User.objects.create_user(
            username='content-reader', email='reader@example.com', password='password12345'
        )
        UserNewsletterPreference.objects.update_or_create(
            user=self.recipient, defaults={'newsletter': True}
        )

    def _blogs(self):
        from datetime import timedelta
        from core.models import Blog

        older = Blog.objects.create(title='Older useful post', content='Older body', author=self.author)
        newer = Blog.objects.create(title='Newest useful post', content='Newest body', author=self.author)
        Blog.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(days=10))
        Blog.objects.filter(pk=newer.pk).update(created_at=timezone.now() - timedelta(hours=1))
        older.refresh_from_db()
        newer.refresh_from_db()
        return older, newer

    @override_settings(CONTENT_MARKETING_DIGEST_SIZE=1)
    def test_database_backfill_schedules_newest_content_first(self):
        from core.content_marketing import rebalance_content_schedule, sync_content_jobs
        from core.models import NewsletterJob

        older, newer = self._blogs()
        sync_content_jobs(include_types=['blog'])
        rebalance_content_schedule()

        older_job = NewsletterJob.objects.get(job_type='blog', object_id=older.pk)
        newer_job = NewsletterJob.objects.get(job_type='blog', object_id=newer.pk)
        self.assertLess(newer_job.run_after, older_job.run_after)

    def test_content_worker_creates_campaign_without_bulk_smtp_send(self):
        from django.core import mail
        from django.core.management import call_command
        from core.content_marketing import sync_content_jobs
        from core.models import MarketingCampaign

        _, newer = self._blogs()
        sync_content_jobs(include_types=['blog'])
        call_command('process_newsletter_queue', limit=1, reconcile_limit=50)

        campaign = MarketingCampaign.objects.get(name__startswith='[AUTO-DIGEST:')
        self.assertIn(campaign.status, {'queued', 'scheduled'})
        self.assertIn('Newest useful post', campaign.body)
        self.assertIn('Older useful post', campaign.body)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    MARKETING_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    NEWSLETTER_DEBUG=False,
    CANONICAL_DOMAIN='testserver',
    MARKETING_EMAIL_BURST_CAP=1,
    MARKETING_EMAIL_TEN_MINUTE_CAP=15,
    MARKETING_EMAIL_HOURLY_CAP=100,
    MARKETING_EMAIL_DAILY_CAP=1500,
    MARKETING_EMAIL_SECONDS_BETWEEN_SENDS=0,
)
class MarketingDeliverabilityGuardTests(TestCase):
    def setUp(self):
        from core.models import UserNewsletterPreference

        self.users = []
        for index in range(2):
            user = User.objects.create_user(
                username=f'warm-{index}', email=f'warm-{index}@example.com', password='password12345'
            )
            UserNewsletterPreference.objects.update_or_create(
                user=user, defaults={'newsletter': True}
            )
            self.users.append(user)

    def _campaign(self, name='Warm campaign', gap=0):
        from core.models import MarketingCampaign
        return MarketingCampaign.objects.create(
            name=name,
            kind='announcement',
            audience='registered_users',
            subject='Useful ChuoSmart update',
            preheader='A useful update',
            headline='Something useful for you',
            body='This is a useful and relevant ChuoSmart update.',
            cta_text='Open ChuoSmart',
            cta_url='https://chuosmart.com/',
            status='queued',
            last_test_sent_at=timezone.now(),
            minimum_gap_hours=gap,
        )

    def test_worker_enforces_burst_cap_even_when_cli_limit_is_higher(self):
        from django.core import mail
        from django.core.management import call_command
        from core.models import MarketingDelivery

        campaign = self._campaign()
        call_command('process_marketing_queue', limit=10, campaign_limit=5)

        self.assertEqual(MarketingDelivery.objects.filter(campaign=campaign, status='sent').count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_time_frequency_cap_stops_stale_queued_delivery(self):
        from django.core import mail
        from core.marketing import prepare_campaign, send_delivery
        from core.models import MarketingDelivery

        campaign = self._campaign(name='Prepared first', gap=24)
        prepare_campaign(campaign)
        delivery = campaign.deliveries.get(recipient_email=self.users[0].email)

        other = self._campaign(name='Intervening campaign', gap=0)
        MarketingDelivery.objects.create(
            campaign=other,
            user=self.users[0],
            recipient_email=self.users[0].email,
            status='sent',
            sent_at=timezone.now(),
        )

        self.assertFalse(send_delivery(delivery))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, 'skipped')
        self.assertEqual(len(mail.outbox), 0)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    MARKETING_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    NEWSLETTER_DEBUG=False,
    CANONICAL_DOMAIN='testserver',
    CONTENT_MARKETING_DIGEST_SIZE=12,
    CONTENT_MARKETING_CAMPAIGN_GAP_HOURS=24,
    CONTENT_MARKETING_RECIPIENT_GAP_HOURS=48,
    MARKETING_EMAIL_BURST_CAP=3,
    MARKETING_EMAIL_TEN_MINUTE_CAP=15,
    MARKETING_EMAIL_HOURLY_CAP=100,
    MARKETING_EMAIL_DAILY_CAP=1500,
    MARKETING_EMAIL_SECONDS_BETWEEN_SENDS=0,
)
class MarketingAutomationRecoveryTests(TestCase):
    def setUp(self):
        from core.models import UserNewsletterPreference

        self.author = User.objects.create_user(
            username='auto-author', email='auto-author@example.com', password='password12345'
        )
        self.recipient = User.objects.create_user(
            username='auto-recipient', email='auto-recipient@example.com', password='password12345'
        )
        UserNewsletterPreference.objects.update_or_create(
            user=self.recipient, defaults={'newsletter': True}
        )

    def test_generic_550_is_policy_not_hard_bounce(self):
        from core.marketing import classify_smtp_refusal_data
        self.assertEqual(
            classify_smtp_refusal_data([550], ['Message rejected by outbound policy']),
            'policy',
        )

    def test_explicit_missing_mailbox_is_hard_bounce(self):
        from core.marketing import classify_smtp_refusal_data
        self.assertEqual(
            classify_smtp_refusal_data([550], ['5.1.1 The email account that you tried to reach does not exist']),
            'hard_bounce',
        )

    def test_unified_engine_creates_digest_and_sends(self):
        from django.core import mail
        from django.core.management import call_command
        from core.models import Blog, MarketingCampaign, MarketingDelivery

        Blog.objects.create(title='Automated useful update', content='Useful content', author=self.author)
        call_command('run_email_marketing_engine', send_limit=10, digest_size=12, reconcile_limit=250)

        campaign = MarketingCampaign.objects.get(name__startswith='[AUTO-DIGEST:')
        delivery = MarketingDelivery.objects.get(campaign=campaign, recipient_email=self.recipient.email)
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(campaign.sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MARKETING_EMAIL_POLICY_FAILURE_CIRCUIT_BREAKER=3)
    def test_worker_does_not_suppress_generic_550_policy_rejection(self):
        import smtplib
        from django.core.management import call_command
        from core.marketing import prepare_campaign
        from core.models import MarketingCampaign, MarketingSuppression

        campaign = MarketingCampaign.objects.create(
            name='Policy refusal test', kind='announcement', audience='registered_users',
            subject='Test', headline='Test', body='Test', status='queued',
            last_test_sent_at=timezone.now(), minimum_gap_hours=0,
        )
        prepare_campaign(campaign)

        fake_message = mock.Mock()
        fake_message.send.side_effect = smtplib.SMTPRecipientsRefused({
            self.recipient.email: (550, b'Message rejected by outbound policy')
        })
        with mock.patch('core.marketing.render_campaign_message', return_value=fake_message):
            call_command('process_marketing_queue', limit=1, campaign_limit=1)

        delivery = campaign.deliveries.get(recipient_email=self.recipient.email)
        self.assertEqual(delivery.status, 'failed')
        self.assertFalse(MarketingSuppression.objects.filter(
            email=self.recipient.email, is_active=True
        ).exists())

    def test_worker_suppresses_explicit_nonexistent_mailbox(self):
        import smtplib
        from django.core.management import call_command
        from core.marketing import prepare_campaign
        from core.models import MarketingCampaign, MarketingSuppression

        campaign = MarketingCampaign.objects.create(
            name='Confirmed bounce test', kind='announcement', audience='registered_users',
            subject='Test', headline='Test', body='Test', status='queued',
            last_test_sent_at=timezone.now(), minimum_gap_hours=0,
        )
        prepare_campaign(campaign)

        fake_message = mock.Mock()
        fake_message.send.side_effect = smtplib.SMTPRecipientsRefused({
            self.recipient.email: (550, b'5.1.1 The email account that you tried to reach does not exist')
        })
        with mock.patch('core.marketing.render_campaign_message', return_value=fake_message):
            call_command('process_marketing_queue', limit=1, campaign_limit=1)

        delivery = campaign.deliveries.get(recipient_email=self.recipient.email)
        self.assertEqual(delivery.status, 'suppressed')
        self.assertTrue(MarketingSuppression.objects.filter(
            email=self.recipient.email, is_active=True, source='smtp_hard_bounce_confirmed'
        ).exists())

    def test_legacy_ambiguous_bounce_can_be_released_for_retry(self):
        from django.core.management import call_command
        from core.models import MarketingCampaign, MarketingDelivery, MarketingSuppression

        campaign = MarketingCampaign.objects.create(
            name='Legacy bounce test', kind='announcement', audience='registered_users',
            subject='Test', headline='Test', body='Test', status='sending',
            last_test_sent_at=timezone.now(), minimum_gap_hours=0,
        )
        delivery = MarketingDelivery.objects.create(
            campaign=campaign, user=self.recipient, recipient_email=self.recipient.email,
            status='suppressed', attempts=1, last_error="Permanent recipient rejection: (550, b'Message rejected')",
        )
        suppression = MarketingSuppression.objects.create(
            email=self.recipient.email, reason='bounce', source='smtp_hard_bounce', is_active=True,
        )

        call_command('repair_marketing_suppressions', apply=True)
        suppression.refresh_from_db()
        delivery.refresh_from_db()
        self.assertFalse(suppression.is_active)
        self.assertEqual(delivery.status, 'failed')
        self.assertEqual(delivery.attempts, 0)


class MarketingDedicatedSmtpTests(TestCase):
    def test_sender_suspension_is_not_a_hard_bounce(self):
        from core.marketing import classify_smtp_refusal_data
        self.assertEqual(
            classify_smtp_refusal_data(
                [550], ['Outgoing mail from "chuosmart.com" has been suspended.']
            ),
            'sender_suspended',
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='transactional.example.com',
        EMAIL_PORT=465,
        EMAIL_HOST_USER='support@chuosmart.com',
        EMAIL_HOST_PASSWORD='transactional-secret',
        EMAIL_USE_SSL=True,
        EMAIL_USE_TLS=False,
        EMAIL_TIMEOUT=30,
        MARKETING_EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        MARKETING_EMAIL_HOST='marketing.example.com',
        MARKETING_EMAIL_PORT=587,
        MARKETING_EMAIL_HOST_USER='marketing-user',
        MARKETING_EMAIL_HOST_PASSWORD='marketing-secret',
        MARKETING_EMAIL_USE_SSL=False,
        MARKETING_EMAIL_USE_TLS=True,
        MARKETING_EMAIL_TIMEOUT=20,
    )
    def test_marketing_connection_uses_dedicated_smtp_settings(self):
        from core.marketing import get_marketing_connection
        with mock.patch('core.marketing.get_connection') as get_connection_mock:
            get_marketing_connection(fail_silently=False)
        kwargs = get_connection_mock.call_args.kwargs
        self.assertEqual(kwargs['host'], 'marketing.example.com')
        self.assertEqual(kwargs['port'], 587)
        self.assertEqual(kwargs['username'], 'marketing-user')
        self.assertEqual(kwargs['password'], 'marketing-secret')
        self.assertTrue(kwargs['use_tls'])
        self.assertFalse(kwargs['use_ssl'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        MARKETING_EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        MARKETING_EMAIL_HOST='should-never-connect.example.com',
        MARKETING_EMAIL_HOST_USER='should-never-connect',
        MARKETING_EMAIL_HOST_PASSWORD='should-never-connect',
    )
    def test_safe_runtime_backend_prevents_real_marketing_smtp_escape(self):
        from core.marketing import get_marketing_connection

        with mock.patch('core.marketing.get_connection') as get_connection_mock:
            get_marketing_connection(fail_silently=False)

        kwargs = get_connection_mock.call_args.kwargs
        self.assertEqual(
            kwargs['backend'],
            'django.core.mail.backends.locmem.EmailBackend',
        )
        self.assertNotIn('host', kwargs)
        self.assertNotIn('username', kwargs)
        self.assertNotIn('password', kwargs)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        MARKETING_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        CANONICAL_DOMAIN='testserver',
        MARKETING_EMAIL_BURST_CAP=3,
        MARKETING_EMAIL_TEN_MINUTE_CAP=15,
        MARKETING_EMAIL_HOURLY_CAP=100,
        MARKETING_EMAIL_DAILY_CAP=1500,
        MARKETING_EMAIL_SECONDS_BETWEEN_SENDS=0,
    )
    def test_sender_suspension_pauses_campaign_without_suppressing_recipient(self):
        import smtplib
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from core.marketing import prepare_campaign
        from core.models import MarketingCampaign, MarketingSuppression, UserNewsletterPreference

        user = User.objects.create_user(
            username='suspension-test', email='suspension@example.com', password='password12345'
        )
        UserNewsletterPreference.objects.update_or_create(user=user, defaults={'newsletter': True})
        campaign = MarketingCampaign.objects.create(
            name='Suspension test', kind='announcement', audience='registered_users',
            subject='Test', headline='Test', body='Test', status='queued',
            last_test_sent_at=timezone.now(), minimum_gap_hours=0,
        )
        prepare_campaign(campaign)
        fake_message = mock.Mock()
        fake_message.send.side_effect = smtplib.SMTPRecipientsRefused({
            user.email: (550, b'Outgoing mail from "chuosmart.com" has been suspended.')
        })
        with mock.patch('core.marketing.render_campaign_message', return_value=fake_message):
            with self.assertRaises(CommandError):
                call_command('process_marketing_queue', limit=3, campaign_limit=1)

        campaign.refresh_from_db()
        delivery = campaign.deliveries.get(recipient_email=user.email)
        self.assertEqual(campaign.status, 'paused')
        self.assertEqual(delivery.status, 'failed')
        self.assertIn('GLOBAL SENDER SUSPENSION', delivery.last_error)
        self.assertFalse(MarketingSuppression.objects.filter(email=user.email, is_active=True).exists())
