from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdSenseIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(
            settings.BASE_DIR
        )

    def test_adsense_loader_and_publisher(self):
        base = (
            self.root
            / "templates"
            / "app"
            / "base.html"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
            base,
        )

        self.assertIn(
            "ca-pub-1815335112679958",
            base,
        )

    def test_all_four_supplied_slots_exist(self):
        partials = (
            self.root
            / "templates"
            / "app"
            / "partials"
        )

        markup = "".join(
            path.read_text(
                encoding="utf-8"
            )
            for path in [
                partials / "adsense_course_infeed_ad.html",
                partials / "adsense_in_article_ad.html",
                partials / "adsense_global_units.html",
                partials / "list_ad_card.html",
            ]
        )

        for slot in [
            "1957297035",
            "9173442074",
            "5625079304",
            "8640009470",
        ]:
            self.assertIn(
                slot,
                markup,
            )

    def test_dynamic_ad_initializer_survives(self):
        runtime = (
            self.root
            / "static"
            / "app"
            / "js"
            / "base.js"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "window.initializeListAds",
            runtime,
        )

        self.assertIn(
            "window.adsbygoogle",
            runtime,
        )

        self.assertIn(
            "data-adsense-slot",
            runtime,
        )

    def test_active_provider_is_not_adcash(self):
        runtime = (
            self.root
            / "static"
            / "app"
            / "js"
            / "base.js"
        ).read_text(
            encoding="utf-8"
        )

        middleware = (
            self.root
            / "core"
            / "middleware.py"
        ).read_text(
            encoding="utf-8"
        )

        config = (
            self.root
            / "Commerce"
            / "settings"
            / "base.py"
        ).read_text(
            encoding="utf-8"
        )

        active = (
            runtime
            + middleware
            + config
        )

        self.assertNotIn(
            "acscdn.com",
            active,
        )

        self.assertNotIn(
            "AdcashCSPMiddleware",
            active,
        )

        self.assertIn(
            "pagead2.googlesyndication.com",
            middleware,
        )
