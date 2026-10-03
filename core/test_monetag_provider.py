from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MonetagProviderIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

        self.base = (
            self.root
            / "templates"
            / "app"
            / "base.html"
        ).read_text(encoding="utf-8")

    def test_popup_provider_formats_are_disabled(self):
        for token in (
            "nap5k.com/tag.min.js",
            "n6wxm.com/vignette.min.js",
            "11945562",
            "11945568",
            "loadMonetagZone(",
        ):
            self.assertNotIn(
                token,
                self.base,
            )

    def test_direct_link_asset_remains_enabled(self):
        self.assertIn(
            "monetag-direct-links.js",
            self.base,
        )

        javascript = (
            self.root
            / "static"
            / "chuosmart_v2"
            / "js"
            / "monetag-direct-links.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "https://omg10.com/4/10558191",
            javascript,
        )

        self.assertIn(
            "data-monetag-direct-link",
            javascript,
        )
