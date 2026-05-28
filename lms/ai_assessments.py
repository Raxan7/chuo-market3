"""AI-assisted module assessment generation."""

import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import Choice, MCQuestion, Quiz

logger = logging.getLogger(__name__)


DEFAULT_QUESTION_COUNT = 5


def collect_module_learning_context(module):
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

    return Truncator("\n\n".join(parts)).chars(12000)


def _call_cerebras_for_questions(module, context, question_count):
    api_key = getattr(settings, 'CEREBRAS_API_KEY', None)
    if not api_key:
        return None

    try:
        from cerebras.cloud.sdk import Cerebras
    except Exception:
        logger.exception("Cerebras SDK is unavailable; using fallback assessment generator.")
        return None

    prompt = f"""
You are creating a mastery check for an online course module.
Use only the module content below. Generate exactly {question_count} multiple choice questions.
Each question must test understanding, not trivia. Each item must have 4 choices, exactly one correct answer, and a short explanation.
Return strict JSON only in this shape:
{{"questions":[{{"question":"...","choices":["...","...","...","..."],"correct_index":0,"explanation":"..."}}]}}

MODULE CONTENT:
{context}
""".strip()

    try:
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            model=getattr(settings, 'CEREBRAS_ASSESSMENT_MODEL', 'llama3.1-8b'),
            messages=[
                {"role": "system", "content": "Return valid JSON only. Do not wrap it in Markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        payload = response.choices[0].message.content
        return json.loads(payload)
    except Exception:
        logger.exception("AI assessment generation failed; using fallback assessment generator.")
        return None


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
def ensure_module_assessment(module, question_count=DEFAULT_QUESTION_COUNT, force=False):
    if getattr(module, 'skip_assessment', False):
        return None

    existing = Quiz.objects.filter(module=module, draft=False).order_by('id').first()
    if existing and existing.questions.exists() and not force:
        return existing

    context = collect_module_learning_context(module)
    raw_payload = _call_cerebras_for_questions(module, context, question_count)
    questions = _normalise_questions(raw_payload, question_count)
    if len(questions) < question_count:
        questions = _normalise_questions(_fallback_questions(module, context, question_count), question_count)

    quiz = existing or Quiz.objects.create(
        course=module.course,
        module=module,
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
    )

    if force:
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

    return quiz
