from decimal import Decimal, InvalidOperation

from django.apps import apps


DEFAULT_PASS_MARK = Decimal("70")


def _decimal(value, default=Decimal("0")):
    try:
        if value is None:
            return default

        return Decimal(str(value))

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return default


def _quiz_taker_model():
    return apps.get_model(
        "lms",
        "QuizTaker",
    )


def _pass_mark(quiz):
    """
    Use an explicit quiz threshold when the model exposes one.
    ChuoSmart's mastery-assessment fallback is 70%.
    """
    for attribute in (
        "passing_score",
        "pass_mark",
        "passing_percentage",
        "required_percentage",
    ):
        value = getattr(
            quiz,
            attribute,
            None,
        )

        if value is not None:
            return _decimal(
                value,
                DEFAULT_PASS_MARK,
            )

    return DEFAULT_PASS_MARK


def learner_passed_previous_module_assessment(
    student,
    previous_module,
):
    """
    True when this learner has a completed passing QuizTaker attempt
    belonging to the previous module.

    Filtering by QuizTaker.user already scopes the attempt to the
    learner, so both historical shared quizzes and newer
    learner-specific quizzes are supported.
    """
    if (
        student is None
        or previous_module is None
    ):
        return False

    QuizTaker = _quiz_taker_model()

    attempts = (
        QuizTaker.objects
        .filter(
            user=student,
            quiz__module=previous_module,
            completed=True,
        )
        .select_related(
            "quiz"
        )
        .order_by(
            "-date_completed",
            "-pk",
        )
    )

    for attempt in attempts:
        try:
            percentage = _decimal(
                attempt.get_score_percentage()
            )
        except Exception:
            # Never accidentally unlock paid content from a corrupt
            # historical attempt.
            continue

        if percentage >= _pass_mark(
            attempt.quiz
        ):
            return True

    return False


def _module_ordering_field(model):
    """
    Determine the real CourseModule ordering field.
    """
    concrete = {
        field.name
        for field in model._meta.concrete_fields
    }

    configured = list(
        model._meta.ordering or ()
    )

    for field in configured:
        field = str(field).lstrip("-")

        if (
            field in concrete
            and field != "pk"
        ):
            return field

    for candidate in (
        "order",
        "position",
        "sequence",
        "sort_order",
        "module_number",
        "number",
    ):
        if candidate in concrete:
            return candidate

    return "pk"


def previous_course_module(module):
    """
    Find the immediate predecessor using the CourseModule model's
    actual course/order structure.
    """
    model = type(module)

    course_id = getattr(
        module,
        "course_id",
        None,
    )

    if course_id is None:
        course = getattr(
            module,
            "course",
            None,
        )

        course_id = getattr(
            course,
            "pk",
            None,
        )

    if course_id is None:
        return None

    ordering = _module_ordering_field(
        model
    )

    modules = list(
        model.objects
        .filter(
            course_id=course_id
        )
        .order_by(
            ordering,
            "pk",
        )
    )

    for index, candidate in enumerate(
        modules
    ):
        if candidate.pk != module.pk:
            continue

        if index == 0:
            return None

        return modules[
            index - 1
        ]

    return None


def assessment_allows_module_purchase(
    module,
    student,
):
    """
    Compatibility fallback called only when ChuoSmart's existing
    progression method says the module is not yet eligible.

    First module remains prerequisite-free.
    """
    previous = previous_course_module(
        module
    )

    if previous is None:
        return True

    return (
        learner_passed_previous_module_assessment(
            student,
            previous,
        )
    )
