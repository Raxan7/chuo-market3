import json
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from lms.models import Course

logger = logging.getLogger(__name__)

RECOMMENDATION_CACHE_HOURS = 24
MAX_RECOMMENDATIONS = 3
MIN_FALLBACK_SCORE = 6

FIELD_SEPARATOR = '---FIELD_SEP---'
ITEM_SEPARATOR = '---ITEM_SEP---'

SKILL_TITLE_BOOST = 10
SKILL_SUMMARY_BOOST = 6
SKILL_CONTENT_BOOST = 4
INDUSTRY_BOOST = 3
KEYWORD_TITLE_BOOST = 2
KEYWORD_CONTENT_BOOST = 1


def get_recommendations(job):
    """Get course recommendations for a job. Returns list of (course, reason, source)."""
    from .models import JobCourseRecommendation

    cache_horizon = timezone.now() - timedelta(hours=RECOMMENDATION_CACHE_HOURS)

    try:
        cached = JobCourseRecommendation.objects.prefetch_related('courses').get(job=job)
        if cached.updated_at >= cache_horizon:
            courses = list(cached.courses.all())
            reasons = cached.reasons or {}
            source = cached.source
            return [(c, reasons.get(str(c.id), ''), source) for c in courses]
    except JobCourseRecommendation.DoesNotExist:
        pass

    result = _generate_recommendations(job)

    rec, created = JobCourseRecommendation.objects.update_or_create(
        job=job,
        defaults={
            'source': result['source'],
            'reasons': {str(c.id): r for c, r, _ in result['items']},
        }
    )
    if result['items']:
        rec.courses.set([c for c, _, _ in result['items']])
    else:
        rec.courses.clear()

    return result['items']


def _generate_recommendations(job):
    """Generate course recommendations using Cerebras or fallback."""
    courses = list(Course.objects.all().order_by('-is_pinned', '-created_at')[:200])
    if not courses:
        logger.info('No courses available for recommendations for job %s', job.id)
        return {'items': [], 'source': ''}

    items, source = _call_cerebras(job, courses)
    if items:
        return {'items': items, 'source': 'cerebras'}

    logger.info('Cerebras unavailable for job %s, using fallback', job.id)
    items = _fallback_recommendations(job, courses)
    return {'items': items, 'source': 'fallback'}


def _build_job_text(job):
    """Build a concise text representation of job details for the prompt."""
    parts = [
        f'Title: {job.title}',
    ]
    if job.description:
        cleaned = re.sub(r'<[^>]+>', '', job.description)
        parts.append(f'Description: {cleaned[:1000]}')
    if job.requirements:
        cleaned = re.sub(r'<[^>]+>', '', job.requirements)
        parts.append(f'Requirements: {cleaned[:800]}')
    if job.industry:
        parts.append(f'Industry: {job.industry.name}')
    if job.experience_level:
        parts.append(f'Experience Level: {job.get_experience_level_display()}')
    skills = list(job.skills.all().values_list('name', flat=True))
    if skills:
        parts.append(f'Skills: {", ".join(skills)}')
    return '\n'.join(parts)


def _build_courses_text(courses):
    """Build a structured text representation of available courses."""
    lines = []
    for c in courses:
        summary = re.sub(r'<[^>]+>', '', c.summary or '')[:200] if c.summary else ''
        level_display = c.get_level_display() if c.level else ''
        program = c.program.title if c.program else ''
        lines.append(
            f'ID:{c.id}{FIELD_SEPARATOR}'
            f'Title:{c.title}{FIELD_SEPARATOR}'
            f'Description:{summary}{FIELD_SEPARATOR}'
            f'Program:{program}{FIELD_SEPARATOR}'
            f'Level:{level_display}{FIELD_SEPARATOR}'
            f'Price:{"Free" if c.is_free else str(c.price)}'
        )
    return ITEM_SEPARATOR.join(lines)


def _call_cerebras(job, courses):
    """Call Cerebras API to select relevant courses for the job."""
    api_key = getattr(settings, 'CEREBRAS_API_KEY', None)
    if not api_key:
        logger.warning('CEREBRAS_API_KEY not set, skipping AI recommendations')
        return [], ''

    model = getattr(settings, 'CEREBRAS_ASSESSMENT_MODEL', 'zai-glm-4.7')
    max_tokens = getattr(settings, 'CEREBRAS_ASSESSMENT_MAX_TOKENS', 2000)

    try:
        from cerebras.cloud.sdk import Cerebras
    except ImportError:
        logger.error('cerebras-cloud-sdk not installed')
        return [], ''

    job_text = _build_job_text(job)
    courses_text = _build_courses_text(courses)

    prompt = (
        'You are a strict course recommendation system. A user is applying for this job:\n\n'
        f'{job_text}\n\n'
        'Available courses:\n'
        f'{courses_text}\n\n'
        'CRITICAL RULE: Only recommend a course if it DIRECTLY teaches one or more of the '
        'specific skills listed under "Skills:" in the job posting. A course is relevant ONLY if '
        'completing it would genuinely teach a skill required for this job.\n\n'
        'For each recommended course, the reason MUST specify which exact skill(s) the course teaches.\n\n'
        'Return ONLY a JSON object with this exact structure:\n'
        '{"recommendations": [{"course_id": <int>, "reason": "<short reason>"}]}\n\n'
        'If NO courses directly teach the required skills, return {"recommendations": []}.\n'
        'Only use course IDs from the provided list. No extra text, markdown, or code fences.'
    )

    messages = [
        {
            'role': 'system',
            'content': 'You return only valid JSON. No Markdown. No code fences. No extra commentary.',
        },
        {'role': 'user', 'content': prompt},
    ]

    for attempt in range(2):
        try:
            client = Cerebras(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                max_tokens=max_tokens,
            )
            payload = response.choices[0].message.content.strip()

            payload = re.sub(r'^```(?:json)?\s*', '', payload)
            payload = re.sub(r'\s*```$', '', payload)

            data = json.loads(payload)
            recs = data.get('recommendations', [])

            if not recs:
                return [], 'cerebras'

            valid_ids = {c.id for c in courses}
            result = []
            for rec in recs:
                cid = rec.get('course_id')
                reason = rec.get('reason', '')
                if cid in valid_ids:
                    course = next(c for c in courses if c.id == cid)
                    result.append((course, reason, 'cerebras'))
                    if len(result) >= MAX_RECOMMENDATIONS:
                        break

            if not result:
                return [], 'cerebras'

            return result, 'cerebras'

        except json.JSONDecodeError:
            if attempt == 0:
                continue
            return [], ''
        except Exception as e:
            logger.error('Cerebras API error for job %s: %s', job.id, e)
            return [], ''

    return [], ''


def _fallback_recommendations(job, courses):
    """Strict keyword/skill matching fallback. Only returns strong matches."""
    skills = list(job.skills.all().values_list('name', flat=True))
    keywords = _extract_keywords(job)

    if not skills and not keywords:
        return []

    scored = []

    for course in courses:
        title_lower = course.title.lower()
        summary_lower = _strip_html(course.summary or '').lower()
        content_lower = _strip_html(course.content or '').lower()

        score = 0
        skill_matches = []

        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in title_lower:
                score += SKILL_TITLE_BOOST
                skill_matches.append(skill)
            elif skill_lower in summary_lower:
                score += SKILL_SUMMARY_BOOST
                skill_matches.append(skill)
            elif skill_lower in content_lower:
                score += SKILL_CONTENT_BOOST
                skill_matches.append(skill)

        if job.industry and job.industry.name:
            industry_lower = job.industry.name.lower()
            if industry_lower in title_lower or industry_lower in summary_lower:
                score += INDUSTRY_BOOST

        if score < MIN_FALLBACK_SCORE:
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in title_lower:
                    score += KEYWORD_TITLE_BOOST
                elif kw_lower in content_lower:
                    score += KEYWORD_CONTENT_BOOST

        if score >= MIN_FALLBACK_SCORE:
            scored.append((score, course, skill_matches))

    scored.sort(key=lambda x: -x[0])

    result = []
    for score, course, skill_matches in scored[:MAX_RECOMMENDATIONS]:
        reason = _build_fallback_reason(course, job, skill_matches)
        result.append((course, reason, 'fallback'))

    return result


def _extract_keywords(job):
    """Extract meaningful keywords from job details."""
    words = set()

    text = f'{job.title} {_strip_html(job.description or "")} {_strip_html(job.requirements or "")}'

    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could',
        'shall', 'should', 'may', 'might', 'must', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'your', 'his', 'its', 'our', 'their', 'not', 'no', 'nor', 'so', 'very',
        'just', 'also', 'well', 'new', 'good', 'get', 'make', 'able', 'use', 'using',
        'work', 'team', 'role', 'job', 'position', 'looking', 'seek', 'need', 'will',
        'including', 'related', 'various', 'across', 'within', 'based', 'make',
        'per', 'etc', 'like', 'much', 'many', 'some', 'any', 'all', 'each', 'every',
        'both', 'between', 'under', 'over', 'such', 'than', 'then', 'into', 'more',
        'most', 'other', 'about', 'above', 'after', 'before', 'during', 'without',
        'through', 'while', 'where', 'when', 'what', 'who', 'which', 'why', 'how',
    }

    for w in text.split():
        w = w.strip().lower()
        if len(w) > 2 and w not in stop_words:
            words.add(w)

    return list(words)


def _build_fallback_reason(course, job, skill_matches):
    """Generate a human-readable reason for strong fallback matches only."""
    reasons_part = []
    title_lower = course.title.lower()
    summary = _strip_html(course.summary or '').lower()

    for skill in skill_matches:
        if skill.lower() in title_lower:
            reasons_part.append(f'teaches the required skill "{skill}"')
        elif skill.lower() in summary:
            reasons_part.append(f'covers the required skill "{skill}"')

    if job.industry and job.industry.name:
        industry_lower = job.industry.name.lower()
        if industry_lower in title_lower or industry_lower in summary:
            reasons_part.append(f'relates to the {job.industry.name} industry')

    if reasons_part:
        return 'This course ' + ' and '.join(reasons_part) + '.'
    return ''


def _strip_html(text):
    return re.sub(r'<[^>]+>', '', text) if text else ''
