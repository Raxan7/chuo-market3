from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class LearningUpgradeSourceSafetyTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        root = Path(settings.BASE_DIR)

        cls.views = (
            root / "lms" / "views.py"
        ).read_text(encoding="utf-8")

        cls.urls = (
            root / "lms" / "urls.py"
        ).read_text(encoding="utf-8")

        cls.course_template = (
            root
            / "lms"
            / "templates"
            / "lms"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

        cls.quiz_template = (
            root
            / "lms"
            / "templates"
            / "lms"
            / "quiz_question.html"
        ).read_text(encoding="utf-8")

        cls.policy = (
            root
            / "lms"
            / "assessment_policy.py"
        ).read_text(encoding="utf-8")

        cls.ai = (
            root
            / "lms"
            / "ai_assessments.py"
        ).read_text(encoding="utf-8")

    def test_enrollment_choice_is_installed(self):
        self.assertIn(
            "pay_as_you_learn_start",
            self.views,
        )
        self.assertIn(
            "pay_as_you_learn_start",
            self.urls,
        )
        self.assertIn(
            "How would you like to learn?",
            self.course_template,
        )
        self.assertIn(
            "Buy Full Course",
            self.course_template,
        )
        self.assertIn(
            "Start Pay as You Learn",
            self.course_template,
        )

    def test_module_choice_is_server_resolved(self):
        self.assertIn(
            "previous_module_accessible_for_request",
            self.views,
        )
        self.assertIn(
            "_user_has_module_access",
            self.views,
        )

    def test_final_exam_policy_is_20_questions(self):
        self.assertIn(
            "MODULE_QUIZ_QUESTION_COUNT = 5",
            self.policy,
        )
        self.assertIn(
            "FINAL_EXAM_QUESTION_COUNT = 20",
            self.policy,
        )
        self.assertIn(
            "final_exam",
            self.policy,
        )

    def test_final_exam_uses_whole_course_context(self):
        self.assertIn(
            "collect_course_assessment_context",
            self.policy,
        )
        self.assertIn(
            "CHUOSMART_FINAL_EXAM_CONTEXT_V1",
            self.ai,
        )

    def test_quiz_navigation_uses_fetch(self):
        self.assertIn(
            "fetch(",
            self.quiz_template,
        )
        self.assertIn(
            "new FormData(form)",
            self.quiz_template,
        )
        self.assertIn(
            "history.pushState",
            self.quiz_template,
        )

    def test_randomized_order_is_frozen_in_session(self):
        self.assertIn(
            "chuosmart.quiz-question-order.",
            self.views,
        )
        self.assertNotIn(
            "Question.objects.filter(quiz=quiz).order_by('?')",
            self.views,
        )
