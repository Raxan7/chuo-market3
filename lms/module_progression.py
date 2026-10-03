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


# CHUOSMART PAY-AS-YOU-LEARN ELIGIBILITY V1

def build_module_purchase_eligibility(
    modules,
    student,
    approved_module_ids=None,
):
    """
    Return the IDs of paid modules the learner may purchase now.

    This deliberately delegates progression to
    CourseModule.previous_module_accessible_for_request(), which is
    also the backend checkout gate.

    Result: course-detail UI and payment backend use one source of truth.
    """
    approved = set(
        approved_module_ids or ()
    )

    eligible = set()

    if student is None:
        return eligible

    for module in modules:
        module_id = (
            getattr(module, "pk", None)
            or getattr(module, "id", None)
        )

        if module_id is None:
            continue

        if module_id in approved:
            continue

        price = getattr(
            module,
            "price",
            None,
        )

        # Only paid modules need a purchase CTA.
        if not price:
            continue

        try:
            may_purchase = (
                module
                .previous_module_accessible_for_request(
                    student
                )
            )
        except Exception:
            # Never expose paid content if progression evaluation
            # itself failed unexpectedly.
            may_purchase = False

        if may_purchase:
            eligible.add(
                module_id
            )

    return eligible


def request_eligible_module_ids(
    course,
    student,
):
    """
    Return paid module IDs that this learner may purchase NOW.

    This is the course-detail equivalent of the backend payment gate.

    A module is not offered for payment when:
      - the learner owns the full course;
      - an approved/pending module request already exists;
      - an active ModuleAccessGrant already gives access;
      - progression prerequisites have not been completed.

    Progression itself remains delegated to
    CourseModule.previous_module_accessible_for_request().
    """
    if (
        course is None
        or student is None
    ):
        return set()

    from django.apps import apps

    CourseEnrollment = apps.get_model(
        "lms",
        "CourseEnrollment",
    )

    CourseModule = apps.get_model(
        "lms",
        "CourseModule",
    )

    ModuleAccessRequest = apps.get_model(
        "lms",
        "ModuleAccessRequest",
    )

    ModuleAccessGrant = apps.get_model(
        "lms",
        "ModuleAccessGrant",
    )

    # Full-course buyers should never see module-level purchase CTAs.
    full_course_access = (
        CourseEnrollment.objects
        .filter(
            student=student,
            course=course,
            payment_status="approved",
        )
        .exists()
    )

    if full_course_access:
        return set()

    # A pending payment must not create another checkout opportunity,
    # and an approved request is already owned.
    unavailable_module_ids = set(
        ModuleAccessRequest.objects
        .filter(
            student=student,
            module__course=course,
            status__in=(
                "pending",
                "approved",
            ),
        )
        .values_list(
            "module_id",
            flat=True,
        )
    )

    # Some historical/admin/webhook paths grant access directly.
    # Those modules must not be sold to the learner a second time.
    unavailable_module_ids.update(
        ModuleAccessGrant.objects
        .filter(
            student=student,
            module__course=course,
            active=True,
        )
        .values_list(
            "module_id",
            flat=True,
        )
    )

    modules = (
        CourseModule.objects
        .filter(
            course=course
        )
        .order_by(
            "order",
            "id",
        )
    )

    return build_module_purchase_eligibility(
        modules,
        student,
        approved_module_ids=unavailable_module_ids,
    )
