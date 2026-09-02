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

        campaign = MarketingCampaign.objects.get(name__startswith=f'[AUTO-CONTENT:blog:{newer.pk}]')
        self.assertIn(campaign.status, {'queued', 'scheduled'})
        self.assertEqual(len(mail.outbox), 0)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
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
