"""Central assessment policy for ChuoSmart courses."""

from django.utils.html import strip_tags

from .models import CourseContent, CourseModule


MODULE_QUIZ_QUESTION_COUNT = 5
FINAL_EXAM_QUESTION_COUNT = 20
DEFAULT_PASS_MARK = 70


def assessed_modules(course):
    """All real learning modules, excluding overview/no-assessment modules."""
    return list(
        CourseModule.objects.filter(
            course=course,
            skip_assessment=False,
        ).order_by("order", "id")
    )


def final_assessed_module(course):
    modules = assessed_modules(course)
    return modules[-1] if modules else None


def is_final_assessed_module(module):
    if module is None or getattr(module, "skip_assessment", False):
        return False

    final_module = final_assessed_module(module.course)

    return bool(
        final_module
        and final_module.pk == module.pk
    )


def assessment_type_for_module(module):
    if module is None or getattr(module, "skip_assessment", False):
        return "none"

    if is_final_assessed_module(module):
        return "final_exam"

    return "module_quiz"


def assessment_question_count_for_module(module):
    if assessment_type_for_module(module) == "final_exam":
        return FINAL_EXAM_QUESTION_COUNT

    return MODULE_QUIZ_QUESTION_COUNT


def assessment_label_for_module(module):
    if assessment_type_for_module(module) == "final_exam":
        return "Final Exam"

    return "Module Quiz"


def assessment_label_for_quiz(quiz):
    return assessment_label_for_module(
        getattr(quiz, "module", None)
    )


def assessment_type_for_quiz(quiz):
    return assessment_type_for_module(
        getattr(quiz, "module", None)
    )


def collect_course_assessment_context(course, limit=10000):
    """
    Build a balanced course-wide context for the Final Exam.

    The old implementation concatenated the course and truncated the
    resulting string. Large courses could therefore include mostly early
    modules while consuming too many provider tokens.

    This implementation gives every assessed module a share of the
    available character budget, so the Final Exam remains course-wide.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10000

    limit = max(2000, limit)

    def clean(value):
        return strip_tags(
            str(value or "")
        ).strip()

    header_parts = [
        f"Course: {clean(course.title)}",
    ]

    summary = clean(
        getattr(course, "summary", "")
    )
    description = clean(
        getattr(course, "description", "")
    )

    if summary:
        header_parts.append(
            f"Course summary: {summary}"
        )

    if description:
        header_parts.append(
            f"Course description: {description}"
        )

    # Keep course metadata useful without allowing it to consume the
    # whole Final Exam context budget.
    header_budget = min(
        1200,
        max(300, limit // 6),
    )

    header = "\n".join(
        header_parts
    )[:header_budget].rstrip()

    modules = list(
        CourseModule.objects.filter(
            course=course,
            skip_assessment=False,
        ).order_by(
            "order",
            "id",
        )
    )

    if not modules:
        return header[:limit]

    remaining = max(
        1,
        limit
        - len(header)
        - 2,
    )

    per_module_budget = max(
        1,
        remaining // len(modules),
    )

    module_sections = []

    for module in modules:
        parts = [
            f"Module: {clean(module.title)}",
        ]

        module_description = clean(
            getattr(
                module,
                "description",
                "",
            )
        )

        if module_description:
            parts.append(
                module_description
            )

        contents = (
            CourseContent.objects
            .filter(module=module)
            .order_by(
                "order",
                "id",
            )
        )

        for content in contents:
            title = clean(
                getattr(
                    content,
                    "title",
                    "",
                )
            )

            if title:
                parts.append(
                    f"Lesson: {title}"
                )

            body = clean(
                getattr(
                    content,
                    "text_content",
                    "",
                )
            )

            if body:
                parts.append(body)

        section = "\n".join(parts)

        module_sections.append(
            section[
                :per_module_budget
            ].rstrip()
        )

    context = (
        header
        + "\n\n"
        + "\n\n".join(
            module_sections
        )
    )

    return context[:limit]

