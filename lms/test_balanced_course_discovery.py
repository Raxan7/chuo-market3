from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from .course_discovery import (
    build_balanced_course_order,
)


class BalancedCourseDiscoveryTests(
    SimpleTestCase
):

    def _course(
        self,
        course_id,
        age_days,
        *,
        pinned=False,
    ):

        return SimpleNamespace(
            id=course_id,
            pk=course_id,
            created_at=(
                timezone.now()
                - timedelta(
                    days=age_days
                )
            ),
            is_pinned=pinned,
        )

    def test_pinned_course_is_always_first(
        self
    ):

        pinned = self._course(
            99,
            500,
            pinned=True,
        )

        mega_popular = self._course(
            1,
            1,
        )

        others = [
            self._course(
                i,
                i,
            )
            for i
            in range(
                2,
                20,
            )
        ]

        popularity = {
            course.id: 10
            for course
            in others
        }

        popularity[1] = 100000
        popularity[99] = 0

        # Test 50 completely different random rotations.
        for seed in range(50):

            result = (
                build_balanced_course_order(
                    [
                        mega_popular,
                        *others,
                        pinned,
                    ],
                    popularity,
                    page_size=10,
                    seed=seed,
                )
            )

            self.assertEqual(
                result[0].id,
                99,
            )

    def test_multiple_pinned_stay_before_everything(
        self
    ):

        pinned_old = self._course(
            90,
            30,
            pinned=True,
        )

        pinned_new = self._course(
            91,
            1,
            pinned=True,
        )

        courses = [
            self._course(
                i,
                i,
            )
            for i
            in range(
                1,
                20,
            )
        ]

        result = (
            build_balanced_course_order(
                [
                    *courses,
                    pinned_old,
                    pinned_new,
                ],
                {
                    course.id: 10000
                    for course
                    in courses
                },
                seed=123,
            )
        )

        self.assertEqual(
            [
                course.id
                for course
                in result[:2]
            ],
            [
                91,
                90,
            ],
        )

    def test_zero_enrolment_courses_get_exposure(
        self
    ):

        courses = [
            self._course(
                i,
                100 + i,
            )
            for i
            in range(
                1,
                21,
            )
        ]

        popularity = {
            i: 50
            for i
            in range(
                1,
                21,
            )
        }

        zero_ids = {
            17,
            18,
            19,
            20,
        }

        for course_id in zero_ids:
            popularity[
                course_id
            ] = 0

        result = (
            build_balanced_course_order(
                courses,
                popularity,
                page_size=10,
                seed=88,
            )
        )

        first_page = {
            course.id
            for course
            in result[:10]
        }

        self.assertGreaterEqual(
            len(
                first_page
                & zero_ids
            ),
            2,
        )

    def test_new_courses_get_exposure(
        self
    ):

        courses = [
            self._course(
                i,
                100 + i,
            )
            for i
            in range(
                1,
                17,
            )
        ]

        new_ids = {
            17,
            18,
            19,
            20,
        }

        courses.extend(
            [
                self._course(
                    17,
                    1,
                ),
                self._course(
                    18,
                    2,
                ),
                self._course(
                    19,
                    3,
                ),
                self._course(
                    20,
                    4,
                ),
            ]
        )

        result = (
            build_balanced_course_order(
                courses,
                {
                    i: 20
                    for i
                    in range(
                        1,
                        21,
                    )
                },
                page_size=10,
                seed=99,
            )
        )

        first_page = {
            course.id
            for course
            in result[:10]
        }

        self.assertGreaterEqual(
            len(
                first_page
                & new_ids
            ),
            2,
        )

    def test_every_course_appears_once(
        self
    ):

        courses = [
            self._course(
                i,
                i,
                pinned=(
                    i == 25
                ),
            )
            for i
            in range(
                1,
                26,
            )
        ]

        result = (
            build_balanced_course_order(
                courses,
                {
                    i: i % 7
                    for i
                    in range(
                        1,
                        26,
                    )
                },
                seed=777,
            )
        )

        ids = [
            course.id
            for course
            in result
        ]

        self.assertEqual(
            ids[0],
            25,
        )

        self.assertEqual(
            len(ids),
            len(set(ids)),
        )

        self.assertEqual(
            set(ids),
            set(
                range(
                    1,
                    26,
                )
            ),
        )
