import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CourseGridAndAdExperienceTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

        self.base = (
            self.root
            / "templates"
            / "app"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.catalogue = (
            self.root
            / "lms"
            / "templates"
            / "lms"
            / "course_list.html"
        ).read_text(encoding="utf-8")

        self.css = (
            self.root
            / "static"
            / "chuosmart_v2"
            / "css"
            / "site.css"
        ).read_text(encoding="utf-8")

    def test_popup_and_overlay_provider_scripts_are_disabled(self):
        forbidden = (
            "vignette.min.js",
            "11945568",
            "nap5k.com/tag.min.js",
            "11945562",
            "loadMonetagZone(",
        )

        for token in forbidden:
            self.assertNotIn(
                token,
                self.base,
                f"Popup/overlay provider remains active: {token}",
            )

    def test_direct_link_monetization_remains_enabled(self):
        self.assertIn(
            "monetag-direct-links.js",
            self.base,
        )

        direct_js = (
            self.root
            / "static"
            / "chuosmart_v2"
            / "js"
            / "monetag-direct-links.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "https://omg10.com/4/10558191",
            direct_js,
        )

        self.assertIn(
            "data-monetag-direct-link",
            direct_js,
        )

    def test_catalogue_uses_dedicated_course_grid(self):
        self.assertIn(
            'class="cs-course-catalog-grid"',
            self.catalogue,
        )

        self.assertIn(
            'class="cs-course-catalog-item"',
            self.catalogue,
        )

        self.assertIn(
            "CHUOSMART COURSE GRID NO-HOLES V2",
            self.css,
        )

        self.assertRegex(
            self.css,
            r"\.cs-course-catalog-grid\s*\{[^}]*display\s*:\s*grid",
        )

    def test_ad_cards_are_not_inside_course_loop(self):
        match = re.search(
            r"{%\s*for\s+course\s+in\s+[^%]+%}"
            r"(?P<body>.*?)"
            r"{%\s*endfor\s*%}",
            self.catalogue,
            flags=re.S,
        )

        self.assertIsNotNone(
            match,
            "Could not locate the course loop.",
        )

        body = match.group("body")

        self.assertNotIn(
            "list_ad_card.html",
            body,
        )

        self.assertNotIn(
            "vertical_ad_card.html",
            body,
        )

        self.assertNotIn(
            "adsterra_ad_card.html",
            body,
        )
