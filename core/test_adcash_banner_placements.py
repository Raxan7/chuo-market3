from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashBannerPlacementTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

        self.base = (
            self.root
            / "templates"
            / "app"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.global_units = (
            self.root
            / "templates"
            / "app"
            / "partials"
            / "adcash_global_units.html"
        ).read_text(encoding="utf-8")

        self.list_banner = (
            self.root
            / "templates"
            / "app"
            / "partials"
            / "list_ad_card.html"
        ).read_text(encoding="utf-8")

        self.runtime = (
            self.root / "static" / "app" / "js" / "base.js"
        ).read_text(encoding="utf-8")

    def test_global_banner_partial_is_included(self):
        self.assertIn(
            '{% include '
            '"app/partials/adcash_global_units.html" %}',
            self.base,
        )

    def test_popup_adcash_formats_remain_disabled(self):
        markup = self.base + self.global_units + self.list_banner + self.runtime

        self.assertNotIn(
            "aclib.runAutoTag",
            markup,
        )
        self.assertNotIn(
            "qlmiolfe5q",
            markup,
        )
        self.assertNotIn(
            "window.open(",
            self.global_units,
        )
        self.assertNotIn(
            "popunder",
            self.global_units.lower(),
        )
        self.assertNotIn(
            "interstitial",
            self.global_units.lower(),
        )

    def test_new_banner_zones_are_present(self):
        self.assertIn(
            'data-zone="12270182"',
            self.global_units,
        )
        self.assertIn(
            '"12270190"',
            self.global_units,
        )
        self.assertIn(
            '"12270198"',
            self.global_units,
        )

    def test_existing_728_banner_is_preserved(self):
        self.assertIn(
            "data-adcash-banner-slot",
            self.list_banner,
        )
        self.assertIn(
            "12269306",
            self.list_banner,
        )

    def test_side_rail_requires_ultra_wide_screen(self):
        self.assertIn(
            "data-adcash-min-width=\"1800\"",
            self.global_units,
        )

    def test_mobile_and_desktop_square_are_exclusive(self):
        self.assertIn(
            "data-zone-breakpoint=\"575.98\"",
            self.global_units,
        )
