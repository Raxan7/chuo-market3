from types import SimpleNamespace
from unittest.mock import patch

from django.test import (
    SimpleTestCase,
    override_settings,
)

from lms.ai_assessments import (
    _call_configured_ai_for_question_set,
)


def payload(start, count):
    return {
        "questions": [
            {
                "question": f"Question {i}",
                "choices": [
                    "A",
                    "B",
                    "C",
                    "D",
                ],
                "correct_index": 0,
                "explanation": "A",
            }
            for i in range(
                start,
                start + count,
            )
        ]
    }


class FinalExamBatchTests(
    SimpleTestCase
):
    def setUp(self):
        self.module = SimpleNamespace(
            id=999,
            title="Final",
        )

    @override_settings(
        AI_ASSESSMENT_BATCH_SIZE=5,
        AI_ASSESSMENT_MAX_BATCH_CALLS=8,
    )
    @patch(
        "lms.ai_assessments."
        "_call_configured_ai_for_questions"
    )
    def test_twenty_is_four_batches(
        self,
        provider,
    ):
        counter = {
            "n": 0,
        }

        def fake(
            module,
            context,
            count,
            max_attempts=None,
        ):
            counter["n"] += 1

            return (
                payload(
                    (
                        counter["n"]
                        - 1
                    )
                    * 5
                    + 1,
                    count,
                ),
                "success",
                "ok",
            )

        provider.side_effect = fake

        result, status, _ = (
            _call_configured_ai_for_question_set(
                self.module,
                "course",
                20,
            )
        )

        self.assertEqual(
            status,
            "success",
        )

        self.assertEqual(
            len(
                result["questions"]
            ),
            20,
        )

        self.assertEqual(
            provider.call_count,
            4,
        )

    @override_settings(
        AI_ASSESSMENT_BATCH_SIZE=5,
    )
    @patch(
        "lms.ai_assessments."
        "_call_configured_ai_for_questions"
    )
    def test_normal_quiz_is_one_call(
        self,
        provider,
    ):
        provider.return_value = (
            payload(1, 5),
            "success",
            "ok",
        )

        result, status, _ = (
            _call_configured_ai_for_question_set(
                self.module,
                "module",
                5,
            )
        )

        self.assertEqual(
            status,
            "success",
        )

        self.assertEqual(
            len(
                result["questions"]
            ),
            5,
        )

        self.assertEqual(
            provider.call_count,
            1,
        )
