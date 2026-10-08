from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashAdsIntegrationTests(SimpleTestCase):
    def test_adcash_library_is_loaded_by_runtime(self):
        root = Path(settings.BASE_DIR)
        base = (root / "templates" / "app" / "base.html").read_text(encoding="utf-8")
        runtime = (root / "static" / "app" / "js" / "base.js").read_text(encoding="utf-8")

        self.assertNotIn('src="//acscdn.com/script/aclib.js"', base)
        self.assertIn("https://acscdn.com/script/aclib.js", runtime)
        self.assertNotIn("aclib.runAutoTag", runtime)
        self.assertNotIn("qlmiolfe5q", base + runtime)

    def test_listing_ad_uses_adcash_banner(self):
        path = (
            Path(settings.BASE_DIR)
            / "templates"
            / "app"
            / "partials"
            / "list_ad_card.html"
        )
        content = path.read_text(encoding="utf-8")

        self.assertIn("data-adcash-banner-slot", content)
        self.assertIn("12269306", content)

    def test_old_monetag_loader_is_not_in_base_template(self):
        path = Path(settings.BASE_DIR) / "templates" / "app" / "base.html"
        content = path.read_text(encoding="utf-8")

        self.assertNotIn("monetag-direct-links.js", content)
