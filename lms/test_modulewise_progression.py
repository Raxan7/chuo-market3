from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from lms.module_progression import (
    learner_passed_previous_module_assessment,
)


class ModulewiseProgressionTests(SimpleTestCase):

    def _attempt(
        self,
        score,
        pass_mark=70,
    ):
        return SimpleNamespace(
            quiz=SimpleNamespace(
                passing_score=pass_mark,
            ),
            get_score_percentage=lambda: score,
        )

    def _queryset(self, attempts):
        qs = MagicMock()

        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = attempts

        return qs

    def test_passed_previous_module_unlocks_next_purchase(self):
        student = SimpleNamespace(pk=101)
        previous = SimpleNamespace(pk=11)

        attempt = self._attempt(82)

        qs = self._queryset([attempt])

        with patch(
            "lms.module_progression._quiz_taker_model"
        ) as model_factory:
            model = MagicMock()
            model.objects.filter.return_value = qs
            model_factory.return_value = model

            result = (
                learner_passed_previous_module_assessment(
                    student,
                    previous,
                )
            )

        self.assertTrue(result)

    def test_exact_70_percent_passes(self):
        student = SimpleNamespace(pk=101)
        previous = SimpleNamespace(pk=11)

        attempt = self._attempt(70)

        qs = self._queryset([attempt])

        with patch(
            "lms.module_progression._quiz_taker_model"
        ) as model_factory:
            model = MagicMock()
            model.objects.filter.return_value = qs
            model_factory.return_value = model

            result = (
                learner_passed_previous_module_assessment(
                    student,
                    previous,
                )
            )

        self.assertTrue(result)

    def test_failed_previous_assessment_does_not_unlock(self):
        student = SimpleNamespace(pk=101)
        previous = SimpleNamespace(pk=11)

        attempt = self._attempt(69)

        qs = self._queryset([attempt])

        with patch(
            "lms.module_progression._quiz_taker_model"
        ) as model_factory:
            model = MagicMock()
            model.objects.filter.return_value = qs
            model_factory.return_value = model

            result = (
                learner_passed_previous_module_assessment(
                    student,
                    previous,
                )
            )

        self.assertFalse(result)

    def test_no_completed_attempt_does_not_unlock(self):
        student = SimpleNamespace(pk=101)
        previous = SimpleNamespace(pk=11)

        qs = self._queryset([])

        with patch(
            "lms.module_progression._quiz_taker_model"
        ) as model_factory:
            model = MagicMock()
            model.objects.filter.return_value = qs
            model_factory.return_value = model

            result = (
                learner_passed_previous_module_assessment(
                    student,
                    previous,
                )
            )

        self.assertFalse(result)

    def test_explicit_quiz_pass_mark_is_respected(self):
        student = SimpleNamespace(pk=101)
        previous = SimpleNamespace(pk=11)

        attempt = self._attempt(
            score=74,
            pass_mark=75,
        )

        qs = self._queryset([attempt])

        with patch(
            "lms.module_progression._quiz_taker_model"
        ) as model_factory:
            model = MagicMock()
            model.objects.filter.return_value = qs
            model_factory.return_value = model

            result = (
                learner_passed_previous_module_assessment(
                    student,
                    previous,
                )
            )

        self.assertFalse(result)
