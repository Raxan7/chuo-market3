from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from .models import (
    Course, CourseModule, CoursePayment, InstructorRevenue, LMSProfile,
    ModulePayment, PayoutProfile, PayoutRequest,
)
from .revenue import create_payout_request, recognize_payment_revenue, set_payout_status


@override_settings(
    INSTRUCTOR_REVENUE_SHARE_PERCENT='80',
    INSTRUCTOR_PAYOUT_THRESHOLD_TZS='100000',
    INSTRUCTOR_PAYOUT_ALERT_EMAILS=[
        'saidi@chuosmart.com', 'francis@chuosmart.com', 'support@chuosmart.com'
    ],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class InstructorRevenueTests(TestCase):
    def setUp(self):
        self.instructor_user = User.objects.create_user('teacher', 'teacher@example.com', 'pass')
        # User creation already creates LMSProfile through lms.signals.create_lms_profile.
        # Reuse that row instead of violating the LMSProfile one-to-one constraint.
        self.instructor = self.instructor_user.lms_profile
        self.instructor.role = 'instructor'
        self.instructor.save(update_fields=['role'])
        self.student = User.objects.create_user('student-revenue', 'student@example.com', 'pass')
        self.course = Course.objects.create(
            title='Paid Revenue Course', is_free=False, price=Decimal('50000.00'),
            revenue_owner=self.instructor,
        )
        self.course.instructors.add(self.instructor)

    def test_course_payment_splits_80_20_and_is_idempotent(self):
        payment = CoursePayment.objects.create(
            user=self.student, course=self.course, amount=Decimal('50000.00'), status='completed'
        )
        first = recognize_payment_revenue(payment)
        second = recognize_payment_revenue(payment)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(InstructorRevenue.objects.count(), 1)
        self.assertEqual(first.instructor_amount, Decimal('40000.00'))
        self.assertEqual(first.platform_amount, Decimal('10000.00'))

    def test_module_payment_splits_actual_amount(self):
        module = CourseModule.objects.create(course=self.course, title='Paid Module', order=1, price=Decimal('1000.00'))
        payment = ModulePayment.objects.create(
            user=self.student, module=module, amount=Decimal('1000.00'), status='completed'
        )
        revenue = recognize_payment_revenue(payment)
        self.assertEqual(revenue.instructor_amount, Decimal('800.00'))
        self.assertEqual(revenue.platform_amount, Decimal('200.00'))
        self.assertEqual(revenue.module, module)

    def test_free_course_does_not_generate_revenue(self):
        free = Course.objects.create(title='Free Revenue Course', is_free=True, revenue_owner=self.instructor)
        free.instructors.add(self.instructor)
        payment = CoursePayment.objects.create(
            user=self.student, course=free, amount=Decimal('1000.00'), status='completed'
        )
        self.assertIsNone(recognize_payment_revenue(payment))
        self.assertEqual(InstructorRevenue.objects.count(), 0)

    def test_pending_payment_does_not_generate_revenue(self):
        payment = CoursePayment.objects.create(
            user=self.student, course=self.course, amount=Decimal('50000.00'), status='pending'
        )
        self.assertIsNone(recognize_payment_revenue(payment))

    def test_multi_instructor_course_without_revenue_owner_is_not_guessed(self):
        second_user = User.objects.create_user('teacher-two', 'teacher2@example.com', 'pass')
        second_instructor = second_user.lms_profile
        second_instructor.role = 'instructor'
        second_instructor.save(update_fields=['role'])

        self.course.revenue_owner = None
        self.course.save(update_fields=['revenue_owner'])
        self.course.instructors.add(second_instructor)
        payment = CoursePayment.objects.create(
            user=self.student, course=self.course, amount=Decimal('50000.00'), status='completed'
        )

        self.assertIsNone(recognize_payment_revenue(payment))
        self.assertEqual(InstructorRevenue.objects.count(), 0)

    def test_payout_threshold_reserves_rows_and_emails_all_recipients(self):
        for index in range(3):
            payment = CoursePayment.objects.create(
                user=self.student,
                course=self.course,
                amount=Decimal('50000.00'),
                status='completed',
                snippe_session_id=f'session-{index}',
            )
            recognize_payment_revenue(payment)
        PayoutProfile.objects.create(
            instructor=self.instructor,
            payout_method='mobile_money',
            account_name='Teacher One',
            phone_number='+255700000001',
            mobile_network='M-Pesa',
        )

        # create_payout_request schedules the alert with transaction.on_commit().
        # Django TestCase wraps each test in a transaction that never normally commits,
        # so explicitly execute registered commit callbacks here.
        with self.captureOnCommitCallbacks(execute=True):
            payout = create_payout_request(self.instructor)

        self.assertEqual(payout.amount, Decimal('120000.00'))
        self.assertEqual(InstructorRevenue.objects.filter(payout_request=payout).count(), 3)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(set(mail.outbox[0].to), {
            'saidi@chuosmart.com', 'francis@chuosmart.com', 'support@chuosmart.com'
        })
        with self.assertRaisesMessage(ValueError, 'at least'):
            create_payout_request(self.instructor)

    def test_rejected_payout_releases_reserved_revenue(self):
        for index in range(3):
            payment = CoursePayment.objects.create(
                user=self.student, course=self.course, amount=Decimal('50000.00'),
                status='completed', snippe_session_id=f'reject-{index}'
            )
            recognize_payment_revenue(payment)
        PayoutProfile.objects.create(
            instructor=self.instructor, payout_method='bank', account_name='Teacher One',
            bank_name='Example Bank', bank_account_number='1234567890'
        )
        payout = create_payout_request(self.instructor)
        set_payout_status(payout, 'rejected')
        self.assertFalse(InstructorRevenue.objects.filter(payout_request=payout).exists())
        self.assertEqual(PayoutRequest.objects.get(pk=payout.pk).status, 'rejected')
