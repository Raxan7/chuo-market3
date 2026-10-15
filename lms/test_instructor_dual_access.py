"""Instructor permissions are additive to enrollment as a learner."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Course, CourseContent, CourseEnrollment, CourseModule, CoursePayment,
    InstructorRequest, InstructorRevenue,
)
from .revenue import recognize_payment_revenue


class InstructorDualAccessTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user('dual-role-instructor', password='pass')
        self.teacher = self.teacher_user.lms_profile
        self.teacher.role = 'instructor'
        self.teacher.save(update_fields=['role'])

        self.other_user = User.objects.create_user('another-teacher', password='pass')
        self.other = self.other_user.lms_profile
        self.other.role = 'instructor'
        self.other.save(update_fields=['role'])

        self.own_course = Course.objects.create(
            title='My Paid Instructor Course', course_type='general',
            is_free=False, price=Decimal('20000.00'), revenue_owner=self.teacher,
        )
        self.own_course.instructors.add(self.teacher)
        self.module = CourseModule.objects.create(
            course=self.own_course, title='Premium Instructor Module', order=1,
            price=Decimal('1000.00'),
        )
        self.content = CourseContent.objects.create(
            title='Private lesson for preview', module=self.module,
            content_type='text', text_content='Visible to owner without enrollment.',
        )
        self.other_course = Course.objects.create(
            title='Other Instructor Free Course', course_type='general',
            is_free=True, revenue_owner=self.other,
        )
        self.other_course.instructors.add(self.other)
        self.client.force_login(self.teacher_user)

    def test_instructor_can_preview_own_paid_course_and_content_without_enrollment(self):
        response = self.client.get(reverse('lms:course_detail', args=[self.own_course.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_course_instructor'])
        self.assertTrue(response.context['has_full_course_access'])
        self.assertFalse(response.context['is_enrolled'])
        self.assertContains(response, 'Instructor preview:')
        self.assertContains(response, 'Preview modules')
        self.assertNotContains(response, 'Enroll Now')
        self.assertNotContains(response, reverse('lms:enroll_course', args=[self.own_course.slug]))
        self.assertContains(response, self.content.title)

        content_url = reverse('lms:content_detail', args=[self.own_course.slug, self.content.pk])
        response = self.client.get(content_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible to owner without enrollment.')
        self.assertFalse(response.context['can_save_progress'])
        self.assertFalse(CourseEnrollment.objects.filter(
            student=self.teacher, course=self.own_course,
        ).exists())

    def test_direct_self_enroll_url_does_not_create_a_purchase_or_enrollment(self):
        response = self.client.get(reverse('lms:enroll_course', args=[self.own_course.slug]))
        self.assertRedirects(response, reverse('lms:course_detail', args=[self.own_course.slug]))
        self.assertFalse(CourseEnrollment.objects.filter(
            student=self.teacher, course=self.own_course,
        ).exists())

    def test_instructor_may_enroll_in_another_instructors_course_and_keep_earnings_tab(self):
        response = self.client.get(reverse('lms:enroll_course', args=[self.other_course.slug]))
        self.assertRedirects(response, reverse('lms:course_detail', args=[self.other_course.slug]))
        self.assertTrue(CourseEnrollment.objects.filter(
            student=self.teacher, course=self.other_course,
        ).exists())
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, 'instructor')

        dashboard = self.client.get(reverse('user_dashboard') + '?tab=instructor')
        self.assertEqual(dashboard.status_code, 200)
        self.assertTrue(dashboard.context['is_instructor_user'])
        self.assertEqual(dashboard.context['active_tab'], 'instructor')
        self.assertContains(dashboard, 'Your earnings')
        self.assertContains(dashboard, self.own_course.title)
        self.assertIn(self.other_course, [x['course'] for x in dashboard.context['enrolled_courses']])

    def test_instructor_can_start_payment_for_another_instructors_paid_course(self):
        other_paid = Course.objects.create(
            title='Another Paid Instructor Course', course_type='general',
            is_free=False, price=Decimal('20000.00'), revenue_owner=self.other,
        )
        other_paid.instructors.add(self.other)
        response = self.client.get(reverse('lms:enroll_course', args=[other_paid.slug]))
        self.assertRedirects(response, reverse('lms:payment_form', args=[other_paid.slug]),
                             fetch_redirect_response=False)
        self.assertFalse(CourseEnrollment.objects.filter(
            student=self.teacher, course=other_paid,
        ).exists())

    def test_non_owner_cannot_preview_paid_course_content_without_enrollment(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('lms:content_detail', args=[self.own_course.slug, self.content.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('lms:enroll_course', args=[self.own_course.slug]), response.url)

    def test_approved_legacy_instructor_gets_earnings_even_if_role_still_student(self):
        # Legacy approval is recognized by navigation but was previously
        # hidden by the unified dashboard's separate role-only condition.
        self.teacher.role = 'student'
        self.teacher.save(update_fields=['role'])
        InstructorRequest.objects.create(
            user=self.teacher_user, reason='I teach', qualifications='Experience',
            status='approved',
        )
        student = User.objects.create_user('paid-learner', password='pass')
        payment = CoursePayment.objects.create(
            user=student, course=self.own_course, status='completed',
            amount=Decimal('10000.00'),
        )
        revenue = recognize_payment_revenue(payment)
        self.assertIsNotNone(revenue)
        self.assertEqual(InstructorRevenue.objects.filter(instructor=self.teacher).count(), 1)

        dashboard = self.client.get(reverse('user_dashboard') + '?tab=instructor')
        self.assertEqual(dashboard.status_code, 200)
        self.assertTrue(dashboard.context['is_instructor_user'])
        self.assertEqual(dashboard.context['active_tab'], 'instructor')
        self.assertEqual(dashboard.context['instructor_total_earnings'], revenue.instructor_amount)
        self.assertContains(dashboard, 'Your earnings')
        # The link exposed by navigation should reach the same earnings page.
        self.assertRedirects(
            self.client.get(reverse('lms:instructor_dashboard')),
            reverse('user_dashboard') + '?tab=instructor',
            fetch_redirect_response=False,
        )
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.role, 'instructor')
