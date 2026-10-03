from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from .course_discovery import build_hybrid_course_order


class CourseDiscoveryRankingTests(SimpleTestCase):
    def _course(self, course_id, age_days):
        return SimpleNamespace(
            id=course_id,
            pk=course_id,
            created_at=timezone.now() - timedelta(days=age_days),
        )

    def test_new_courses_receive_priority_without_hiding_popular_course(self):
        newest = self._course(1, 0)
        second_newest = self._course(2, 1)
        older_popular = self._course(3, 90)
        older = self._course(4, 120)

        result = build_hybrid_course_order(
            [older, older_popular, second_newest, newest],
            {
                1: 1,
                2: 0,
                3: 500,
                4: 2,
            },
        )

        self.assertEqual(
            [course.id for course in result[:3]],
            [1, 2, 3],
        )

    def test_hybrid_ranking_does_not_duplicate_courses(self):
        courses = [
            self._course(1, 0),
            self._course(2, 3),
            self._course(3, 30),
            self._course(4, 50),
            self._course(5, 90),
        ]

        result = build_hybrid_course_order(
            courses,
            {
                1: 2,
                2: 4,
                3: 500,
                4: 300,
                5: 100,
            },
        )

        ids = [course.id for course in result]

        self.assertEqual(len(ids), len(courses))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {1, 2, 3, 4, 5})
