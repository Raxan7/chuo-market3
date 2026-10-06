from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashCourseInfeedTests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "templates/app/base.html"
        ).read_text(encoding="utf-8")

        self.catalogue = (
            root / "lms/templates/lms/course_list.html"
        ).read_text(encoding="utf-8")

        self.infeed = (
            root
            / "templates/app/partials/adcash_course_infeed_ad.html"
        ).read_text(encoding="utf-8")

    def test_popup_formats_are_disabled(self):
        markup = self.base + self.infeed

        self.assertNotIn("aclib.runAutoTag", markup)
        self.assertNotIn("qlmiolfe5q", markup)

    def test_infeed_uses_banner_only(self):
        self.assertIn("aclib.runBanner", self.infeed)
        self.assertIn("12270190", self.infeed)
        self.assertIn("12270198", self.infeed)

    def test_ads_are_after_course_4_and_9(self):
        self.assertIn(
            "forloop.counter == 4",
            self.catalogue,
        )
        self.assertIn(
            "forloop.counter == 9",
            self.catalogue,
        )
        self.assertNotIn(
            "forloop.counter == 14",
            self.catalogue,
        )

    def test_infeed_partial_is_included_once(self):
        self.assertEqual(
            self.catalogue.count(
                "adcash_course_infeed_ad.html"
            ),
            1,
        )
