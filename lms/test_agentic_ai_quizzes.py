import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .agentic_ai import chat_completion
from .ai_assessments import ensure_module_assessment, _extract_json_object
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


class ExtractJsonObjectTests(TestCase):
    def test_plain_json_is_returned_unchanged(self):
        payload = {'questions': [{'question': 'Q?'}]}
        self.assertEqual(_extract_json_object(json.dumps(payload)), payload)

    def test_reasoning_preamble_before_json_is_ignored(self):
        text = (
            'User Safety: safe\n'
            'We need to generate exactly 5 multiple choice questions '
            'based on the module content, which is in Swahili.\n'
            '{"questions":[{"question":"Je?"}]}'
        )
        self.assertEqual(_extract_json_object(text), {'questions': [{'question': 'Je?'}]})

    def test_think_block_wrapping_json_is_stripped(self):
        text = '<think>The user wants a quiz about {braces}</think>\n{"questions": []}'
        self.assertEqual(_extract_json_object(text), {'questions': []})

    def test_unclosed_think_block_keeps_trailing_json_out(self):
        with self.assertRaises(ValueError):
            _extract_json_object('<think>still reasoning {"questions": []}')

    def test_json_wrapped_in_code_fence_is_parsed(self):
        self.assertEqual(
            _extract_json_object('```json\n{"questions": []}\n```'),
            {'questions': []},
        )

    def test_nested_braces_inside_strings_do_not_break_extraction(self):
        text = 'Sure!\n{"questions":[{"question":"What is {JSON}?"}]}\nHope that helps.'
        self.assertEqual(
            _extract_json_object(text),
            {'questions': [{'question': 'What is {JSON}?'}]},
        )

    def test_truncated_payload_recovers_complete_questions(self):
        text = (
            '{"questions":['
            '{"question":"Q1","choices":["a","b","c","d"],"correct_index":0,"explanation":"E1"},'
            '{"question":"Q2","choices":["a","b","c","d"],"correct_index":1,"explanation":"E2"},'
            '{"question":"Q3 partial'
        )
        parsed = _extract_json_object(text)
        self.assertEqual(len(parsed['questions']), 2)
        self.assertEqual(parsed['questions'][1]['question'], 'Q2')

    def test_purely_non_json_output_raises(self):
        with self.assertRaises(ValueError):
            _extract_json_object('User Safety: safe')


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

    @patch('lms.ai_assessments.chat_completion')
    def test_reasoning_preamble_before_json_still_produces_a_quiz(self, chat_completion):
        chat_completion.return_value = (
            'User Safety: safe\nWe need to generate 5 questions.\n' + AI_QUIZ_JSON,
            {'provider': 'groq', 'model': 'qwen/qwen3.8-27b'},
        )

        quiz = ensure_module_assessment(self.module, force=True)

        self.assertTrue(quiz.ai_generated)
        self.assertEqual(quiz.questions.count(), 5)

    @patch('lms.ai_assessments.chat_completion')
    def test_invalid_json_is_retried_before_failing(self, chat_completion):
        chat_completion.side_effect = [
            ('User Safety: safe', {'provider': 'groq', 'model': 'qwen/qwen3.8-27b'}),
            (AI_QUIZ_JSON, {'provider': 'groq', 'model': 'qwen/qwen3.8-27b'}),
        ]

        quiz = ensure_module_assessment(self.module, force=True)

        self.assertTrue(quiz.ai_generated)
        self.assertEqual(chat_completion.call_count, 2)
        # The retry must ask for JSON explicitly rather than repeating the original prompt.
        retry_prompt = chat_completion.call_args_list[1].args[0][1]['content']
        self.assertIn('not valid JSON', retry_prompt)

    @patch('lms.ai_assessments.chat_completion')
    def test_persistently_invalid_json_fails_after_three_attempts(self, chat_completion):
        chat_completion.return_value = ('User Safety: safe', {'provider': 'groq'})

        with self.assertRaises(RuntimeError):
            ensure_module_assessment(self.module, force=True)

        self.assertEqual(chat_completion.call_count, 3)
        quiz = Quiz.objects.get(module=self.module, generated_for__isnull=True, draft=False)
        self.assertFalse(quiz.ai_generated)
        self.assertEqual(quiz.generation_status, 'failed')
        self.assertIn('after 3 attempts', quiz.generation_message)

    @patch('lms.ai_assessments.chat_completion')
    def test_retry_escalates_max_tokens(self, chat_completion):
        chat_completion.return_value = ('User Safety: safe', {'provider': 'groq'})

        with self.assertRaises(RuntimeError):
            ensure_module_assessment(self.module, force=True)

        tokens = [call.kwargs['max_tokens'] for call in chat_completion.call_args_list]
        self.assertEqual(tokens, sorted(tokens))
        self.assertGreater(tokens[-1], tokens[0])

    @override_settings(AGENTIC_AI_BASE_URL='', AGENTIC_AI_API_KEY='')
    def test_missing_ai_provider_never_silently_publishes_deterministic_fallback(self):
        with self.assertRaises(RuntimeError):
            ensure_module_assessment(self.module, force=True)

        quiz = Quiz.objects.get(module=self.module, generated_for__isnull=True, draft=False)
        self.assertFalse(quiz.ai_generated)
        self.assertEqual(quiz.questions.count(), 0)
        self.assertEqual(quiz.generation_status, 'failed')


class RegenerateAllQuizzesCommandTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title='Regen Course', summary='Regen course')

    def _module(self, title):
        return CourseModule.objects.create(
            course=self.course,
            title=title,
            description='Module description',
            order=CourseModule.objects.filter(course=self.course).count() + 1,
        )

    @patch('lms.management.commands.regenerate_all_quizzes.ensure_module_assessment')
    def test_continue_on_error_processes_every_module_and_reports_failures(self, ensure_assessment):
        first = self._module('First Module')
        second = self._module('Second Module')
        self._module('Third Module')

        def generate(module, **kwargs):
            if module.id == second.id:
                raise RuntimeError('invalid JSON from AI provider')
            return MagicMock(questions=MagicMock(count=MagicMock(return_value=5)))

        ensure_assessment.side_effect = generate

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command('regenerate_all_quizzes', '--continue-on-error', stdout=out, stderr=out)

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(ensure_assessment.call_count, 3)
        self.assertIn('Failed: 1 module(s)', out.getvalue())
        self.assertIn('Second Module', out.getvalue())

    @patch('lms.management.commands.regenerate_all_quizzes.ensure_module_assessment')
    def test_default_still_stops_at_first_failure(self, ensure_assessment):
        self._module('First Module')
        self._module('Second Module')
        ensure_assessment.side_effect = RuntimeError('invalid JSON from AI provider')

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command('regenerate_all_quizzes', stdout=out, stderr=out)

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(ensure_assessment.call_count, 1)


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
