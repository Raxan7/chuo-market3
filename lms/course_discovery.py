# CHUOSMART_COURSE_DISCOVERY_V1

import hashlib
import math
import random

from django.db.models import Count
from django.utils import timezone

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



# CHUOSMART_BALANCED_DISCOVERY_V2

DISCOVERY_ROTATION_MINUTES = 30
DISCOVERY_NEW_WINDOW_DAYS = 30


def _discovery_course_id(course):
    return (
        getattr(course, "pk", None)
        or getattr(course, "id", None)
        or 0
    )


def _discovery_age_days(course, now):
    created_at = getattr(
        course,
        "created_at",
        None,
    )

    if created_at is None:
        return 999999.0

    try:
        return max(
            0.0,
            (
                now - created_at
            ).total_seconds()
            / 86400.0,
        )

    except (
        TypeError,
        AttributeError,
        OverflowError,
    ):
        return 999999.0


def _discovery_seed(
    courses,
    now,
):
    """
    Rotate the discovery feed every 30 minutes.

    Within the same rotation window the order remains
    deterministic so pagination cannot randomly duplicate
    or skip courses between page requests.
    """

    bucket = int(
        now.timestamp()
        // (
            DISCOVERY_ROTATION_MINUTES
            * 60
        )
    )

    ids = ",".join(
        str(course_id)
        for course_id in sorted(
            _discovery_course_id(
                course
            )
            for course in courses
        )
    )

    digest = hashlib.sha256(
        (
            "chuosmart-discovery-v2:"
            f"{bucket}:{ids}"
        ).encode("utf-8")
    ).hexdigest()

    return int(
        digest[:16],
        16,
    )


def _weighted_discovery_pick(
    pool,
    count,
    weight_fn,
    rng,
):
    """
    Weighted random sample without replacement.
    """

    if count <= 0 or not pool:
        return []

    scored = []

    for course in pool:

        weight = max(
            float(
                weight_fn(course)
            ),
            0.001,
        )

        random_value = max(
            rng.random(),
            1e-12,
        )

        priority = (
            -math.log(
                random_value
            )
            / weight
        )

        scored.append(
            (
                priority,
                _discovery_course_id(
                    course
                ),
                course,
            )
        )

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return [
        item[2]
        for item in scored[:count]
    ]


def build_balanced_course_order(
    courses,
    popularity_by_id,
    *,
    page_size=10,
    now=None,
    seed=None,
):
    """
    ChuoSmart Balanced Course Discovery.

    ABSOLUTE RULE:

        PINNED COURSES ALWAYS COME FIRST.

    Pinned courses are completely removed from the
    randomized algorithm.

    Therefore:

        1 pinned course => card #1, always.

        multiple pinned courses =>
        every pinned card appears before every unpinned
        course.

    The unpinned courses are then balanced between:

        popularity
        new-course exposure
        zero-enrolment exploration
        weighted random discovery
    """

    courses = list(
        courses
    )

    if len(courses) <= 1:
        return courses

    page_size = max(
        1,
        int(
            page_size
            or 10
        ),
    )

    now = (
        now
        or timezone.now()
    )

    # ========================================================
    # HARD PINNED PREFIX
    #
    # IMPORTANT:
    # Pinned courses NEVER enter any random algorithm below.
    # ========================================================

    pinned = sorted(
        [
            course
            for course in courses
            if bool(
                getattr(
                    course,
                    "is_pinned",
                    False,
                )
            )
        ],
        key=lambda course: (
            _created_timestamp(
                course
            ),
            _discovery_course_id(
                course
            ),
        ),
        reverse=True,
    )

    remaining = [
        course
        for course in courses
        if not bool(
            getattr(
                course,
                "is_pinned",
                False,
            )
        )
    ]

    if not remaining:
        return pinned

    rng = random.Random(
        (
            _discovery_seed(
                courses,
                now,
            )
            if seed is None
            else seed
        )
    )

    def learners(course):

        return max(
            0,
            popularity_by_id.get(
                _discovery_course_id(
                    course
                ),
                0,
            ),
        )

    # Log scaling means:
    #
    # 10,000 learners is stronger than 10,
    # but it does NOT become 1,000x more powerful
    # inside discovery.

    popularity_logs = {
        _discovery_course_id(
            course
        ):
        math.log1p(
            learners(
                course
            )
        )
        for course
        in remaining
    }

    max_popularity = max(
        [1.0]
        + list(
            popularity_logs.values()
        )
    )

    def popularity_score(
        course
    ):

        return (
            popularity_logs.get(
                _discovery_course_id(
                    course
                ),
                0.0,
            )
            / max_popularity
        )

    def freshness_score(
        course
    ):

        age = _discovery_age_days(
            course,
            now,
        )

        if (
            age
            >= DISCOVERY_NEW_WINDOW_DAYS
        ):
            return 0.0

        return max(
            0.0,
            1.0
            - (
                age
                / float(
                    DISCOVERY_NEW_WINDOW_DAYS
                )
            ),
        )

    # THIS is why pinned cannot ever be displaced.
    ordered = list(
        pinned
    )

    # If pinned courses occupy part of page 1,
    # fill only the remaining page-1 positions.
    #
    # Example:
    #
    # pinned = 1
    # page size = 10
    #
    # position 1 = PINNED
    # positions 2-10 = algorithm
    #

    pinned_offset = (
        len(pinned)
        % page_size
    )

    first_block_size = (
        page_size
        - pinned_offset
        if pinned_offset
        else page_size
    )

    first_block = True

    while remaining:

        requested_size = (
            first_block_size
            if first_block
            else page_size
        )

        first_block = False

        target = min(
            requested_size,
            len(remaining),
        )

        block = []

        # On a normal 10-card block:
        #
        # 3 popularity slots
        # 2 new-course slots
        # 2 zero-learner slots
        # remaining slots = blended discovery

        if target >= 8:

            popular_slots = 3
            new_slots = 2
            zero_slots = 2

        else:

            popular_slots = (
                max(
                    1,
                    round(
                        target
                        * 0.30
                    ),
                )
                if target >= 2
                else 0
            )

            new_slots = (
                max(
                    1,
                    round(
                        target
                        * 0.20
                    ),
                )
                if target >= 3
                else 0
            )

            zero_slots = (
                max(
                    1,
                    round(
                        target
                        * 0.20
                    ),
                )
                if target >= 4
                else 0
            )

        def take(
            pool,
            count,
            weight_fn,
        ):
            nonlocal remaining

            count = min(
                count,
                target
                - len(block),
            )

            if count <= 0:
                return

            selected = (
                _weighted_discovery_pick(
                    pool,
                    count,
                    weight_fn,
                    rng,
                )
            )

            if not selected:
                return

            selected_ids = {
                _discovery_course_id(
                    course
                )
                for course
                in selected
            }

            block.extend(
                selected
            )

            remaining = [
                course
                for course
                in remaining
                if (
                    _discovery_course_id(
                        course
                    )
                    not in selected_ids
                )
            ]

        # ====================================================
        # POPULAR COURSES
        # ====================================================

        positive_courses = [
            course
            for course
            in remaining
            if learners(
                course
            ) > 0
        ]

        popular_pool_size = max(
            popular_slots,
            min(
                len(
                    positive_courses
                ),
                max(
                    popular_slots * 3,
                    math.ceil(
                        len(
                            positive_courses
                        )
                        * 0.30
                    ),
                ),
            ),
        )

        popular_pool = sorted(
            positive_courses,
            key=lambda course: (
                learners(
                    course
                ),
                _created_timestamp(
                    course
                ),
                _discovery_course_id(
                    course
                ),
            ),
            reverse=True,
        )[
            :popular_pool_size
        ]

        take(
            popular_pool,
            popular_slots,
            lambda course: (
                1.0
                + (
                    8.0
                    * popularity_score(
                        course
                    )
                )
            ),
        )

        # ====================================================
        # NEW COURSE PROTECTION
        # ====================================================

        take(
            [
                course
                for course
                in remaining
                if (
                    _discovery_age_days(
                        course,
                        now,
                    )
                    <= DISCOVERY_NEW_WINDOW_DAYS
                )
            ],
            new_slots,
            lambda course: (
                1.0
                + (
                    5.0
                    * freshness_score(
                        course
                    )
                )
                + (
                    1.0
                    if learners(
                        course
                    ) == 0
                    else 0.0
                )
            ),
        )

        # ====================================================
        # ZERO-LEARNER EXPLORATION
        # ====================================================

        take(
            [
                course
                for course
                in remaining
                if learners(
                    course
                ) == 0
            ],
            zero_slots,
            lambda course: (
                1.0
                + (
                    2.0
                    * freshness_score(
                        course
                    )
                )
            ),
        )

        # ====================================================
        # MIXED DISCOVERY
        #
        # Every course starts with weight 1.
        # Therefore no course can have zero opportunity.
        # ====================================================

        take(
            list(
                remaining
            ),
            target
            - len(block),
            lambda course: (
                1.0
                + (
                    4.0
                    * popularity_score(
                        course
                    )
                )
                + (
                    3.0
                    * freshness_score(
                        course
                    )
                )
                + (
                    0.75
                    if learners(
                        course
                    ) == 0
                    else 0.0
                )
            ),
        )

        # This shuffle ONLY sees unpinned courses.
        #
        # The pinned prefix has already been permanently
        # placed into `ordered`.

        rng.shuffle(
            block
        )

        ordered.extend(
            block
        )

    return ordered


def rank_courses_for_discovery(
    queryset,
    *,
    page_size=10,
    now=None,
    seed=None,
):
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

    ranked = build_balanced_course_order(
        courses,
        popularity,
        page_size=page_size,
        now=now,
        seed=seed,
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
