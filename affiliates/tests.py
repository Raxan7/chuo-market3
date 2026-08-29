from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Affiliate, PayoutRequest


class PayoutSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='affiliate-user',
            email='affiliate@example.com',
            password='password12345',
        )
        self.affiliate = Affiliate.objects.create(
            user=self.user,
            affiliate_code='affiliate-test',
            balance=Decimal('10000.00'),
            payment_method='mobile_money',
            payment_details={'phone': '255700000000'},
        )
        self.client.login(username='affiliate-user', password='password12345')

    def test_payout_request_is_post_only(self):
        response = self.client.get(reverse('affiliates:request_payout'))
        self.assertEqual(response.status_code, 405)

    def test_payout_request_reserves_available_balance_without_erasing_it(self):
        response = self.client.post(reverse('affiliates:request_payout'))
        self.assertEqual(response.status_code, 200)
        self.affiliate.refresh_from_db()
        self.assertEqual(self.affiliate.balance, Decimal('10000.00'))
        payout = PayoutRequest.objects.get(affiliate=self.affiliate)
        self.assertEqual(payout.amount, Decimal('10000.00'))
        self.assertEqual(payout.status, PayoutRequest.PayoutStatus.PENDING)

        second = self.client.post(reverse('affiliates:request_payout'))
        self.assertEqual(second.status_code, 400)
        self.assertEqual(PayoutRequest.objects.filter(affiliate=self.affiliate).count(), 1)


class AffiliateFlowRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='new-affiliate', email='new-affiliate@example.com', password='password12345'
        )
        self.client.login(username='new-affiliate', password='password12345')

    def test_registration_uses_affiliate_code_field(self):
        response = self.client.post(reverse('affiliates:register'))
        self.assertRedirects(response, reverse('affiliates:dashboard'))
        affiliate = Affiliate.objects.get(user=self.user)
        self.assertTrue(affiliate.affiliate_code)

    def test_canonical_code_referral_link_resolves(self):
        affiliate = Affiliate.objects.create(user=self.user, affiliate_code='share-me')
        visitor = self.client_class()
        response = visitor.get(reverse('affiliates:referral_link', kwargs={'code': 'share-me'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(visitor.session.get('referrer_id'), affiliate.pk)

    def test_payout_history_uses_payout_requests(self):
        affiliate = Affiliate.objects.create(user=self.user, affiliate_code='payout-history')
        PayoutRequest.objects.create(
            affiliate=affiliate,
            amount=Decimal('2500.00'),
            payment_method='mobile_money',
            status=PayoutRequest.PayoutStatus.PAID,
        )
        response = self.client.get(reverse('affiliates:payouts'))
        self.assertContains(response, '2,500')
        self.assertContains(response, 'Paid')
