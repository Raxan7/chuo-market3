from decimal import Decimal

from django.test import SimpleTestCase

from .pricing import (
    calculate_pricing,
    normalize_package_price_for_modules,
)


class AutomaticPackageIncreaseTests(SimpleTestCase):
    def assert_valid_plan(self, starting_price, modules, expected):
        normalized = normalize_package_price_for_modules(
            Decimal(str(starting_price)),
            modules,
        )

        self.assertEqual(
            normalized,
            Decimal(str(expected)),
        )

        plan = calculate_pricing(
            normalized,
            modules,
            is_free=False,
        )

        self.assertEqual(plan.total, normalized)

        self.assertGreaterEqual(
            plan.certificate_price,
            Decimal("1000"),
        )
        self.assertEqual(
            plan.certificate_price % Decimal("500"),
            0,
        )

        for price in plan.module_prices:
            self.assertGreaterEqual(
                price,
                Decimal("1000"),
            )
            self.assertEqual(
                price % Decimal("500"),
                0,
            )

    def test_invalid_15000_12_modules_becomes_17000(self):
        self.assert_valid_plan(
            15000,
            12,
            17000,
        )

    def test_invalid_10000_11_modules_becomes_15500(self):
        self.assert_valid_plan(
            10000,
            11,
            15500,
        )

    def test_invalid_5000_15_modules_becomes_21500(self):
        self.assert_valid_plan(
            5000,
            15,
            21500,
        )

    def test_invalid_2000_8_modules_becomes_11500(self):
        self.assert_valid_plan(
            2000,
            8,
            11500,
        )

    def test_invalid_10000_16_modules_becomes_23000(self):
        self.assert_valid_plan(
            10000,
            16,
            23000,
        )

    def test_existing_valid_price_is_never_reduced(self):
        normalized = normalize_package_price_for_modules(
            Decimal("50000"),
            10,
        )

        self.assertEqual(
            normalized,
            Decimal("50000"),
        )

    def test_non_500_price_rounds_up_not_down(self):
        normalized = normalize_package_price_for_modules(
            Decimal("17750"),
            5,
        )

        self.assertEqual(
            normalized,
            Decimal("18000"),
        )
