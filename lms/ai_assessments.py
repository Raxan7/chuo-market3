"""AI-assisted module assessment generation."""

import json
import logging
import re
import time

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone as django_timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import ActivityLog, Choice, MCQuestion, Quiz
from .agentic_ai import AgenticAIError, chat_completion, gateway_configured

logger = logging.getLogger(__name__)

DEFAULT_QUESTION_COUNT = 5


def _log_assessment_event(message, level='info'):
    log_method = getattr(logger, level, logger.info)
    log_method(message)

    try:
        ActivityLog.objects.create(message=Truncator(str(message)).chars(500))
    except Exception:
        logger.exception("Could not write LMS assessment activity log: %s", message)


def _clean_text(text):
    """Strip HTML, collapse whitespace, remove empty lines."""
    text = strip_tags(text or '')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def collect_module_learning_context(module, student=None):
    """
    Collect course/module content only.
    Student personalization is intentionally ignored so each module has one shared quiz.
    """
    parts = [
        f"Course: {module.course.title}",
        f"Module: {module.title}",
        f"Module description: {_clean_text(module.description or '')}",
    ]

    for content in module.contents.order_by('order', 'id'):
        body = ''

        if content.content_type == 'text':
            body = _clean_text(content.text_content or '')
        elif content.content_type == 'link':
            body = (content.external_link or '').strip()
        elif content.content_type == 'video':
            body = (content.video_url or '').strip()
        elif content.document:
            body = f"Document resource: {content.document.name}"

        parts.append(f"Content item: {content.title}\n{body}")

    limit = getattr(settings, 'AI_ASSESSMENT_CONTEXT_LIMIT', getattr(settings, 'CEREBRAS_CONTEXT_LIMIT', 8000))
    context = Truncator("\n\n".join(parts)).chars(limit)

    logger.info(
        "Collected module context module_id=%s context_chars=%s limit=%s",
        getattr(module, 'id', '?'),
        len(context or ''),
        limit,
    )

    return context


def _get_existing_assessment_quiz(module, student=None):
    """Return the active assessment quiz for this module/student scope."""
    qs = Quiz.objects.filter(module=module, draft=False)
    if student is None:
        qs = qs.filter(generated_for__isnull=True)
    else:
        qs = qs.filter(generated_for=student)
    return qs.order_by('id').first()


def _create_assessment_quiz(module, student=None):
    """Create an assessment shell, personalized when a learner is supplied."""
    return Quiz.objects.create(
        course=module.course,
        module=module,
        generated_for=student,
        title=f"{module.title} Mastery Check",
        description=(
            "Assessment based on this module's content. "
            "Score 70% or higher to unlock the next module."
        ),
        category='practice',
        pass_mark=70,
        answers_at_end=True,
        exam_paper=True,
        draft=False,
        generation_status='processing',
        generation_message='Quiz is being prepared.',
        generation_started_at=django_timezone.now(),
    )


def _get_or_create_assessment_quiz(module, student=None):
    """Get/create one active assessment per module and learner scope."""
    existing = _get_existing_assessment_quiz(module, student=student)
    scope = Quiz.objects.filter(module=module, draft=False)
    if student is None:
        scope = scope.filter(generated_for__isnull=True)
    else:
        scope = scope.filter(generated_for=student)

    if existing:
        scope.exclude(pk=existing.pk).update(
            draft=True,
            generation_message='Archived duplicate assessment quiz.',
        )
        return existing, False

    defaults = {
        'course': module.course,
        'title': f"{module.title} Mastery Check",
        'description': (
            "Assessment based on this module's content. "
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
            generated_for=student,
            draft=False,
            defaults=defaults,
        )
    except IntegrityError:
        quiz = _get_existing_assessment_quiz(module, student=student)
        if quiz is None:
            raise
        created = False

    scope.exclude(pk=quiz.pk).update(
        draft=True,
        generation_message='Archived duplicate assessment quiz.',
    )

    if created:
        scope_label = f'learner {student.id}' if student else 'shared'
        _log_assessment_event(
            f"Created {scope_label} AI quiz shell for module {module.id}."
        )

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
    ])


def _build_quiz_prompt(module, context, question_count):
    return f"""
You are generating a quiz for an online course module.

Return ONLY valid minified JSON.
Do not use Markdown.
Do not use code fences.
Do not add explanations outside JSON.
Do not use trailing commas.
Do not use newline characters inside string values.
Do not include unescaped quotation marks inside question, choice, or explanation text.

Generate exactly {question_count} multiple choice questions.

Rules:
- Use ONLY the module content provided.
- Each question must test useful understanding.
- Each question must have exactly 4 choices.
- Only one choice must be correct.
- correct_index must be 0, 1, 2, or 3.
- Keep each question under 160 characters.
- Keep each choice under 100 characters.
- Keep each explanation under 180 characters.
- Use simple clear language.
- If the module content is Swahili, write the quiz in Swahili.
- If the module content is English, write the quiz in English.

Return exactly this JSON shape:
{{"questions":[{{"question":"Question text","choices":["Choice A","Choice B","Choice C","Choice D"],"correct_index":0,"explanation":"Brief explanation"}}]}}

MODULE TITLE:
{module.title}

MODULE CONTENT:
{context}
""".strip()


def _strip_reasoning_blocks(text):
    """
    Remove reasoning/thinking blocks that some OpenAI-compatible gateways
    concatenate into message.content ahead of the real answer.
    """
    cleaned = re.sub(
        r'<(think|thinking|reasoning|reflection|scratchpad)\b[^>]*>.*?</\1\s*>',
        ' ',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Unclosed trailing reasoning block: everything from the tag onwards is reasoning.
    cleaned = re.sub(
        r'<(?:think|thinking|reasoning|reflection|scratchpad)\b[^>]*>.*\Z',
        ' ',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return cleaned.strip()


def _iter_json_candidates(text):
    """
    Yield balanced ``{...}`` substrings, outermost first, ignoring braces that
    appear inside JSON string literals.
    """
    length = len(text)
    index = 0

    while index < length:
        if text[index] != '{':
            index += 1
            continue

        depth = 0
        in_string = False
        escaped = False
        cursor = index

        while cursor < length:
            char = text[cursor]

            if in_string:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        yield text[index:cursor + 1]
                        index = cursor + 1
                        break

            cursor += 1
        else:
            return


def _close_truncated_json(text):
    """
    Best-effort recovery of a payload cut off by max_tokens.
    Rewinds to the last complete array element and closes the brackets that
    were still open at that point.
    """
    start = text.find('{')
    if start == -1:
        return None

    stack = []
    in_string = False
    escaped = False
    # (end_index, stack_snapshot) of the last point we can safely cut at.
    safe_cut = None
    cursor = start

    while cursor < len(text):
        char = text[cursor]

        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in '{[':
                stack.append('}' if char == '{' else ']')
            elif char in '}]':
                if not stack:
                    break
                stack.pop()
                if not stack:
                    # Whole payload completed after all.
                    return None
                if stack[-1] == ']':
                    # Just finished an element of the enclosing array.
                    safe_cut = (cursor + 1, list(stack))
            elif char == ',' and stack and stack[-1] == ']':
                safe_cut = (cursor, list(stack))

        cursor += 1

    if safe_cut is None:
        return None

    cut_index, cut_stack = safe_cut
    body = text[start:cut_index].rstrip().rstrip(',').rstrip()

    return body + ''.join(reversed(cut_stack))


def _extract_json_object(text):
    """
    Try to extract a valid JSON object from model output.
    Handles code fences, reasoning preambles, leading/trailing commentary and
    common LLM JSON errors. Recovers truncated payloads when possible.
    """
    if not text:
        raise ValueError('empty response from AI provider')

    text = str(text).strip()
    text = _strip_reasoning_blocks(text)

    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    def _attempt_parse(raw):
        raw = raw.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    result = _attempt_parse(text)
    if result is not None:
        return result

    for candidate in _iter_json_candidates(text):
        result = _attempt_parse(candidate)
        if result is not None:
            return result

        repaired = _attempt_parse(_repair_json_strings(candidate))
        if repaired is not None:
            return repaired

    salvaged = _close_truncated_json(text)
    if salvaged:
        result = _attempt_parse(salvaged)
        if result is not None:
            return result

        result = _attempt_parse(_repair_json_strings(salvaged))
        if result is not None:
            return result

    raise ValueError(f'invalid JSON from AI provider: {text[:200]}')


def _repair_json_strings(text):
    """
    Attempt basic repair of common JSON issues from LLM output:
    - Unescaped quotes inside string values
    """
    result = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == '\\':
            result.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "'":
            result.append("'")
            continue
        if in_string and ch == '\n':
            result.append('\\n')
            continue
        result.append(ch)
    return ''.join(result)


def _normalise_questions(raw_payload, question_count):
    if not raw_payload or not isinstance(raw_payload, dict):
        return []

    questions = raw_payload.get('questions', [])
    if not isinstance(questions, list):
        return []

    normalised = []

    for item in questions:
        if not isinstance(item, dict):
            continue

        question_text = str(item.get('question', '')).strip()
        choices = item.get('choices') or []
        explanation = str(item.get('explanation', '')).strip()

        if not question_text:
            continue

        if not isinstance(choices, list):
            continue

        choices = [str(choice).strip() for choice in choices[:4]]

        if len(choices) != 4:
            continue

        if not all(choices):
            continue

        correct_index = item.get('correct_index', 0)

        try:
            correct_index = int(correct_index)
        except (TypeError, ValueError):
            correct_index = 0

        if correct_index < 0 or correct_index > 3:
            correct_index = 0

        normalised.append({
            'question': question_text,
            'choices': choices,
            'correct_index': correct_index,
            'explanation': explanation,
        })

        if len(normalised) >= question_count:
            break

    return normalised


def _is_rate_or_quota_error(exc):
    text = str(exc).lower()
    name = type(exc).__name__.lower()

    markers = [
        'ratelimit',
        'rate limit',
        'too many requests',
        '429',
        'quota',
        'too_many',
        'token_quota_exceeded',
        'tokens per day',
    ]

    return any(marker in text or marker in name for marker in markers)


def _call_cerebras_for_questions(module, context, question_count):
    """
    Call Cerebras API and return:
    (payload_dict, status, message)

    Status values:
    - success
    - missing_api_key
    - sdk_error
    - rate_limited
    - api_error
    - invalid_json
    """
    api_key = getattr(settings, 'CEREBRAS_API_KEY', None)
    model = getattr(settings, 'CEREBRAS_ASSESSMENT_MODEL', 'zai-glm-4.7')
    max_tokens = getattr(settings, 'CEREBRAS_ASSESSMENT_MAX_TOKENS', 1400)

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

    prompt = _build_quiz_prompt(module, context, question_count)
    client = Cerebras(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": (
                "You return only valid JSON. No Markdown. No code fences. "
                "No extra commentary."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    last_json_error = None

    for attempt in range(1, 3):
        try:
            logger.info(
                "Cerebras request starting module_id=%s attempt=%s/2 model=%s context_chars=%s prompt_chars=%s max_tokens=%s",
                getattr(module, 'id', '?'),
                attempt,
                model,
                len(context or ''),
                len(prompt or ''),
                max_tokens,
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                max_tokens=max_tokens,
            )

            payload = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            logger.info(
                "Cerebras response received module_id=%s attempt=%s/2 payload_chars=%s finish_reason=%s payload_preview=%s",
                getattr(module, 'id', '?'),
                attempt,
                len(str(payload or '')),
                finish_reason,
                str(payload or '')[:250],
            )

            if payload is None:
                raise ValueError(
                    f"empty response from AI provider (finish_reason={finish_reason}). "
                    "Try increasing CEREBRAS_ASSESSMENT_MAX_TOKENS."
                )

            parsed = _extract_json_object(payload)

            logger.info(
                "Cerebras JSON parsed module_id=%s attempt=%s/2 questions_raw=%s",
                getattr(module, 'id', '?'),
                attempt,
                len(parsed.get('questions', [])) if isinstance(parsed, dict) else 'not_dict',
            )

            return parsed, 'success', 'ok'

        except Exception as exc:
            if _is_rate_or_quota_error(exc):
                msg = (
                    f"Module {getattr(module, 'id', '?')}: Cerebras rate/quota limit reached: "
                    f"{type(exc).__name__}: {exc}"
                )
                logger.warning(msg)
                return None, 'rate_limited', msg

            last_json_error = exc
            msg = f"Module {getattr(module, 'id', '?')}: invalid JSON from Cerebras: {exc}"
            logger.error(msg)

            if attempt == 1:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You repair invalid JSON. Return only valid minified JSON. "
                            "No Markdown. No explanations."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "The previous response was invalid JSON. "
                            "Regenerate the quiz as valid minified JSON only. "
                            "No Markdown. No code fences. No trailing commas. "
                            "Exactly this schema: "
                            '{"questions":[{"question":"Question text","choices":["Choice A","Choice B","Choice C","Choice D"],"correct_index":0,"explanation":"Brief explanation"}]}'
                            f"\n\nGenerate exactly {question_count} questions."
                            f"\n\nMODULE TITLE:\n{module.title}"
                            f"\n\nMODULE CONTENT:\n{context}"
                        ),
                    },
                ]
                continue

    final_msg = (
        f"Module {getattr(module, 'id', '?')}: invalid JSON from Cerebras after retries: "
        f"{last_json_error}"
    )
    return None, 'invalid_json', final_msg


def _build_json_repair_messages(module, context, question_count):
    """Retry prompt used when a provider returns reasoning text instead of JSON."""
    return [
        {
            'role': 'system',
            'content': (
                'You output one raw JSON object and nothing else. '
                'Do not think out loud, do not describe your plan, do not repeat the instructions. '
                'The first characters of your reply must be { and the last character must be }.'
            ),
        },
        {
            'role': 'user',
            'content': (
                'Your previous reply was not valid JSON. '
                'Regenerate the quiz now. Output only the minified JSON object, '
                'no Markdown, no code fences, no trailing commas, no commentary. '
                'Use exactly this schema: '
                '{"questions":[{"question":"Question text",'
                '"choices":["Choice A","Choice B","Choice C","Choice D"],'
                '"correct_index":0,"explanation":"Brief explanation"}]}'
                f"\n\nGenerate exactly {question_count} questions."
                f"\n\nMODULE TITLE:\n{module.title}"
                f"\n\nMODULE CONTENT:\n{context}"
            ),
        },
    ]


def _is_transient_gateway_error(exc):
    """
    429/5xx responses and network blips from the free-tier gateway are temporary.
    These are worth retrying in-process; a hard 4xx is not.
    """
    if not isinstance(exc, AgenticAIError):
        return False

    if exc.rate_limited:
        return True

    status_code = exc.status_code
    if isinstance(status_code, int) and 500 <= status_code < 600:
        return True

    return 'network error' in str(exc).lower()


def _call_agentic_gateway_for_questions(module, context, question_count):
    """Call the multi-provider agentic AI gateway and return the legacy status tuple."""
    if not gateway_configured():
        msg = f"Module {getattr(module, 'id', '?')}: agentic AI gateway is not configured"
        logger.warning(msg)
        return None, 'missing_api_key', msg

    prompt = _build_quiz_prompt(module, context, question_count)
    messages = [
        {
            'role': 'system',
            'content': (
                'You generate accurate course assessments grounded only in the supplied module content. '
                'Reply with one raw JSON object only. No Markdown, no code fences, no commentary, '
                'and do not include your reasoning.'
            ),
        },
        {'role': 'user', 'content': prompt},
    ]

    base_max_tokens = int(getattr(settings, 'AI_ASSESSMENT_MAX_TOKENS', 4000) or 4000)
    max_attempts = int(getattr(settings, 'AI_ASSESSMENT_MAX_ATTEMPTS', 3) or 3)
    backoff = float(getattr(settings, 'AI_ASSESSMENT_RETRY_BACKOFF_SECONDS', 2.0) or 0)
    last_json_error = None

    for attempt in range(1, max_attempts + 1):
        # Reasoning models spend part of the budget on thinking, so grow the
        # allowance on each retry to leave room for the JSON body itself.
        max_tokens = base_max_tokens * attempt

        try:
            payload_text, meta = chat_completion(
                messages,
                route=getattr(settings, 'AGENTIC_AI_ROUTE', 'structured'),
                temperature=0.0,
                max_tokens=max_tokens,
                response_format={'type': 'json_object'},
            )

            logger.info(
                'Agentic AI response module_id=%s attempt=%s/%s provider=%s model=%s '
                'payload_chars=%s finish_reason=%s payload_preview=%s',
                getattr(module, 'id', '?'),
                attempt,
                max_attempts,
                meta.get('provider'),
                meta.get('model'),
                len(payload_text or ''),
                meta.get('finish_reason'),
                str(payload_text or '')[:300],
            )

            parsed = _extract_json_object(payload_text)

            logger.info(
                'Agentic AI JSON parsed module_id=%s attempt=%s/%s questions_raw=%s',
                getattr(module, 'id', '?'),
                attempt,
                max_attempts,
                len(parsed.get('questions', [])) if isinstance(parsed, dict) else 'not_dict',
            )

            return parsed, 'success', (
                f"provider={meta.get('provider') or 'unknown'} model={meta.get('model') or 'unknown'}"
            )

        except AgenticAIError as exc:
            if _is_transient_gateway_error(exc) and attempt < max_attempts:
                delay = backoff * attempt
                logger.warning(
                    'Module %s: agentic AI gateway transient failure (attempt %s/%s): %s. '
                    'Retrying in %ss. body=%s',
                    getattr(module, 'id', '?'),
                    attempt,
                    max_attempts,
                    exc,
                    delay,
                    str(exc.response_body or '')[:200],
                )
                if delay > 0:
                    time.sleep(delay)
                continue

            status = 'rate_limited' if exc.rate_limited else 'api_error'
            msg = (
                f"Module {getattr(module, 'id', '?')}: agentic AI gateway failed after "
                f"{attempt} attempt(s): {exc}"
            )
            logger.warning(msg)
            return None, status, msg
        except ValueError as exc:
            last_json_error = exc
            msg = (
                f"Module {getattr(module, 'id', '?')}: invalid JSON from agentic AI gateway "
                f"(attempt {attempt}/{max_attempts}): {exc}"
            )
            logger.warning(msg)
            messages = _build_json_repair_messages(module, context, question_count)
        except Exception as exc:
            msg = f"Module {getattr(module, 'id', '?')}: unexpected agentic AI error: {type(exc).__name__}: {exc}"
            logger.exception(msg)
            return None, 'api_error', msg

    final_msg = (
        f"Module {getattr(module, 'id', '?')}: invalid JSON from agentic AI gateway "
        f"after {max_attempts} attempts: {last_json_error}"
    )
    return None, 'invalid_json', final_msg


def _call_configured_ai_for_questions(module, context, question_count):
    """Use the configured quiz provider, preferring the multi-provider gateway in auto mode."""
    provider = getattr(settings, 'AI_ASSESSMENT_PROVIDER', 'auto').strip().lower()

    if provider not in {'auto', 'agentic', 'cerebras'}:
        return None, 'api_error', f"Unsupported AI_ASSESSMENT_PROVIDER={provider!r}"

    if provider in {'auto', 'agentic'} and gateway_configured():
        return _call_agentic_gateway_for_questions(module, context, question_count)

    if provider == 'agentic':
        return None, 'missing_api_key', 'Agentic AI gateway selected but AGENTIC_AI_BASE_URL/API_KEY are not configured.'

    if provider in {'auto', 'cerebras'} and getattr(settings, 'CEREBRAS_API_KEY', None):
        return _call_cerebras_for_questions(module, context, question_count)

    if provider == 'cerebras':
        return None, 'missing_api_key', 'Cerebras selected but CEREBRAS_API_KEY is not configured.'

    return None, 'missing_api_key', 'No AI quiz provider is configured.'


def ensure_module_assessment(module, student=None, question_count=DEFAULT_QUESTION_COUNT, force=False):
    """
    Generate one shared AI quiz for a module.
    No fallback questions are created. Bad AI output fails the job instead of creating bogus quizzes.
    """
    _log_assessment_event(
        f"AI generation started for module {module.id} ({module.title}), "
        f"question_count={question_count}, force={force}."
    )

    if getattr(module, 'skip_assessment', False):
        _log_assessment_event(
            f"Skipped AI quiz generation for module {module.id} ({module.title}) because skip_assessment is enabled."
        )
        return None

    existing = _get_existing_assessment_quiz(module, student=student)

    if existing and existing.questions.exists() and not force and existing.generation_status == 'ready':
        logger.info(
            "Reusing existing ready quiz quiz_id=%s module_id=%s questions=%s",
            existing.id,
            module.id,
            existing.questions.count(),
        )
        return existing

    if existing is None:
        existing, _ = _get_or_create_assessment_quiz(module, student=student)
    else:
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

    _log_assessment_event(
        f"Collected AI context for module {module.id}: {len(context or '')} characters."
    )

    provider_name = getattr(settings, 'AI_ASSESSMENT_PROVIDER', 'auto')
    _log_assessment_event(
        f"Calling configured AI provider for module {module.id}: provider={provider_name}."
    )

    raw_payload, status, msg = _call_configured_ai_for_questions(
        module,
        context,
        question_count,
    )

    _log_assessment_event(
        f"AI provider returned for module {module.id}: status={status}, message={str(msg)[:300]}."
    )

    if status == 'rate_limited':
        existing.generation_status = 'pending'
        existing.generation_message = 'AI quota/rate limit reached. Waiting to retry later.'
        existing.generation_completed_at = None
        existing.save(update_fields=[
            'generation_status',
            'generation_message',
            'generation_completed_at',
        ])

        raise RuntimeError(str(msg))

    if status != 'success' or not raw_payload:
        if getattr(settings, 'AI_ASSESSMENT_ALLOW_DETERMINISTIC_FALLBACK', False):
            from .management.commands.fallback_pending_quiz_jobs import build_fallback_questions

            fallback_questions = build_fallback_questions(module)[:question_count]
            with transaction.atomic():
                existing.questions.all().delete()
                for order, item in enumerate(fallback_questions, start=1):
                    question = MCQuestion.objects.create(
                        quiz=existing,
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
            _mark_quiz_generation_state(
                existing,
                'ready',
                'Emergency deterministic fallback is ready. Regenerate with AI before normal production use.',
            )
            existing.ai_generated = False
            existing.save(update_fields=['ai_generated'])
            logger.warning(
                'Using deterministic fallback assessment module_id=%s student_id=%s status=%s',
                module.id, getattr(student, 'id', None), status,
            )
            return existing

        error_message = (
            f"AI quiz generation failed for module {module.id} "
            f"with status '{status}': {msg}"
        )

        logger.warning(error_message)

        existing.generation_status = 'failed'
        existing.generation_message = error_message[:500]
        existing.generation_completed_at = django_timezone.now()
        existing.save(update_fields=[
            'generation_status',
            'generation_message',
            'generation_completed_at',
        ])

        raise RuntimeError(error_message)

    questions = _normalise_questions(raw_payload, question_count)

    _log_assessment_event(
        f"Normalised {len(questions)} question(s) for module {module.id}; expected {question_count}."
    )

    if len(questions) < question_count:
        error_message = (
            f"AI quiz generation produced only {len(questions)} valid question(s) "
            f"for module {module.id}; expected {question_count}."
        )

        logger.warning(error_message)

        existing.generation_status = 'failed'
        existing.generation_message = error_message[:500]
        existing.generation_completed_at = django_timezone.now()
        existing.save(update_fields=[
            'generation_status',
            'generation_message',
            'generation_completed_at',
        ])

        raise RuntimeError(error_message)

    quiz = existing

    with transaction.atomic():
        deleted_count, _ = quiz.questions.all().delete()

        logger.info(
            "Deleted old quiz questions quiz_id=%s module_id=%s deleted_count=%s",
            quiz.id,
            module.id,
            deleted_count,
        )

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
    quiz.ai_generated = True
    quiz.save(update_fields=['ai_generated'])

    _log_assessment_event(
        f"AI quiz {quiz.id} is ready for module {module.id} ({module.title}) "
        f"with {quiz.questions.count()} question(s)."
    )

    return quiz


def ensure_course_module_assessments(course, student=None, question_count=DEFAULT_QUESTION_COUNT):
    quizzes = []

    for module in course.modules.exclude(skip_assessment=True).order_by('order', 'id'):
        quiz = queue_module_assessment_generation(
            module,
            student=student,
            question_count=question_count,
        )

        if quiz:
            quizzes.append(quiz)

    return quizzes


def queue_module_assessment_generation(module, student=None, question_count=DEFAULT_QUESTION_COUNT, force=False):
    """
    Queue quiz generation using the database-backed queue.
    The student argument is ignored so one shared quiz is created per module.
    """
    from .models import QuizGenerationJob

    if getattr(module, 'skip_assessment', False):
        logger.info(
            "Not queueing quiz generation for module_id=%s because skip_assessment=True",
            module.id,
        )
        return None

    # Deterministic fallback is opt-in only. Production defaults never publish
    # repeated placeholder quizzes just because the AI provider is unavailable.
    if getattr(settings, 'AI_ASSESSMENT_ALLOW_DETERMINISTIC_FALLBACK', False):
        has_ai_provider = gateway_configured() or bool(getattr(settings, 'CEREBRAS_API_KEY', None))
        if not has_ai_provider:
            return ensure_module_assessment(
                module, student=student, question_count=question_count, force=force
            )

    # The database-backed production queue currently generates one shared quiz
    # per module. Personalized offline assessments above remain learner-scoped.
    quiz = _get_existing_assessment_quiz(module)

    if quiz and quiz.generation_status == 'ready' and quiz.questions.exists() and not force:
        logger.info(
            "Not queueing module_id=%s because shared quiz_id=%s is already ready",
            module.id,
            quiz.id,
        )
        return quiz

    if not quiz:
        quiz, _ = _get_or_create_assessment_quiz(module)

    existing_job = QuizGenerationJob.objects.filter(
        module=module,
        status__in=['pending', 'processing'],
    ).order_by('id').first()

    if existing_job:
        existing_job.force = force or existing_job.force
        existing_job.question_count = question_count
        existing_job.attempts = 0
        existing_job.error = ''
        existing_job.status = 'pending'
        existing_job.locked_at = None
        existing_job.started_at = None
        existing_job.completed_at = None
        existing_job.save(update_fields=[
            'force',
            'question_count',
            'attempts',
            'error',
            'status',
            'locked_at',
            'started_at',
            'completed_at',
            'updated_at',
        ])

        job = existing_job
        created = False
    else:
        job = QuizGenerationJob.objects.create(
            module=module,
            force=force,
            question_count=question_count,
            status='pending',
            attempts=0,
            error='',
        )
        created = True

    quiz.generation_status = 'pending'
    quiz.generation_message = 'Scheduled for AI generation.'
    quiz.generation_completed_at = None
    quiz.save(update_fields=[
        'generation_status',
        'generation_message',
        'generation_completed_at',
    ])

    _log_assessment_event(
        f"Quiz generation job {'created' if created else 'updated'} for module {module.id}. "
        f"Job={job.id}, force={force}, question_count={question_count}."
    )

    return quiz