from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase

from lms.module_progression import (
    build_module_purchase_eligibility,
)


class PayAsYouLearnUiProgressionTests(SimpleTestCase):

    def _module(
        self,
        pk,
        eligible,
        price="5000",
    ):
        return SimpleNamespace(
            pk=pk,
            id=pk,
            price=Decimal(price),
            previous_module_accessible_for_request=(
                lambda student: eligible
            ),
        )

    def test_completed_previous_module_makes_next_module_payable(self):
        student = SimpleNamespace(pk=10)

        module_1 = self._module(
            1,
            eligible=True,
        )

        module_2 = self._module(
            2,
            eligible=True,
        )

        result = build_module_purchase_eligibility(
            [module_1, module_2],
            student,
            approved_module_ids={1},
        )

        self.assertEqual(
            result,
            {2},
        )

    def test_future_module_remains_locked_until_previous_completed(self):
        student = SimpleNamespace(pk=10)

        module_2 = self._module(
            2,
            eligible=True,
        )

        module_3 = self._module(
            3,
            eligible=False,
        )

        result = build_module_purchase_eligibility(
            [module_2, module_3],
            student,
            approved_module_ids=set(),
        )

        self.assertEqual(
            result,
            {2},
        )

    def test_already_approved_module_is_not_offered_for_payment_again(self):
        student = SimpleNamespace(pk=10)

        module = self._module(
            2,
            eligible=True,
        )

        result = build_module_purchase_eligibility(
            [module],
            student,
            approved_module_ids={2},
        )

        self.assertEqual(
            result,
            set(),
        )

    def test_free_module_is_not_offered_as_paid_unlock(self):
        student = SimpleNamespace(pk=10)

        module = SimpleNamespace(
            pk=2,
            id=2,
            price=Decimal("0"),
            previous_module_accessible_for_request=(
                lambda student: True
            ),
        )

        result = build_module_purchase_eligibility(
            [module],
            student,
            approved_module_ids=set(),
        )

        self.assertEqual(
            result,
            set(),
        )

    def test_course_detail_uses_canonical_pay_as_you_learn_reconciliation(self):
        root = Path(settings.BASE_DIR)

        views = (
            root
            / "lms"
            / "views.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "CHUOSMART PAY-AS-YOU-LEARN UI GATE V1",
            views,
        )

        self.assertIn(
            "request_eligible_module_ids(",
            views,
        )

    def test_template_no_longer_claims_full_course_is_required(self):
        root = Path(settings.BASE_DIR)

        template = (
            root
            / "lms"
            / "templates"
            / "lms"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            "All other modules remain locked until "
            "full-course payment is approved",
            template,
        )

        self.assertIn(
            "next eligible module",
            template.lower(),
        )

    def test_template_keeps_module_payment_cta(self):
        root = Path(settings.BASE_DIR)

        template = (
            root
            / "lms"
            / "templates"
            / "lms"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "module.id in request_eligible_modules",
            template,
        )

        self.assertIn(
            "module_access_payment",
            template,
        )

    def test_purchase_eligible_locked_module_can_expand(self):
        root = Path(settings.BASE_DIR)

        template = (
            root
            / "lms"
            / "templates"
            / "lms"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "state.unlocked or is_course_instructor or "
            "module.id in request_eligible_modules",
            template,
        )

        self.assertIn(
            "Ready to unlock",
            template,
        )

        self.assertIn(
            "module_access_payment",
            template,
        )
