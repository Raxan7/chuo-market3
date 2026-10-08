from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashSurfacePlacementTests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)
        self.root = root
        self.infeed_name = "app/partials/adcash_course_infeed_ad.html"

    def read(self, relative_path):
        return (self.root / relative_path).read_text(encoding="utf-8")

    def assert_course_cadence(self, markup):
        self.assertIn("forloop.counter == 4", markup)
        self.assertIn("forloop.counter == 9", markup)
        self.assertIn(self.infeed_name, markup)

    def test_marketplace_and_blog_lists_match_course_cadence(self):
        self.assert_course_cadence(self.read("templates/app/marketplace.html"))
        self.assert_course_cadence(self.read("templates/app/blog_list.html"))

    def test_marketplace_category_results_are_monetized(self):
        self.assert_course_cadence(
            self.read("templates/app/products_by_category.html")
        )

    def test_jobs_default_list_view_matches_course_cadence(self):
        self.assert_course_cadence(
            self.read("jobs/templates/jobs/_job_items.html")
        )

    def test_active_detail_pages_have_one_inline_ad(self):
        detail_templates = (
            "templates/app/productdetail.html",
            "templates/app/blog_detail.html",
            "templates/app/blog_detail_simple.html",
            "jobs/templates/jobs/job_detail.html",
        )

        for template in detail_templates:
            with self.subTest(template=template):
                markup = self.read(template)
                self.assertEqual(markup.count(self.infeed_name), 1)

    def test_infeed_remains_banner_only_and_dynamically_rehydratable(self):
        infeed = self.read(
            "templates/app/partials/adcash_course_infeed_ad.html"
        )
        base_js = self.read("static/app/js/base.js")

        self.assertIn("data-adcash-banner-slot", infeed)
        self.assertNotIn("aclib.runBanner", infeed)
        self.assertNotIn("aclib.runAutoTag", infeed + base_js)
        self.assertNotIn("popunder", infeed.lower())
        self.assertNotIn("interstitial", infeed.lower())
        self.assertNotIn("data-adcash-inline", infeed)
        self.assertIn("library.runBanner", base_js)
        self.assertIn('renderIn: "#" + slot.id', base_js)
