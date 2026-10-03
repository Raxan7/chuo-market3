import re
from pathlib import Path

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

from core.context_processors import site_ad_settings


class MonetagProviderIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

        self.base = (
            self.root
            / "templates"
            / "app"
            / "base.html"
        ).read_text(encoding="utf-8")

    def test_monetag_provider_zones_load_once(self):
        self.assertEqual(
            len(
                re.findall(
                    r"loadMonetagZone\(\s*['\"]11945562['\"]",
                    self.base,
                )
            ),
            1,
        )

        self.assertEqual(
            len(
                re.findall(
                    r"loadMonetagZone\(\s*['\"]11945568['\"]",
                    self.base,
                )
            ),
            1,
        )

        self.assertEqual(
            self.base.count(
                "https://nap5k.com/tag.min.js"
            ),
            1,
        )

        self.assertEqual(
            self.base.count(
                "https://n6wxm.com/vignette.min.js"
            ),
            1,
        )

    def test_provider_is_guarded_by_ads_allowed(self):
        start = self.base.index(
            "<!-- CHUOSMART MONETAG PROVIDER START -->"
        )

        end = self.base.index(
            "<!-- CHUOSMART MONETAG PROVIDER END -->"
        )

        block = self.base[start:end]

        self.assertIn(
            "{% if ads_allowed %}",
            block,
        )

    def test_course_catalogue_allows_ads(self):
        request = RequestFactory().get(
            "/lms/courses/"
        )

        context = site_ad_settings(
            request
        )

        self.assertTrue(
            context["ads_allowed"]
        )

    def test_sensitive_page_still_suppresses_ads(self):
        request = RequestFactory().get(
            "/login/"
        )

        context = site_ad_settings(
            request
        )

        self.assertFalse(
            context["ads_allowed"]
        )

    def test_google_adsense_removed_from_active_frontend(self):
        leftovers = []

        for source_root in (
            self.root / "templates",
            self.root / "static",
        ):
            if not source_root.exists():
                continue

            for path in source_root.rglob("*"):
                if not path.is_file():
                    continue

                if "staticfiles" in path.parts:
                    continue

                if path.suffix.lower() not in {
                    ".html", ".htm",
                    ".js", ".jsx",
                    ".ts", ".tsx",
                    ".css", ".scss",
                }:
                    continue

                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).lower()

                if (
                    "pagead2.googlesyndication.com"
                    in content
                    or "adsbygoogle"
                    in content
                ):
                    leftovers.append(
                        str(
                            path.relative_to(
                                self.root
                            )
                        )
                    )

        self.assertEqual(
            leftovers,
            [],
        )

    def test_fallback_card_uses_monetag_direct_links(self):
        content = (
            self.root
            / "templates"
            / "app"
            / "partials"
            / "list_ad_card.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "data-monetag-direct-link",
            content,
        )

        self.assertIn(
            "Sponsored",
            content,
        )
