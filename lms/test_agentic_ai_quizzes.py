import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .agentic_ai import chat_completion
from .ai_assessments import ensure_module_assessment
from .models import Course, CourseContent, CourseModule, LMSProfile, Quiz


AI_QUIZ_JSON = json.dumps({
    'questions': [
        {
            'question': f'AI question {index}?',
            'choices': [f'Correct {index}', f'Wrong A {index}', f'Wrong B {index}', f'Wrong C {index}'],
            'correct_index': 0,
            'explanation': f'AI explanation {index}',
        }
        for index in range(1, 6)
    ]
})


@override_settings(
    AGENTIC_AI_BASE_URL='https://ai-gateway.example.test',
    AGENTIC_AI_API_KEY='test-gateway-key',
    AGENTIC_AI_TIMEOUT_SECONDS=5,
)
class AgenticGatewayClientContractTests(TestCase):
    @patch('lms.agentic_ai.request.urlopen')
    def test_openai_compatible_gateway_contract_is_parsed(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            'choices': [{'message': {'content': '{"questions": []}'}}],
            'gateway_meta': {'provider': 'gemini', 'model': 'gemini-3.8-flash'},
        }).encode('utf-8')
        urlopen.return_value.__enter__.return_value = response

        content, meta = chat_completion(
            [{'role': 'user', 'content': 'Return JSON'}],
            route='structured',
            response_format={'type': 'json_object'},
        )

        self.assertEqual(content, '{"questions": []}')
        self.assertEqual(meta['provider'], 'gemini')
        request_obj = urlopen.call_args.args[0]
        self.assertEqual(request_obj.full_url, 'https://ai-gateway.example.test/v1/chat/completions')
        self.assertEqual(request_obj.get_header('X-api-key'), 'test-gateway-key')
        sent = json.loads(request_obj.data.decode('utf-8'))
        self.assertEqual(sent['route'], 'structured')
        self.assertEqual(sent['response_format'], {'type': 'json_object'})

    @override_settings(AGENTIC_AI_BASE_URL='https://agentic-ai-engine.onrender.com/v1')
    @patch('lms.agentic_ai.request.urlopen')
    def test_gateway_base_url_may_already_include_v1(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            'choices': [{'message': {'content': '{"questions": []}'}}],
            'gateway_meta': {'provider': 'groq', 'model': 'test-model'},
        }).encode('utf-8')
        urlopen.return_value.__enter__.return_value = response

        chat_completion([{'role': 'user', 'content': 'Return JSON'}])

        request_obj = urlopen.call_args.args[0]
        self.assertEqual(
            request_obj.full_url,
            'https://agentic-ai-engine.onrender.com/v1/chat/completions',
        )


@override_settings(
    AGENTIC_AI_BASE_URL='https://ai-gateway.example.test',
    AGENTIC_AI_API_KEY='test-gateway-key',
    AI_ASSESSMENT_PROVIDER='agentic',
    AI_ASSESSMENT_ALLOW_DETERMINISTIC_FALLBACK=False,
)
class AgenticQuizGenerationTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title='AI Course', summary='AI course')
        self.module = CourseModule.objects.create(
            course=self.course,
            title='Grounded Module',
            description='Learn grounded facts from this module.',
            order=1,
        )
        CourseContent.objects.create(
            module=self.module,
            title='Lesson',
            content_type='text',
            text_content='Photosynthesis converts light energy into chemical energy in plants.',
            order=1,
        )

    @patch('lms.ai_assessments.chat_completion')
    def test_agentic_gateway_creates_real_ai_quiz_and_marks_it_ai_generated(self, chat_completion):
        chat_completion.return_value = (
            AI_QUIZ_JSON,
            {'provider': 'gemini', 'model': 'gemini-3.8-flash', 'attempts': [{'status': 'success'}]},
        )

        quiz = ensure_module_assessment(self.module, force=True)

        self.assertTrue(quiz.ai_generated)
        self.assertEqual(quiz.generation_status, 'ready')
        self.assertEqual(quiz.questions.count(), 5)
        self.assertEqual(quiz.questions.order_by('order').first().content, 'AI question 1?')
        chat_completion.assert_called_once()
        payload = chat_completion.call_args.args[0]
        self.assertIn('Photosynthesis', payload[1]['content'])

    @override_settings(AGENTIC_AI_BASE_URL='', AGENTIC_AI_API_KEY='')
    def test_missing_ai_provider_never_silently_publishes_deterministic_fallback(self):
        with self.assertRaises(RuntimeError):
            ensure_module_assessment(self.module, force=True)

        quiz = Quiz.objects.get(module=self.module, generated_for__isnull=True, draft=False)
        self.assertFalse(quiz.ai_generated)
        self.assertEqual(quiz.questions.count(), 0)
        self.assertEqual(quiz.generation_status, 'failed')


class InstructorModuleCrudTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user('teacher', password='pass12345')
        self.profile, _ = LMSProfile.objects.get_or_create(user=self.instructor, defaults={'role': 'instructor'})
        self.profile.role = 'instructor'
        self.profile.save(update_fields=['role'])
        self.course = Course.objects.create(title='Instructor Course', summary='Course')
        self.course.instructors.add(self.profile)
        self.module = CourseModule.objects.create(
            course=self.course,
            title='Module With Typo',
            description='Needs editing',
            order=1,
        )
        self.client.login(username='teacher', password='pass12345')

    def test_instructor_can_edit_module_from_module_route(self):
        url = reverse('lms:module_update', kwargs={
            'course_slug': self.course.slug,
            'module_id': self.module.id,
        })
        response = self.client.post(url, {
            'title': 'Corrected Module',
            'description': 'Corrected description',
            'order': 1,
            'skip_assessment': '',
        })

        self.assertEqual(response.status_code, 302)
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, 'Corrected Module')

    def test_delete_confirmation_renders_and_post_deletes_module(self):
        url = reverse('lms:module_delete', kwargs={
            'course_slug': self.course.slug,
            'module_id': self.module.id,
        })

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'Delete “Module With Typo”?')

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(CourseModule.objects.filter(pk=self.module.pk).exists())

    def test_course_page_exposes_edit_and_delete_controls_to_instructor(self):
        response = self.client.get(reverse('lms:course_detail', kwargs={'slug': self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Module')
        self.assertContains(response, 'Delete Module')
