# CHUOSMART_COURSE_DISCOVERY_V1

from django.db.models import Count

from .models import CourseEnrollment


def _created_timestamp(course):
    value = getattr(course, "created_at", None)
    if value is None:
        return 0.0

    try:
        return value.timestamp()
    except (AttributeError, OSError, OverflowError, ValueError):
        return 0.0


def build_hybrid_course_order(
    courses,
    popularity_by_id,
    newest_slots=2,
    popular_slots=1,
):
    """
    Blend freshness with proven student interest.

    The default sequence is:
        newest, newest, popular, newest, newest, popular...

    Duplicate courses are removed automatically.
    """
    courses = list(courses)

    if len(courses) <= 1:
        return courses

    newest = sorted(
        courses,
        key=lambda course: (
            _created_timestamp(course),
            getattr(course, "pk", None)
            or getattr(course, "id", 0)
            or 0,
        ),
        reverse=True,
    )

    popular = sorted(
        courses,
        key=lambda course: (
            popularity_by_id.get(
                getattr(course, "pk", None)
                or getattr(course, "id", None),
                0,
            ),
            _created_timestamp(course),
            getattr(course, "pk", None)
            or getattr(course, "id", 0)
            or 0,
        ),
        reverse=True,
    )

    ordered = []
    seen = set()

    newest_index = 0
    popular_index = 0

    def append_from(source, index):
        while index < len(source):
            course = source[index]
            index += 1

            course_id = (
                getattr(course, "pk", None)
                or getattr(course, "id", None)
            )

            if course_id in seen:
                continue

            seen.add(course_id)
            ordered.append(course)
            return index, True

        return index, False

    while len(ordered) < len(courses):
        added_any = False

        for _ in range(newest_slots):
            newest_index, added = append_from(
                newest,
                newest_index,
            )
            added_any = added_any or added

        for _ in range(popular_slots):
            popular_index, added = append_from(
                popular,
                popular_index,
            )
            added_any = added_any or added

        if not added_any:
            for course in newest:
                course_id = (
                    getattr(course, "pk", None)
                    or getattr(course, "id", None)
                )

                if course_id not in seen:
                    seen.add(course_id)
                    ordered.append(course)

            break

    return ordered


def rank_courses_for_discovery(queryset):
    """
    Rank an already-filtered course queryset/list.

    Popularity is based on CourseEnrollment count while freshness uses
    Course.created_at. This introduces no schema migration.
    """
    courses = list(queryset)

    if len(courses) <= 1:
        return courses

    ids = [
        course.pk
        for course in courses
        if getattr(course, "pk", None) is not None
    ]

    popularity = dict(
        CourseEnrollment.objects
        .filter(course_id__in=ids)
        .values("course_id")
        .annotate(total=Count("pk"))
        .values_list("course_id", "total")
    )

    ranked = build_hybrid_course_order(
        courses,
        popularity,
    )

    # Useful to templates now or later without requiring more DB queries.
    newest_ids = {
        course.pk
        for course in sorted(
            courses,
            key=_created_timestamp,
            reverse=True,
        )[:6]
        if getattr(course, "pk", None) is not None
    }

    popular_ids = {
        course_id
        for course_id, _count in sorted(
            popularity.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:6]
    }

    for course in ranked:
        course.discovery_popularity = popularity.get(
            course.pk,
            0,
        )
        course.discovery_is_new = course.pk in newest_ids
        course.discovery_is_popular = (
            course.pk in popular_ids
            and course.pk not in newest_ids
        )

    return ranked
