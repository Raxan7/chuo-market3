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


def collect_course_assessment_context(course, limit=24000):
    """
    Build course-wide textual context for the final exam.

    Videos/audio remain externally hosted, so their title/module metadata
    contributes context, while text lessons and descriptions contribute
    their actual textual content.
    """
    chunks = []

    def add(value):
        value = strip_tags(str(value or "")).strip()

        if value:
            chunks.append(value)

    add(f"Course: {course.title}")
    add(getattr(course, "summary", ""))
    add(getattr(course, "description", ""))

    modules = CourseModule.objects.filter(
        course=course
    ).order_by("order", "id")

    for module in modules:
        if getattr(module, "skip_assessment", False):
            continue

        add(f"Module: {module.title}")
        add(getattr(module, "description", ""))

        contents = CourseContent.objects.filter(
            module=module
        ).order_by("id")

        for content in contents:
            add(f"Lesson: {content.title}")
            add(getattr(content, "text_content", ""))

    context = "\n\n".join(chunks)

    return context[: max(1000, int(limit or 24000))]
