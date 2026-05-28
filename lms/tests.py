from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .ai_assessments import ensure_module_assessment
from .models import Course, CourseContent, CourseEnrollment, LMSProfile, CourseModule, ContentAccess, QuizTaker
from .utils import is_module_unlocked, update_module_content_completion, update_module_assessment_completion


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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

    @override_settings(CEREBRAS_API_KEY=None)
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

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['module_states'][0]['skip_assessment'])
        self.assertTrue(response.context['module_states'][0]['completed'])
        self.assertTrue(response.context['module_states'][1]['unlocked'])
        self.assertIsNone(response.context['module_states'][0]['assessment'])
        self.assertIsNotNone(response.context['module_states'][1]['assessment'])
        self.assertContains(response, 'Open Assessment')

    @override_settings(CEREBRAS_API_KEY=None)
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

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['module_states'][1]['unlocked'])
        self.assertIsNotNone(response.context['module_states'][1]['assessment'])
        self.assertContains(response, 'Open Assessment')
        self.assertIn('aria-disabled="true"', response.content.decode())
        self.assertNotIn(f'data-bs-target="#collapse{second_module.id}"', response.content.decode())
