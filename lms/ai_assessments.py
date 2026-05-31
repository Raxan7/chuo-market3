"""AI-assisted module assessment generation."""

import json
import logging
import re
import sys
import threading

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.db import transaction
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import Choice, MCQuestion, Quiz

logger = logging.getLogger(__name__)


DEFAULT_QUESTION_COUNT = 5


def _personalization_lines(student):
    if not student:
        return []

    display_name = student.user.get_full_name() or student.user.username
    return [
        f"Learner: {display_name}",
        f"Learner role: {getattr(student, 'role', 'student')}",
        f"Learner username: {student.user.username}",
    ]


def collect_module_learning_context(module, student=None):
    parts = [
        f"Course: {module.course.title}",
        f"Module: {module.title}",
        f"Module description: {strip_tags(module.description or '')}",
    ]
    parts.extend(_personalization_lines(student))
    for content in module.contents.order_by('order', 'id'):
        body = ''
        if content.content_type == 'text':
            body = strip_tags(content.text_content or '')
        elif content.content_type == 'link':
            body = content.external_link or ''
        elif content.content_type == 'video':
            body = content.video_url or ''
        elif content.document:
            body = f"Document resource: {content.document.name}"

        parts.append(f"Content item: {content.title}\n{body}")

    limit = getattr(settings, 'CEREBRAS_CONTEXT_LIMIT', 12000)
    return Truncator("\n\n".join(parts)).chars(limit)


def _get_existing_assessment_quiz(module, student=None):
    if student:
        personal_quiz = Quiz.objects.filter(
            module=module,
            generated_for=student,
            draft=False,
        ).order_by('-id').first()
        if personal_quiz:
            return personal_quiz

    return Quiz.objects.filter(module=module, draft=False).order_by('generated_for', 'id').first()


def _get_personal_assessment_quiz(module, student):
    if not student:
        return None

    return Quiz.objects.filter(
        module=module,
        generated_for=student,
        draft=False,
    ).order_by('-id').first()


def _create_assessment_quiz(module, student=None):
    return Quiz.objects.create(
        course=module.course,
        module=module,
        generated_for=student,
        title=f"{module.title} Mastery Check",
        description=(
            "AI-generated assessment based on this module's content. "
            "Score 70% or higher to unlock the next module."
        ),
        category='practice',
        pass_mark=70,
        answers_at_end=True,
        exam_paper=True,
        draft=False,
        generation_status='processing',
        generation_message='Quiz is being prepared.',
        generation_started_at=timezone.now(),
    )


def _mark_quiz_generation_state(quiz, status, message=''):
    quiz.generation_status = status
    quiz.generation_message = message or ''
    if status == 'processing' and not quiz.generation_started_at:
        quiz.generation_started_at = timezone.now()
    if status in {'ready', 'failed'}:
        quiz.generation_completed_at = timezone.now()
    quiz.save(update_fields=[
        'generation_status',
        'generation_message',
        'generation_started_at',
        'generation_completed_at',
        'slug',
        'course',
        'module',
        'generated_for',
        'title',
        'description',
        'category',
        'pass_mark',
        'answers_at_end',
        'exam_paper',
        'draft',
    ])


def _call_cerebras_for_questions(module, context, question_count):
    """Call Cerebras API and return (payload_dict, status, message).

    status is one of: 'success', 'missing_api_key', 'sdk_error', 'api_error', 'invalid_json'
    """
    api_key = getattr(settings, 'CEREBRAS_API_KEY', None)
    if not api_key:
        msg = f"Module {getattr(module, 'id', '?')}: missing CEREBRAS_API_KEY"
        logger.warning(msg)
        return None, 'missing_api_key', msg

    try:
        from cerebras.cloud.sdk import Cerebras
    except Exception as exc:
        msg = f"Module {getattr(module, 'id', '?')}: Cerebras SDK import failed: {exc}"
        logger.exception(msg)
        return None, 'sdk_error', msg

    prompt = f"""
You are creating a mastery check for an online course module.
Use ONLY the module content below. Generate exactly {question_count} multiple choice questions.
Each question must:
- Test deep understanding of the module content
- Have 4 distinct choices
- Have exactly one correct answer
- Include a brief learning explanation tied to the module content

Return ONLY valid JSON in this exact shape (no Markdown, no code fences):
{{"questions":[{{"question":"...","choices":["...","...","...","..."],"correct_index":0,"explanation":"..."}}]}}

MODULE CONTENT:
{context}
""".strip()

    def parse_payload(payload_text):
        if not payload_text:
            raise ValueError('empty response from Cerebras')

        text = str(payload_text).strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*```$', '', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start:end + 1])
            raise

    try:
        client = Cerebras(api_key=api_key)
        messages = [
            {"role": "system", "content": "Return valid JSON only. Do not wrap it in Markdown."},
            {"role": "user", "content": prompt},
        ]

        for attempt in range(2):
            response = client.chat.completions.create(
                model=getattr(settings, 'CEREBRAS_ASSESSMENT_MODEL', 'zai-glm-4.7'),
                messages=messages,
                temperature=0.0 if attempt else 0.2,
                max_tokens=3000,
            )
            payload = response.choices[0].message.content
            try:
                parsed = parse_payload(payload)
                return parsed, 'success', 'ok'
            except Exception as exc:
                msg = f"Module {getattr(module, 'id', '?')}: invalid JSON from Cerebras: {exc}"
                logger.error(msg)
                logger.debug("Payload start: %s", str(payload)[:500])
                if attempt == 0:
                    messages = [
                        {"role": "system", "content": "Return valid JSON only. Do not wrap it in Markdown."},
                        {
                            "role": "user",
                            "content": (
                                f"The previous response was invalid JSON. Re-answer using only valid JSON that matches this schema exactly: "
                                f'{{"questions":[{{"question":"...","choices":["...","...","...","..."],"correct_index":0,"explanation":"..."}}]}}\n\n'
                                f"MODULE CONTENT:\n{context}"
                            ),
                        },
                    ]
                    continue
                return None, 'invalid_json', msg
    except Exception as exc:
        msg = f"Module {getattr(module, 'id', '?')}: Cerebras API call failed: {type(exc).__name__}: {exc}"
        logger.exception(msg)
        return None, 'api_error', msg


def _fallback_questions(module, context, question_count):
    clean_context = re.sub(r'\s+', ' ', strip_tags(context)).strip()
    summary = Truncator(clean_context or module.description or module.title).chars(180)
    key_terms = [
        term.strip('.,;:()[]{}"\'')
        for term in re.findall(r'\b[A-Za-z][A-Za-z0-9-]{5,}\b', clean_context)
    ]
    unique_terms = []
    for term in key_terms:
        lower = term.lower()
        if lower not in {item.lower() for item in unique_terms}:
            unique_terms.append(term)
        if len(unique_terms) >= question_count:
            break

    if not unique_terms:
        unique_terms = [module.title] * question_count

    questions = []
    for index in range(question_count):
        term = unique_terms[index % len(unique_terms)]
        questions.append({
            "question": f"Based on this module, which statement best reflects the role of {term}?",
            "choices": [
                f"It is an important idea or resource discussed in {module.title}.",
                "It is unrelated to the module learning material.",
                "It should be ignored when applying the module concepts.",
                "It only appears as a random example with no learning value.",
            ],
            "correct_index": 0,
            "explanation": f"The module context connects this idea to the learning material: {summary}",
        })

    return {"questions": questions}


def _normalise_questions(raw_payload, question_count):
    if not raw_payload:
        return []

    questions = raw_payload.get('questions', []) if isinstance(raw_payload, dict) else []
    normalised = []
    for item in questions:
        choices = item.get('choices') or []
        if len(choices) < 2:
            continue
        correct_index = item.get('correct_index', 0)
        try:
            correct_index = int(correct_index)
        except (TypeError, ValueError):
            correct_index = 0
        correct_index = max(0, min(correct_index, len(choices) - 1))
        normalised.append({
            'question': str(item.get('question', '')).strip(),
            'choices': [str(choice).strip() for choice in choices[:4]],
            'correct_index': correct_index,
            'explanation': str(item.get('explanation', '')).strip(),
        })
        if len(normalised) >= question_count:
            break

    return [item for item in normalised if item['question'] and all(item['choices'])]


@transaction.atomic
def ensure_module_assessment(module, student=None, question_count=DEFAULT_QUESTION_COUNT, force=False):
    if getattr(module, 'skip_assessment', False):
        return None

    existing = _get_personal_assessment_quiz(module, student) if student else _get_existing_assessment_quiz(module, student=student)
    if existing and existing.questions.exists() and not force and existing.generation_status == 'ready':
        return existing

    if existing is None:
        existing = _create_assessment_quiz(module, student=student)
    elif force:
        existing.questions.all().delete()
        existing.generation_status = 'processing'
        existing.generation_message = 'Quiz is being prepared.'
        existing.generation_started_at = timezone.now()
        existing.generation_completed_at = None
        existing.save(update_fields=[
            'generation_status',
            'generation_message',
            'generation_started_at',
            'generation_completed_at',
        ])

    context = collect_module_learning_context(module, student=student)
    raw_payload, status, msg = _call_cerebras_for_questions(module, context, question_count)
    if status != 'success' or not raw_payload:
        logger.warning(
            f"Module {getattr(module, 'id', '?')}: AI generation failed ({status}), using fallback questions: {msg}"
        )
        fallback_payload = _fallback_questions(module, context, question_count)
        questions = _normalise_questions(fallback_payload, question_count)
    else:
        questions = _normalise_questions(raw_payload, question_count)

    if not questions:
        logger.warning(
            f"Module {getattr(module, 'id', '?')}: no valid questions generated, using fallback questions"
        )
        questions = _normalise_questions(_fallback_questions(module, context, question_count), question_count)

    quiz = existing

    if force or quiz.generation_status != 'ready':
        quiz.questions.all().delete()

    for order, item in enumerate(questions, start=1):
        question = MCQuestion.objects.create(
            quiz=quiz,
            content=item['question'],
            explanation=item['explanation'],
            order=order,
        )
        for choice_index, choice_text in enumerate(item['choices']):
            Choice.objects.create(
                question=question,
                content=choice_text,
                correct=choice_index == item['correct_index'],
            )

    _mark_quiz_generation_state(quiz, 'ready', 'Quiz is ready.')
    return quiz


def queue_module_assessment_generation(module, student=None, question_count=DEFAULT_QUESTION_COUNT):
    if getattr(module, 'skip_assessment', False):
        return None

    quiz = _get_personal_assessment_quiz(module, student) if student else _get_existing_assessment_quiz(module, student=student)
    if quiz and quiz.generation_status == 'ready' and quiz.questions.exists():
        return quiz

    if quiz is None:
        quiz = _create_assessment_quiz(module, student=student)
    else:
        quiz.generation_status = 'processing'
        quiz.generation_message = 'Quiz is being prepared.'
        quiz.generation_started_at = timezone.now()
        quiz.generation_completed_at = None
        quiz.save(update_fields=['generation_status', 'generation_message', 'generation_started_at', 'generation_completed_at'])

    module_id = module.id
    student_id = student.id if student else None

    if 'test' in sys.argv:
        from .models import CourseModule, LMSProfile

        module_obj = CourseModule.objects.get(pk=module_id)
        student_obj = LMSProfile.objects.filter(pk=student_id).first() if student_id else None
        return ensure_module_assessment(module_obj, student=student_obj, question_count=question_count, force=True)

    def worker():
        close_old_connections()
        try:
            from .models import CourseModule, LMSProfile

            module_obj = CourseModule.objects.get(pk=module_id)
            student_obj = LMSProfile.objects.filter(pk=student_id).first() if student_id else None
            ensure_module_assessment(module_obj, student=student_obj, question_count=question_count, force=True)
        except Exception as exc:
            logger.exception(
                "Module %s: background assessment generation failed for student %s: %s",
                module_id,
                student_id,
                exc,
            )
            if quiz.pk:
                Quiz.objects.filter(pk=quiz.pk).update(
                    generation_status='failed',
                    generation_message=str(exc),
                    generation_completed_at=timezone.now(),
                )
        finally:
            close_old_connections()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return quiz
