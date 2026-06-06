"""AI-assisted module assessment generation."""

import json
import logging
import re
import sys

from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone as django_timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import ActivityLog, Choice, MCQuestion, Quiz

logger = logging.getLogger(__name__)


DEFAULT_QUESTION_COUNT = 5


def _log_assessment_event(message, level='info'):
    log_method = getattr(logger, level, logger.info)
    log_method(message)
    try:
        from .models import ActivityLog
        ActivityLog.objects.create(message=Truncator(message).chars(500))
    except Exception:
        logger.exception("Could not write LMS assessment activity log: %s", message)

def collect_module_learning_context(module, student=None):
    """Collect content only. Student/personalization data removed for shared quizzes."""
    parts = [
        f"Course: {module.course.title}",
        f"Module: {module.title}",
        f"Module description: {strip_tags(module.description or '')}",
    ]
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
    """Always returns the shared (non-personalized) quiz for this module."""
    return Quiz.objects.filter(
        module=module,
        generated_for__isnull=True,
        draft=False,
    ).order_by('id').first()


def _create_assessment_quiz(module, student=None):
    """Creates a shared quiz shell."""
    return Quiz.objects.create(
        course=module.course,
        module=module,
        generated_for=None,
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
        generation_message='Preparation queued.',
        generation_started_at=django_timezone.now(),
    )


def _get_or_create_assessment_quiz(module, student=None):
    existing = _get_existing_assessment_quiz(module)
    if existing:
        return existing, False

    defaults = {
        'course': module.course,
        'title': f"{module.title} Mastery Check",
        'description': (
            "AI-generated assessment based on this module's content. "
            "Score 70% or higher to unlock the next module."
        ),
        'category': 'practice',
        'pass_mark': 70,
        'answers_at_end': True,
        'exam_paper': True,
        'generation_status': 'processing',
        'generation_message': 'Quiz is being prepared.',
        'generation_started_at': django_timezone.now(),
    }

    try:
        quiz, created = Quiz.objects.get_or_create(
            module=module,
            generated_for=None,
            draft=False,
            defaults=defaults,
        )
    except IntegrityError:
        quiz = _get_existing_assessment_quiz(module)
        created = False

    # Archive potential duplicates
    Quiz.objects.filter(module=module, generated_for__isnull=True, draft=False).exclude(pk=quiz.pk).update(draft=True)

    if created:
        _log_assessment_event(f"Created shared AI quiz shell for module {module.id}.")

    return quiz, created


def _mark_quiz_generation_state(quiz, status, message=''):
    quiz.generation_status = status
    quiz.generation_message = message or ''
    if status == 'processing' and not quiz.generation_started_at:
        quiz.generation_started_at = django_timezone.now()
    if status in {'ready', 'failed'}:
        quiz.generation_completed_at = django_timezone.now()
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
    clean_context = re.sub(r'\s+', ' ', strip_tags(context or '')).strip()
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


def ensure_module_assessment(module, student=None, question_count=DEFAULT_QUESTION_COUNT, force=False):
    """Primary worker function. Generates shared questions from API and updates the DB."""
    if getattr(module, 'skip_assessment', False):
        _log_assessment_event(
            "Skipped AI quiz generation for module %s (%s) because skip_assessment is enabled." % (
                module.id,
                module.title,
            )
        )
        return None

    existing = _get_existing_assessment_quiz(module)
    if existing and existing.questions.exists() and not force and existing.generation_status == 'ready':
        return existing

    if existing is None:
        existing, _ = _get_or_create_assessment_quiz(module, student=student)
    elif force:
        existing.generation_status = 'processing'
        existing.generation_message = 'Quiz is being prepared.'
        existing.generation_started_at = django_timezone.now()
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

    with transaction.atomic():
        quiz.questions.all().delete()
        for order, item in enumerate(questions, start=1):
            question = MCQuestion.objects.create(
                quiz=quiz, content=item['question'], explanation=item['explanation'], order=order
            )
            for choice_index, choice_text in enumerate(item['choices']):
                Choice.objects.create(
                    question=question, content=choice_text,
                    correct=choice_index == item['correct_index']
                )

    _mark_quiz_generation_state(quiz, 'ready', 'Quiz is ready.')
    _log_assessment_event(
        "AI quiz %s is ready for module %s (%s) with %s question(s)." % (
            quiz.id,
            module.id,
            module.title,
            quiz.questions.count(),
        )
    )
    return quiz


def ensure_course_module_assessments(course, student=None, question_count=DEFAULT_QUESTION_COUNT):
    quizzes = []
    for module in course.modules.exclude(skip_assessment=True).order_by('order', 'id'):
        quiz = queue_module_assessment_generation(module, student=student, question_count=question_count)
        if quiz:
            quizzes.append(quiz)

    return quizzes


def queue_module_assessment_generation(module, student=None, question_count=DEFAULT_QUESTION_COUNT, force=False):
    """Creates a QuizGenerationJob to be processed by cron. Request returns immediately."""
    from .models import QuizGenerationJob
    
    if getattr(module, 'skip_assessment', False):
        return None

    quiz = _get_existing_assessment_quiz(module)
    if quiz and quiz.generation_status == 'ready' and quiz.questions.exists() and not force:
        return quiz

    if not quiz:
        quiz, _ = _get_or_create_assessment_quiz(module)

    # Create or update the job
    job, created = QuizGenerationJob.objects.update_or_create(
        module=module,
        status__in=['pending', 'processing'],
        defaults={
            'force': force,
            'question_count': question_count,
            'status': 'pending',
            'attempts': 0,
            'error': None
        }
    )
    
    # Sync Quiz status to shell
    quiz.generation_status = 'pending'
    quiz.generation_message = 'Scheduled for AI generation.'
    quiz.save(update_fields=['generation_status', 'generation_message'])
    
    _log_assessment_event(f"Job queued for module {module.id}. Force={force}.")
    return quiz
