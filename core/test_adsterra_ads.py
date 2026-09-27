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

    def test_adsterra_card_is_sponsored_outbound_link_not_iframe(self):
        request = self.factory.get("/marketplace/?page=2")
        request.user = AnonymousUser()
        html = render_to_string(
            "app/partials/adsterra_ad_card.html",
            {"show_list_ads": True, "forloop": {"counter": 6}},
            request=request,
        )
        selected = select_adsterra_smartlink(request.get_full_path(), occurrence=6)
        self.assertIn(selected["url"], html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="sponsored nofollow noopener"', html)
        self.assertIn("data-adsterra-smartlink", html)
        self.assertNotIn("<iframe", html)

    def test_list_ad_switch_suppresses_adsterra_card(self):
        request = self.factory.get("/marketplace/")
        request.user = AnonymousUser()
        html = render_to_string(
            "app/partials/adsterra_ad_card.html",
            {"show_list_ads": False, "forloop": {"counter": 6}},
            request=request,
        )
        self.assertNotIn(ADSTERRA_SMARTLINK_HOST, html)
        self.assertNotIn("data-adsterra-smartlink", html)

    def test_csp_already_recognizes_adsterra_host(self):
        self.assertIn(
            "https://www.profitableratecpmnetwork.com",
            SecurityHeadersMiddleware.CSP_DIRECTIVES["frame-src"],
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
