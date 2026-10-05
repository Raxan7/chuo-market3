from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdcashAdsIntegrationTests(SimpleTestCase):
    def test_base_template_loads_adcash_library(self):
        path = Path(settings.BASE_DIR) / "templates" / "app" / "base.html"
        content = path.read_text(encoding="utf-8")

        self.assertIn("acscdn.com/script/aclib.js", content)
        self.assertNotIn("aclib.runAutoTag", content)
        self.assertNotIn("qlmiolfe5q", content)

    def test_listing_ad_uses_adcash_banner(self):
        path = (
            Path(settings.BASE_DIR)
            / "templates"
            / "app"
            / "partials"
            / "list_ad_card.html"
        )
        content = path.read_text(encoding="utf-8")

        self.assertIn("aclib.runBanner", content)
        self.assertIn("12269306", content)

    def test_old_monetag_loader_is_not_in_base_template(self):
        path = Path(settings.BASE_DIR) / "templates" / "app" / "base.html"
        content = path.read_text(encoding="utf-8")

        self.assertNotIn("monetag-direct-links.js", content)
