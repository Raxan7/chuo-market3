from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .ai_assessments import ensure_module_assessment, queue_module_assessment_generation
from .models import Course, CourseContent, CourseEnrollment, LMSProfile, CourseModule, ContentAccess, QuizTaker, Quiz, MCQuestion, Choice, StudentAnswer, ModuleProgress
from .utils import is_module_unlocked, update_module_content_completion, update_module_assessment_completion


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

    def test_modules_with_default_order_still_lock_later_modules(self):
        first_module = CourseModule.objects.create(
            course=self.course,
            title='Module 1',
            description='First module',
        )
        second_module = CourseModule.objects.create(
            course=self.course,
            title='Module 2',
            description='Second module',
        )
        self._create_content(first_module)
        self._create_content(second_module, title='Lesson 2')

        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['module_states'][0]['unlocked'])
        self.assertFalse(response.context['module_states'][1]['unlocked'])
        self.assertContains(response, 'Prerequisite module: Module 1')

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
        self.assertFalse(progress.content_completed)
        self.assertGreaterEqual(float(progress.best_score), 70)
        self.assertFalse(progress.completed)
