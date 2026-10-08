from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashRuntimeSafetyTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(settings.BASE_DIR)
        cls.runtime = (
            cls.root / "static" / "app" / "js" / "base.js"
        ).read_text(encoding="utf-8")
        cls.base = (
            cls.root / "templates" / "app" / "base.html"
        ).read_text(encoding="utf-8")
        cls.infeed = (
            cls.root
            / "templates"
            / "app"
            / "partials"
            / "adcash_course_infeed_ad.html"
        ).read_text(encoding="utf-8")
        cls.global_units = (
            cls.root
            / "templates"
            / "app"
            / "partials"
            / "adcash_global_units.html"
        ).read_text(encoding="utf-8")
        cls.list_card = (
            cls.root
            / "templates"
            / "app"
            / "partials"
            / "list_ad_card.html"
        ).read_text(encoding="utf-8")

    def test_provider_library_is_centrally_and_lazily_loaded(self):
        self.assertIn(
            'var ADCASH_LIBRARY_URL = "https://acscdn.com/script/aclib.js";',
            self.runtime,
        )
        self.assertIn("var adcashLibraryPromise = null;", self.runtime)
        self.assertIn("data-chuosmart-adcash-library", self.runtime)
        self.assertNotIn('src="//acscdn.com/script/aclib.js"', self.base)

    def test_banner_rendering_targets_the_exact_slot(self):
        self.assertIn("library.runBanner({", self.runtime)
        self.assertIn("zoneId: String(zoneId)", self.runtime)
        self.assertIn('renderIn: "#" + slot.id', self.runtime)
        self.assertIn(
            'slot.setAttribute("data-adcash-state", "requested")',
            self.runtime,
        )

    def test_runtime_fails_gracefully_instead_of_breaking_the_page(self):
        self.assertIn("adcashRuntimeWarning", self.runtime)
        self.assertIn(
            "library unavailable; page continues without ads",
            self.runtime,
        )
        self.assertIn("runBanner failed for zone", self.runtime)
        self.assertIn(
            'slot.setAttribute("data-adcash-state", "failed")',
            self.runtime,
        )

    def test_dynamic_content_reuses_the_central_initializer(self):
        self.assertIn("window.initializeListAds", self.runtime)
        self.assertIn(
            "initAdIframes(listContainer || document)",
            self.runtime,
        )
        self.assertIn(
            '[data-adcash-banner-slot][data-adcash-state="pending"]',
            self.runtime,
        )
        self.assertIn(
            '[data-adcash-banner-slot][data-adcash-state="waiting-for-width"]',
            self.runtime,
        )

    def test_banner_partials_do_not_execute_inline_adcash_javascript(self):
        markup = self.infeed + self.global_units + self.list_card
        self.assertIn("data-adcash-banner-slot", markup)
        self.assertNotIn("data-adcash-inline", markup)
        self.assertNotIn("aclib.runBanner", markup)
        self.assertNotIn("aclib.runAutoTag", markup + self.runtime)
        self.assertNotIn("popunder", markup.lower())
        self.assertNotIn("interstitial", markup.lower())
