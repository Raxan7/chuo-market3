import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from core.middleware import SecurityHeadersMiddleware
from core.templatetags.ad_tags import (
    ADSTERRA_SMARTLINK_HOST,
    ADSTERRA_SMARTLINKS,
    EXPECTED_ADSTERRA_SMARTLINK_COUNT,
    FORBIDDEN_ADSTERRA_SMARTLINK_NUMBERS,
    select_adsterra_smartlink,
)


ADSTERRA_DISPLAY_SCRIPT_ORIGIN = "https://www.highrevenueformat.com"
ADSTERRA_DESKTOP_KEY = "bddb20c8197be539197c4b2ee02363f0"
ADSTERRA_DESKTOP_SCRIPT_URL = (
    f"{ADSTERRA_DISPLAY_SCRIPT_ORIGIN}/"
    f"{ADSTERRA_DESKTOP_KEY}/invoke.js"
)
ADSTERRA_MOBILE_KEY = "ec22a6cfe1b3a979c2c1167a8f7e4d47"
ADSTERRA_MOBILE_SCRIPT_URL = (
    f"{ADSTERRA_DISPLAY_SCRIPT_ORIGIN}/"
    f"{ADSTERRA_MOBILE_KEY}/invoke.js"
)


class AdsterraSmartlinkTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_pool_contains_only_approved_unique_https_links(self):
        self.assertEqual(len(ADSTERRA_SMARTLINKS), EXPECTED_ADSTERRA_SMARTLINK_COUNT)
        numbers = {link["number"] for link in ADSTERRA_SMARTLINKS}
        self.assertEqual(len(numbers), EXPECTED_ADSTERRA_SMARTLINK_COUNT)
        self.assertTrue(numbers.isdisjoint(FORBIDDEN_ADSTERRA_SMARTLINK_NUMBERS))

        for link in ADSTERRA_SMARTLINKS:
            parsed = urlparse(link["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.hostname, ADSTERRA_SMARTLINK_HOST)
            self.assertEqual(len(parse_qs(parsed.query).get("key", [])), 1)

    def test_rotation_can_reach_every_approved_smartlink(self):
        selected = {
            select_adsterra_smartlink("/marketplace/", occurrence=6 * index)["number"]
            for index in range(1, EXPECTED_ADSTERRA_SMARTLINK_COUNT + 1)
        }
        self.assertEqual(len(selected), EXPECTED_ADSTERRA_SMARTLINK_COUNT)

    def test_rotation_is_stable_for_same_page_and_occurrence(self):
        first = select_adsterra_smartlink("/blog/?page=3", occurrence=12)
        second = select_adsterra_smartlink("/blog/?page=3", occurrence=12)
        self.assertEqual(first, second)

    def test_adsterra_card_renders_responsive_display_banner(self):
        request = self.factory.get("/marketplace/?page=2")
        request.user = AnonymousUser()

        html = render_to_string(
            "app/partials/adsterra_ad_card.html",
            {"show_list_ads": True, "forloop": {"counter": 6}},
            request=request,
        )

        self.assertIn("<iframe", html)
        self.assertIn('data-ad-type="adsterra-display"', html)
        self.assertIn(
            f'data-desktop-key="{ADSTERRA_DESKTOP_KEY}"',
            html,
        )
        self.assertIn(
            f'data-desktop-script-src="{ADSTERRA_DESKTOP_SCRIPT_URL}"',
            html,
        )
        self.assertIn(
            f'data-mobile-key="{ADSTERRA_MOBILE_KEY}"',
            html,
        )
        self.assertIn(
            f'data-mobile-script-src="{ADSTERRA_MOBILE_SCRIPT_URL}"',
            html,
        )
        self.assertNotIn("pl31147888.profitableratecpmnetwork.com", html)
        self.assertNotIn(">View offer<", html)

    def test_adsense_card_uses_direct_page_markup(self):
        html = render_to_string("app/partials/list_ad_card.html")

        self.assertIn(
            'class="adsbygoogle list-adsense-unit"',
            html,
        )
        self.assertIn(
            'data-ad-client="ca-pub-1815335112679958"',
            html,
        )
        self.assertIn('data-ad-slot="9477202901"', html)
        self.assertNotIn("<iframe", html)

    def test_list_ad_switch_suppresses_adsterra_card(self):
        request = self.factory.get("/marketplace/")
        request.user = AnonymousUser()

        html = render_to_string(
            "app/partials/adsterra_ad_card.html",
            {"show_list_ads": False, "forloop": {"counter": 6}},
            request=request,
        )

        self.assertNotIn(ADSTERRA_DISPLAY_SCRIPT_ORIGIN, html)
        self.assertNotIn('data-ad-type="adsterra-display"', html)

    def test_csp_allows_adsterra_display_banner_origins(self):
        for directive in ("script-src", "connect-src", "frame-src"):
            self.assertIn(
                ADSTERRA_DISPLAY_SCRIPT_ORIGIN,
                SecurityHeadersMiddleware.CSP_DIRECTIVES[directive],
            )

        for directive in ("connect-src", "frame-src"):
            self.assertIn(
                "https://*.highrevenueformat.com",
                SecurityHeadersMiddleware.CSP_DIRECTIVES[directive],
            )
            self.assertIn(
                "https://*.profitableratecpmnetwork.com",
                SecurityHeadersMiddleware.CSP_DIRECTIVES[directive],
            )

        self.assertNotIn(
            "https:",
            SecurityHeadersMiddleware.CSP_DIRECTIVES["script-src"],
        )

    def test_ad_initializer_uses_direct_adsense_and_display_banners(self):
        js_source = (
            Path(settings.BASE_DIR) / "static/app/js/base.js"
        ).read_text(encoding="utf-8")

        adsense_template = (
            Path(settings.BASE_DIR)
            / "templates/app/partials/list_ad_card.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'class="adsbygoogle list-adsense-unit"',
            adsense_template,
        )
        self.assertNotIn("<iframe", adsense_template)

        self.assertIn("function initAdsenseUnits", js_source)
        self.assertIn(
            "getBoundingClientRect().width",
            js_source,
        )
        self.assertIn(
            "window.adsbygoogle = window.adsbygoogle || []",
            js_source,
        )

        self.assertIn("adsterra-display", js_source)
        self.assertIn("window.atOptions", js_source)
        self.assertIn("data-desktop-key", js_source)
        self.assertIn("data-mobile-key", js_source)
        self.assertNotIn(
            "buildAdsterraNativeDocument",
            js_source,
        )



class ListAdTemplateWiringTests(SimpleTestCase):
    templates = (
        "templates/app/blog_list.html",
        "templates/app/marketplace.html",
        "lms/templates/lms/course_list.html",
        "materials/templates/materials/material_list.html",
    )

    pattern = re.compile(
        r"\{%\s*if show_list_ads\s*%\}.*?"
        r"\{%\s*if forloop\.counter\|divisibleby:3\s*%\}.*?"
        r"\{%\s*if forloop\.counter\|divisibleby:6\s*%\}.*?"
        r"app/partials/adsterra_ad_card\.html.*?"
        r"\{%\s*else\s*%\}.*?"
        r"app/partials/list_ad_card\.html",
        re.S,
    )

    def test_all_configured_list_surfaces_keep_google_then_adsterra_alternation(self):
        for relative_path in self.templates:
            with self.subTest(template=relative_path):
                source = (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")
                self.assertRegex(source, self.pattern)
                self.assertIn("adsterra-full-width-slot", source)
