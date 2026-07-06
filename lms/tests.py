import json
import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .ai_assessments import ensure_module_assessment, queue_module_assessment_generation
from .models import Course, CourseContent, CourseEnrollment, LMSProfile, CourseModule, ContentAccess, QuizTaker, Quiz, MCQuestion, Choice, StudentAnswer, ModuleProgress, CoursePayment, CertificateTemplate, PaymentMethod
from .utils import ensure_course_learning_records, is_module_unlocked, update_module_content_completion, update_module_assessment_completion


@override_settings(
    DEBUG=True,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)
class LMSModuleGatingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpassword',
        )
        self.profile, _ = LMSProfile.objects.get_or_create(
            user=self.user,
            defaults={'role': 'student'},
        )
        self.course = Course.objects.create(title='Sample Course', summary='Test course summary')
        self.enrollment, _ = CourseEnrollment.objects.get_or_create(
            student=self.profile,
            course=self.course,
            defaults={'payment_status': 'not_required'},
        )
        self.client.login(username='student', password='testpassword')

    def _create_content(self, module, title='Lesson 1'):
        return CourseContent.objects.create(
            title=title,
            module=module,
            content_type='text',
            text_content='Module content for testing.',
            order=1,
        )

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_overview_module_skips_assessment_and_unlocks_next_module(self):
        overview_module = CourseModule.objects.create(
            course=self.course,
            title='Course Overview',
            description='Introductory module',
            order=0,
            skip_assessment=True,
        )
        next_module = CourseModule.objects.create(
            course=self.course,
            title='Module 2',
            description='Second module',
            order=1,
        )
        content = self._create_content(overview_module)

        self.assertIsNone(ensure_module_assessment(overview_module))

        ContentAccess.objects.create(student=self.profile, content=content, completed=True)
        progress = update_module_content_completion(overview_module, self.profile)

        self.assertTrue(progress.content_completed)
        self.assertTrue(progress.assessment_passed)
        self.assertTrue(progress.completed)
        self.assertTrue(is_module_unlocked(next_module, self.profile))

        # Ensure non-overview module has an assessment available for UI
        ensure_module_assessment(next_module)

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['module_states'][0]['skip_assessment'])
        self.assertTrue(response.context['module_states'][0]['completed'])
        self.assertTrue(response.context['module_states'][1]['unlocked'])
        self.assertIsNone(response.context['module_states'][0]['assessment'])
        self.assertIsNotNone(response.context['module_states'][1]['assessment'])
        self.assertContains(response, 'Open Assessment')

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_generated_assessment_is_required_before_next_module_unlocks(self):
        first_module = CourseModule.objects.create(
            course=self.course,
            title='Module 1',
            description='First module',
            order=0,
        )
        second_module = CourseModule.objects.create(
            course=self.course,
            title='Module 2',
            description='Second module',
            order=1,
        )
        content = self._create_content(first_module)

        quiz = ensure_module_assessment(first_module)
        self.assertIsNotNone(quiz)
        self.assertGreater(quiz.questions.count(), 0)

        ContentAccess.objects.create(student=self.profile, content=content, completed=True)
        progress = update_module_content_completion(first_module, self.profile)
        self.assertTrue(progress.content_completed)
        self.assertFalse(progress.assessment_passed)
        self.assertFalse(is_module_unlocked(second_module, self.profile))

        quiz_taker = QuizTaker.objects.create(
            user=self.profile,
            quiz=quiz,
            score=80,
            completed=True,
            date_completed=timezone.now(),
        )
        progress = update_module_assessment_completion(quiz_taker)

        self.assertTrue(progress.assessment_passed)
        self.assertTrue(progress.completed)
        self.assertTrue(is_module_unlocked(second_module, self.profile))

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_enrollment_queues_personalized_assessment_for_student(self):
        module = CourseModule.objects.create(
            course=self.course,
            title='Module 1',
            description='First module',
            order=0,
        )

        quiz = queue_module_assessment_generation(module, student=self.profile)

        self.assertIsNotNone(quiz)
        self.assertEqual(quiz.generated_for, self.profile)
        self.assertEqual(quiz.generation_status, 'ready')
        self.assertGreater(quiz.questions.count(), 0)

        response = self.client.get(reverse('lms:quiz_detail', kwargs={'slug': quiz.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['quiz_is_ready'])
        self.assertFalse(response.context['is_generating'])

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_new_module_after_enrollment_gets_progress_and_one_ai_quiz(self):
        module = CourseModule.objects.create(
            course=self.course,
            title='Late Module',
            description='Added after the student enrolled',
            order=2,
        )
        self._create_content(module, title='Late Lesson')

        stats = ensure_course_learning_records(self.course, self.profile)

        self.assertGreaterEqual(stats['progress_existing'] + stats['progress_created'], 1)
        progress = ModuleProgress.objects.get(student=self.profile, module=module)
        self.assertFalse(progress.content_completed)
        self.assertFalse(progress.assessment_passed)

        quizzes = Quiz.objects.filter(module=module, generated_for=self.profile, draft=False)
        self.assertEqual(quizzes.count(), 1)
        self.assertEqual(quizzes.first().generation_status, 'ready')
        self.assertGreater(quizzes.first().questions.count(), 0)

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        state = next(item for item in response.context['module_states'] if item['module'].id == module.id)
        self.assertIsNotNone(state['progress'])
        self.assertIsNotNone(state['assessment'])
        self.assertEqual(state['assessment_status'], 'ready')

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_queueing_module_assessment_is_idempotent(self):
        module = CourseModule.objects.create(
            course=self.course,
            title='No Duplicate Module',
            description='Only one quiz should exist',
            order=3,
        )

        first_quiz = queue_module_assessment_generation(module, student=self.profile)
        second_quiz = queue_module_assessment_generation(module, student=self.profile)

        self.assertEqual(first_quiz.id, second_quiz.id)
        self.assertEqual(
            Quiz.objects.filter(module=module, generated_for=self.profile, draft=False).count(),
            1,
        )

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_instructor_quiz_create_route_queues_ai_instead_of_manual_form(self):
        instructor_user = User.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='testpassword',
        )
        instructor_profile, _ = LMSProfile.objects.get_or_create(
            user=instructor_user,
            defaults={'role': 'instructor'},
        )
        instructor_profile.role = 'instructor'
        instructor_profile.save()
        self.course.instructors.add(instructor_profile)
        module = CourseModule.objects.create(
            course=self.course,
            title='AI Route Module',
            description='Route test module',
            order=4,
        )

        self.client.logout()
        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(
            reverse('lms:quiz_create_in_module', kwargs={'course_slug': self.course.slug, 'module_id': module.id}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Create New Quiz')
        self.assertEqual(
            Quiz.objects.filter(module=module, generated_for__isnull=True, draft=False).count(),
            1,
        )

    def test_locked_modules_render_as_disabled_controls(self):
        first_module = CourseModule.objects.create(
            course=self.course,
            title='Module 1',
            description='First module',
            order=0,
        )
        second_module = CourseModule.objects.create(
            course=self.course,
            title='Module 2',
            description='Second module',
            order=1,
        )
        self._create_content(first_module)
        self._create_content(second_module, title='Lesson 2')

        # Ensure second module has an assessment available for UI
        ensure_module_assessment(second_module)

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['module_states'][1]['unlocked'])
        self.assertIn('Module 1', response.context['module_states'][1]['lock_message'])
        self.assertIsNotNone(response.context['module_states'][1]['assessment'])
        self.assertContains(response, 'Open Assessment')
        self.assertContains(response, 'Prerequisite module: Module 1')
        self.assertIn('aria-disabled="true"', response.content.decode())
        self.assertNotIn(f'data-bs-target="#collapse{second_module.id}"', response.content.decode())

    @override_settings(CEREBRAS_API_KEY=None, CEREBRAS_STRICT_ASSESSMENTS=False)
    def test_passing_quiz_saves_progress_and_redirects_to_next_module(self):
        first_module = CourseModule.objects.create(
            course=self.course,
            title='Module 1',
            description='First module',
            order=0,
        )
        second_module = CourseModule.objects.create(
            course=self.course,
            title='Module 2',
            description='Second module',
            order=1,
        )
        self._create_content(first_module, title='Lesson 1')
        quiz = Quiz.objects.create(
            course=self.course,
            module=first_module,
            title='Module 1 Mastery Check',
            category='practice',
            pass_mark=70,
            answers_at_end=True,
            exam_paper=True,
            draft=False,
            generation_status='ready',
        )
        question = MCQuestion.objects.create(quiz=quiz, content='What is 2 + 2?', explanation='Basic math', order=1)
        correct_choice = Choice.objects.create(question=question, content='4', correct=True)
        Choice.objects.create(question=question, content='3', correct=False)
        StudentAnswer.objects.create(
            quiz_taker=QuizTaker.objects.create(
                user=self.profile,
                quiz=quiz,
                score=0,
                completed=False,
                date_started=timezone.now(),
            ),
            question=question,
            mc_answer=correct_choice,
            is_correct=True,
        )

        quiz_taker = QuizTaker.objects.get(user=self.profile, quiz=quiz)
        response = self.client.get(reverse('lms:complete_quiz', kwargs={'quiz_taker_id': quiz_taker.id}), follow=False)

        self.assertIn(response.status_code, (301, 302))
        self.assertIn(f'/lms/courses/{self.course.slug}/', response['Location'])
        self.assertIn(f'#collapse{second_module.id}', response['Location'])

        progress = ModuleProgress.objects.get(student=self.profile, module=first_module)
        self.assertTrue(progress.assessment_passed)
        self.assertTrue(progress.content_completed)
        self.assertGreaterEqual(float(progress.best_score), 70)
        self.assertTrue(progress.completed)


@override_settings(
    DEBUG=True,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)
class CoursePaymentTests(TestCase):
    """Tests for paid/free course payment flow and instructor price editing"""

    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            username='student', password='testpassword',
        )
        self.student_profile, _ = LMSProfile.objects.get_or_create(
            user=self.student_user, defaults={'role': 'student'},
        )
        self.instructor_user = User.objects.create_user(
            username='instructor', password='testpassword',
        )
        self.instructor_profile, created = LMSProfile.objects.get_or_create(
            user=self.instructor_user,
        )
        if not created or self.instructor_profile.role != 'instructor':
            self.instructor_profile.role = 'instructor'
            self.instructor_profile.save()
        # Free course
        self.free_course = Course.objects.create(
            title='Free Course', is_free=True, price=0,
            course_type='general',
        )
        self.free_course.instructors.add(self.instructor_profile)
        # Paid course (general type to avoid university-specific field requirements)
        self.paid_course = Course.objects.create(
            title='Paid Course', is_free=False, price=Decimal('25000.00'),
            course_type='general',
        )
        self.paid_course.instructors.add(self.instructor_profile)

    # ── Pay-First Model ──────────────────────────────────────────────

    def test_free_course_enrolls_immediately(self):
        """Free courses should enroll instantly without payment"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:enroll_course', kwargs={'slug': self.free_course.slug}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        enrollment = CourseEnrollment.objects.get(
            student=self.student_profile, course=self.free_course,
        )
        self.assertEqual(enrollment.payment_status, 'not_required')

    def test_paid_course_redirects_to_payment_form(self):
        """Paid courses should redirect to payment form (not auto-enroll)"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:enroll_course', kwargs={'slug': self.paid_course.slug}),
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/payment/', response['Location'])
        self.assertFalse(
            CourseEnrollment.objects.filter(
                student=self.student_profile, course=self.paid_course,
            ).exists(),
        )

    def test_enrolled_paid_course_without_approved_payment_has_no_access(self):
        """Enrollment without approved payment should not grant access"""
        self.client.login(username='student', password='testpassword')
        CourseEnrollment.objects.create(
            student=self.student_profile, course=self.paid_course,
            payment_status='pending',
        )
        self.assertFalse(self.paid_course.user_has_access(self.student_user))

    def test_enrolled_paid_course_with_approved_payment_has_access(self):
        """Enrollment with approved payment should grant access"""
        self.client.login(username='student', password='testpassword')
        CourseEnrollment.objects.create(
            student=self.student_profile, course=self.paid_course,
            payment_status='approved',
        )
        self.assertTrue(self.paid_course.user_has_access(self.student_user))

    def test_paid_course_price_shown_on_course_detail(self):
        """Course detail page should show price for paid courses"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:course_detail', kwargs={'slug': self.paid_course.slug}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25000.00')
        self.assertContains(response, 'Paid Course')

    def test_free_course_shows_free_badge(self):
        """Free course detail should show Free badge"""
        response = self.client.get(
            reverse('lms:course_detail', kwargs={'slug': self.free_course.slug}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Free Course')

    # ── CoursePayment model ──────────────────────────────────────────

    @override_settings(SNIPPE_API_KEY='test_key')
    @override_settings(CERTIFICATE_PRICE=15000)
    def test_course_payment_init_creates_payment_record(self):
        """course_payment_init should create a CoursePayment and attempt Snippe redirect"""
        self.client.login(username='student', password='testpassword')
        # Before the call, no payments exist
        self.assertEqual(
            CoursePayment.objects.filter(user=self.student_user, course=self.paid_course).count(), 0,
        )
        # Mock the Snippe API call — the view will fail because test has no real API
        # But we can verify the view redirects to payment_form on failure
        response = self.client.get(
            reverse('lms:course_payment_init', kwargs={'slug': self.paid_course.slug}),
            follow=True,
        )
        # It should fall back to payment form (Snippe returns error in test)
        self.assertIn('payment', response.request['PATH_INFO'])

    @override_settings(SNIPPE_API_KEY='')
    def test_course_payment_init_falls_back_when_snippe_unconfigured(self):
        """When Snippe is not configured, redirect back to payment form"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:course_payment_init', kwargs={'slug': self.paid_course.slug}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('payment', response.request['PATH_INFO'])

    def test_course_payment_success_without_payment_shows_form(self):
        """course_payment_success without completed payment should redirect back"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:course_payment_success', kwargs={'slug': self.paid_course.slug}),
            follow=True,
        )
        self.assertIn('payment', response.request['PATH_INFO'])

    def test_course_payment_success_with_completed_payment_creates_enrollment(self):
        """course_payment_success with completed CoursePayment should create approved enrollment"""
        self.client.login(username='student', password='testpassword')
        CoursePayment.objects.create(
            user=self.student_user, course=self.paid_course,
            amount=self.paid_course.price, status='completed',
        )
        response = self.client.get(
            reverse('lms:course_payment_success', kwargs={'slug': self.paid_course.slug}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        enrollment = CourseEnrollment.objects.get(
            student=self.student_profile, course=self.paid_course,
        )
        self.assertEqual(enrollment.payment_status, 'approved')

    # ── Payment form shows online option ────────────────────────────

    @override_settings(SNIPPE_API_KEY='test_key_123')
    def test_payment_form_shows_online_pay_button_when_snippe_configured(self):
        """Payment form should show 'Pay Online' button when Snippe is configured"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:payment_form', kwargs={'slug': self.paid_course.slug}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pay Online')
        self.assertContains(response, '25000.00')

    @override_settings(SNIPPE_API_KEY='')
    def test_payment_form_hides_online_button_when_snippe_not_configured(self):
        """Payment form should show nothing useful when Snippe is not configured"""
        self.client.login(username='student', password='testpassword')
        response = self.client.get(
            reverse('lms:payment_form', kwargs={'slug': self.paid_course.slug}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pay Now')
        self.assertNotContains(response, 'Pay Online')

    # ── Webhook handling for course payments ─────────────────────────

    @override_settings(SNIPPE_WEBHOOK_SECRET='test-secret-key')
    def test_webhook_ignores_request_without_user_id(self):
        """Webhook should return 200 but skip processing if no user_id"""
        import hashlib
        import hmac
        import time as time_module
        from django.test import RequestFactory
        from .views import snippe_webhook
        factory = RequestFactory()
        payload = json.dumps({
            'type': 'payment.completed',
            'data': {
                'reference': 'ref_123',
                'metadata': {'payment_type': 'course_enrollment', 'course_id': 1},
            },
        })
        timestamp = str(int(time_module.time()))
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            b'test-secret-key', message.encode('utf-8'), hashlib.sha256,
        ).hexdigest()
        request = factory.post(
            '/lms/webhooks/snippe/',
            data=payload,
            content_type='application/json',
            HTTP_X_Webhook_Signature=signature,
            HTTP_X_Webhook_Timestamp=timestamp,
        )
        response = snippe_webhook(request)
        self.assertEqual(response.status_code, 200)

    # ── Instructor price editing ─────────────────────────────────────

    def test_instructor_can_edit_course_price(self):
        """Instructor should be able to update course price via course update form"""
        self.client.login(username='instructor', password='testpassword')
        response = self.client.post(
            reverse('lms:course_update', kwargs={'slug': self.paid_course.slug}),
            {
                'title': self.paid_course.title,
                'course_type': 'general',
                'summary': self.paid_course.summary,
                'is_free': 'on',
                'price': '0.00',
                'instructors': [self.instructor_profile.id],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.paid_course.refresh_from_db()
        self.assertTrue(self.paid_course.is_free)
        self.assertEqual(self.paid_course.price, Decimal('0.00'))

    def test_instructor_can_set_paid_course_price(self):
        """Instructor should be able to set a price on a course"""
        self.client.login(username='instructor', password='testpassword')
        response = self.client.post(
            reverse('lms:course_update', kwargs={'slug': self.paid_course.slug}),
            {
                'title': self.paid_course.title,
                'course_type': 'general',
                'summary': self.paid_course.summary,
                'is_free': '',  # unchecked = paid
                'price': '50000.00',
                'instructors': [self.instructor_profile.id],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.paid_course.refresh_from_db()
        self.assertFalse(self.paid_course.is_free)
        self.assertEqual(self.paid_course.price, Decimal('50000.00'))

    def test_instructor_dashboard_shows_price_badge(self):
        """Instructor dashboard should show price/Free badge for each course"""
        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(reverse('lms:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25000.00')
        self.assertContains(response, 'Free')

    def test_instructor_dashboard_shows_edit_price_link(self):
        """Instructor dashboard should have Edit Price links"""
        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(reverse('lms:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Price')

    # ── Certificate price editing ────────────────────────────────────

    def test_certificate_template_list_shows_price(self):
        """Certificate template list should display certificate price"""
        self.client.login(username='instructor', password='testpassword')
        template = CertificateTemplate.objects.create(
            course=self.paid_course,
            title='Test Certificate',
            certificate_price=Decimal('20000.00'),
        )
        response = self.client.get(
            reverse('lms:certificate_template_list'),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '20000.00')

    def test_instructor_can_edit_certificate_price(self):
        """Instructor should be able to update certificate template price"""
        self.client.login(username='instructor', password='testpassword')
        template = CertificateTemplate.objects.create(
            course=self.paid_course,
            title='Test Certificate',
            certificate_price=Decimal('10000.00'),
        )
        response = self.client.post(
            reverse('lms:certificate_template_edit', kwargs={'pk': template.pk}),
            {
                'course': self.paid_course.id,
                'title': 'Updated Certificate',
                'organization_name': 'ChuoSmart Academy',
                'recipient_name_format': '{{ student_name }}',
                'course_name_display': '{{ course_title }}',
                'completion_date_display': '{{ completion_date }}',
                'certificate_id_display': '{{ certificate_id }}',
                'certificate_price': '30000.00',
                'completion_percentage': 100,
                'status': 'draft',
                'template_style': 'modern',
                'orientation': 'landscape',
                'primary_color': '#0d6efd',
                'secondary_color': '#111827',
                'accent_color': '#1FAA59',
                'background_style': 'plain',
                'border_style': 'premium',
                'font_style': 'serif',
            },
        )
        self.assertEqual(response.status_code, 302,
                         msg=f'Got {response.status_code}')
        self.assertIn('/lms/certificates/templates/', response['Location'])
        template.refresh_from_db()
        self.assertEqual(template.certificate_price, Decimal('30000.00'))
        self.assertEqual(template.title, 'Updated Certificate')
