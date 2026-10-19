"""Regression tests. Mock Snippe HTTP: NEVER transfer real funds from tests."""
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from lms.models import (Course, CoursePayment, InstructorRevenue, PayoutProfile,
                        PayoutRequest, SnippeWebhookEvent)
from lms.revenue import create_payout_request, recognize_payment_revenue, set_payout_status
from .models import PayoutTransfer
from .service import (PayoutSafetyError, authorize_transfer, dispatch_transfer,
                      reconcile_transfer)

TEST_KEY = Fernet.generate_key().decode()
CONFIG = dict(
    SNIPPE_PAYOUT_ENCRYPTION_KEY=TEST_KEY,
    SNIPPE_PAYOUT_API_KEY='TEST-NOT-A-REAL-SECRET',
    SNIPPE_PAYOUT_BASE_URL='https://api.snippe.sh',
    SNIPPE_PAYOUT_WEBHOOK_URL='https://chuosmart.test/payouts/webhooks/snippe/',
    SNIPPE_WEBHOOK_SECRET='payout-webhook-test-key',
    INSTRUCTOR_DISBURSEMENTS_ENABLED=True,
    INSTRUCTOR_PAYOUT_REQUIRE_DUAL_CONTROL=True,
    INSTRUCTOR_PAYOUT_SETTLEMENT_DAYS=0,
    INSTRUCTOR_PAYOUT_THRESHOLD_TZS='100000',
    INSTRUCTOR_PAYOUT_MAX_SINGLE_TZS=500000,
    INSTRUCTOR_PAYOUT_MAX_DAILY_TZS=1000000,
    INSTRUCTOR_PAYOUT_ALERT_EMAILS=[],
)


def api_response(data):
    result = Mock()
    result.status_code = 200
    result.raise_for_status.return_value = None
    result.json.return_value = {'status': 'success', 'code': 200, 'data': data}
    return result


@override_settings(**CONFIG)
class SecureDisbursementTests(TestCase):
    def setUp(self):
        self.instructor_user = User.objects.create_user('payteacher', 'payteacher@example.test', 'pass')
        self.instructor = self.instructor_user.lms_profile
        self.instructor.role = 'instructor'
        self.instructor.save(update_fields=['role'])
        self.student = User.objects.create_user('paystudent', 'paystudent@example.test', 'pass')
        self.approver = User.objects.create_superuser('firstapprover', 'first@example.test', 'pass')
        self.authorizer = User.objects.create_superuser('secondapprover', 'second@example.test', 'pass')
        self.course = Course.objects.create(
            title='Payout Security Course', is_free=False,
            price=Decimal('50000.00'), revenue_owner=self.instructor,
        )
        self.course.instructors.add(self.instructor)
        for i in range(3):
            payment = CoursePayment.objects.create(
                user=self.student, course=self.course, amount=Decimal('50000.00'),
                status='completed', snippe_reference=f'collection-{i}', webhook_event_id=f'collection-event-{i}',
            )
            SnippeWebhookEvent.objects.create(
                event_id=f'collection-event-{i}', event_type='payment.completed',
                payment_type='course_enrollment', provider_reference=f'collection-{i}',
                payload_hash='0' * 64, status='processed',
            )
            recognize_payment_revenue(payment)
        self.payout_profile = PayoutProfile.objects.create(
            instructor=self.instructor, payout_method='mobile_money',
            account_name='Teacher Name', phone_number='+255700000001', mobile_network='M-Pesa',
        )
        self.payout = create_payout_request(self.instructor)
        set_payout_status(self.payout, 'approved', self.approver)
        self.transfer = authorize_transfer(self.payout.pk, self.authorizer)
        self.recipient = {'phone': '255700000001', 'name': 'Teacher Name'}

    def mock_snippe(self, method, url, **kwargs):
        if url.endswith('/fee'):
            return api_response({'amount': 120000, 'currency': 'TZS', 'fee_amount': 2000, 'total_amount': 122000})
        if method == 'POST':
            self.assertEqual(kwargs['json']['amount'], 120000)
            self.assertEqual(kwargs['json']['recipient_phone'], '255700000001')
            self.assertLessEqual(len(kwargs['headers']['Idempotency-Key']), 30)
            return api_response({'reference': 'snippe-pay-0001', 'status': 'pending',
                                 'amount': {'currency': 'TZS', 'value': 120000}, 'recipient': self.recipient})
        if method == 'GET':
            return api_response({'reference': 'snippe-pay-0001', 'status': 'completed',
                                 'amount': {'currency': 'TZS', 'value': 120000}, 'recipient': self.recipient})
        raise AssertionError('Unexpected request')

    def test_approve_then_dispatch_then_verify_is_once_only(self):
        with patch('payouts.service.requests.request', side_effect=self.mock_snippe) as provider:
            result = dispatch_transfer(self.payout.pk)
            self.assertEqual(result.status, 'pending')
            self.payout.refresh_from_db()
            self.assertEqual(self.payout.status, 'approved')
            with self.assertRaises(PayoutSafetyError):
                dispatch_transfer(self.payout.pk)
            self.assertEqual(sum(call.args[0] == 'POST' for call in provider.call_args_list), 1)
            result = reconcile_transfer(self.payout.pk)
            self.assertEqual(result.status, 'completed')
            self.payout.refresh_from_db()
            self.assertEqual(self.payout.status, 'paid')

    def test_failed_provider_confirmed_releases_reserved_once(self):
        with patch('payouts.service.requests.request', side_effect=self.mock_snippe):
            dispatch_transfer(self.payout.pk)
        def failed(method, url, **kwargs):
            return api_response({'reference': 'snippe-pay-0001', 'status': 'failed',
                                 'amount': {'currency': 'TZS', 'value': 120000}, 'recipient': self.recipient})
        with patch('payouts.service.requests.request', side_effect=failed):
            self.assertEqual(reconcile_transfer(self.payout.pk).status, 'failed')
            self.assertEqual(reconcile_transfer(self.payout.pk).status, 'failed')
        self.assertFalse(InstructorRevenue.objects.filter(payout_request_id=self.payout.pk).exists())
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'rejected')

    def test_timeout_never_retries_outbound_post(self):
        calls = []
        def timeout(method, url, **kwargs):
            calls.append(method)
            if method == 'POST':
                raise requests.Timeout('Ambiguous payment result')
            return self.mock_snippe(method, url, **kwargs)
        with patch('payouts.service.requests.request', side_effect=timeout):
            with self.assertRaisesRegex(PayoutSafetyError, 'RECONCILE'):
                dispatch_transfer(self.payout.pk)
            with self.assertRaises(PayoutSafetyError):
                dispatch_transfer(self.payout.pk)
        self.assertEqual(calls.count('POST'), 1)
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, 'unknown')

    def test_threshold_and_server_ledger_cannot_be_increased(self):
        PayoutTransfer.objects.filter(pk=self.transfer.pk).update(amount_tzs=500000)
        with patch('payouts.service.requests.request') as provider:
            with self.assertRaisesRegex(PayoutSafetyError, 'changed'):
                dispatch_transfer(self.payout.pk)
            provider.assert_not_called()

    def test_two_person_authorization_and_disabled_kill_switch(self):
        with self.assertRaises(PayoutSafetyError):
            authorize_transfer(self.payout.pk, self.approver)
        with override_settings(INSTRUCTOR_DISBURSEMENTS_ENABLED=False):
            with patch('payouts.service.requests.request') as provider:
                with self.assertRaisesRegex(PayoutSafetyError, 'disabled'):
                    dispatch_transfer(self.payout.pk)
                provider.assert_not_called()

    def test_admin_mark_paid_shortcut_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            set_payout_status(self.payout, 'paid', self.approver)
        with self.assertRaisesRegex(ValueError, 'authorized'):
            set_payout_status(self.payout, 'rejected', self.approver)

    def test_changed_recipient_cannot_be_authorized(self):
        # Forbid any second transfer even if another superuser attempts it.
        self.assertEqual(PayoutTransfer.objects.filter(payout_request_id=self.payout.pk).count(), 1)
        with self.assertRaises(PayoutSafetyError):
            authorize_transfer(self.payout.pk, self.authorizer)

    def test_signed_webhook_uses_authoritative_get_not_event_amount(self):
        with patch('payouts.service.requests.request', side_effect=self.mock_snippe):
            dispatch_transfer(self.payout.pk)
        body = json.dumps({'id': 'payout-event-1', 'type': 'payout.completed',
                           'data': {'reference': 'snippe-pay-0001', 'amount': {'value': 99999999, 'currency': 'TZS'}}})
        timestamp = str(int(time.time()))
        url = reverse('payout_webhook')
        invalid = self.client.post(url, body, content_type='application/json',
                                   HTTP_X_WEBHOOK_TIMESTAMP=timestamp, HTTP_X_WEBHOOK_SIGNATURE='0' * 64)
        self.assertEqual(invalid.status_code, 400)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'approved')
        signed = hmac.new(b'payout-webhook-test-key', f'{timestamp}.{body}'.encode(), hashlib.sha256).hexdigest()
        with patch('payouts.service.requests.request', side_effect=self.mock_snippe) as provider:
            response = self.client.post(url, body, content_type='application/json',
                                        HTTP_X_WEBHOOK_TIMESTAMP=timestamp, HTTP_X_WEBHOOK_SIGNATURE=signed)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(provider.call_count, 1)
            duplicate = self.client.post(url, body, content_type='application/json',
                                         HTTP_X_WEBHOOK_TIMESTAMP=timestamp, HTTP_X_WEBHOOK_SIGNATURE=signed)
            self.assertEqual(duplicate.status_code, 200)
            self.assertEqual(provider.call_count, 1)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'paid')

    def test_new_request_caps_earnings_without_double_reserving(self):
        # The initial 120k is already reserved. Three later 240k earnings
        # should yield a 480k request, leaving one distinct 240k entry free.
        for i in range(3):
            payment = CoursePayment.objects.create(
                user=self.student, course=self.course, amount=Decimal('300000.00'),
                status='completed', snippe_reference=f'new-collection-{i}',
                webhook_event_id=f'new-event-{i}',
            )
            recognize_payment_revenue(payment)
        later = create_payout_request(self.instructor)
        self.assertEqual(later.amount, Decimal('480000.00'))
        self.assertEqual(InstructorRevenue.objects.filter(payout_request=later).count(), 2)
        self.assertEqual(InstructorRevenue.objects.filter(payout_request__isnull=True).count(), 1)

    def test_provider_amount_mismatch_keeps_funds_reserved(self):
        with patch('payouts.service.requests.request', side_effect=self.mock_snippe):
            dispatch_transfer(self.payout.pk)
        def tampered(*args, **kwargs):
            return api_response({'reference': 'snippe-pay-0001', 'status': 'completed',
                                 'amount': {'currency': 'TZS', 'value': 900000}, 'recipient': self.recipient})
        with patch('payouts.service.requests.request', side_effect=tampered):
            with self.assertRaises(PayoutSafetyError):
                reconcile_transfer(self.payout.pk)
        self.assertTrue(InstructorRevenue.objects.filter(payout_request=self.payout).exists())
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'approved')
