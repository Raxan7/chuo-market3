from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MonetagAdsIntegrationTests(SimpleTestCase):
    expected_links = (
        "https://omg10.com/4/10558191",
        "https://omg10.com/4/10558195",
        "https://omg10.com/4/10558194",
        "https://omg10.com/4/11939936",
        "https://omg10.com/4/10558192",
        "https://omg10.com/4/10558193",
        "https://omg10.com/4/10558189",
        "https://omg10.com/4/10558184",
        "https://omg10.com/4/10558188",
        "https://omg10.com/4/10558187",
    )

    def test_monetag_direct_link_asset_contains_all_zones(self):
        path = (
            Path(settings.BASE_DIR)
            / "static"
            / "chuosmart_v2"
            / "js"
            / "monetag-direct-links.js"
        )
        self.assertTrue(path.exists())

        content = path.read_text(encoding="utf-8")

        for direct_link in self.expected_links:
            self.assertIn(direct_link, content)

    def test_base_template_loads_monetag_through_ads_allowed(self):
        path = Path(settings.BASE_DIR) / "templates" / "app" / "base.html"
        content = path.read_text(encoding="utf-8")

        self.assertIn("{% if ads_allowed %}", content)
        self.assertIn("chuosmart_v2/js/monetag-direct-links.js", content)

    def test_frontend_source_has_no_legacy_network_reference(self):
        root = Path(settings.BASE_DIR)

        excluded = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "staticfiles",
            "media",
            "private_media",
            "__pycache__",
        }

        bad_tokens = (
            "ad" + "sterra",
            "highperformanceformat.com",
            "profitabledisplaynetwork.com",
        )

        leftovers = []

        for source_root in (root / "templates", root / "static"):
            if not source_root.exists():
                continue

            for path in source_root.rglob("*"):
                if not path.is_file():
                    continue

                relative = path.relative_to(root)

                if any(part in excluded for part in relative.parts):
                    continue

                if path.suffix.lower() not in {
                    ".html", ".htm", ".js", ".jsx",
                    ".ts", ".tsx", ".css", ".scss"
                }:
                    continue

                try:
                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    ).lower()
                except OSError:
                    continue

                if any(token in content for token in bad_tokens):
                    leftovers.append(str(relative))

        self.assertEqual(
            leftovers,
            [],
            "Old legacy ad-network references remain in: "
            + ", ".join(leftovers),
        )
