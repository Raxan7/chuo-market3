from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.middleware import MonetagCSPMiddleware
from lms.course_permissions import user_owns_course


class ProductionHotfixTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(settings.BASE_DIR)

    def test_monetag_csp_extends_script_policy(self):
        def app(_request):
            response = HttpResponse("ok")
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-src 'self';"
            )
            return response

        middleware = MonetagCSPMiddleware(app)

        response = middleware(
            RequestFactory().get("/lms/courses/")
        )

        csp = response["Content-Security-Policy"]

        self.assertIn("https://nap5k.com", csp)
        self.assertIn("https://n6wxm.com", csp)

    def test_monetag_middleware_precedes_security_headers(self):
        settings_text = (
            self.root
            / "Commerce"
            / "settings"
            / "base.py"
        ).read_text(encoding="utf-8")

        monetag = settings_text.index(
            "core.middleware.MonetagCSPMiddleware"
        )

        security = settings_text.index(
            "core.middleware.SecurityHeadersMiddleware"
        )

        self.assertLess(monetag, security)

    def test_dashboard_theme_patch_is_present(self):
        template = (
            self.root
            / "templates"
            / "app"
            / "dashboard.html"
        ).read_text(encoding="utf-8")

        css = (
            self.root
            / "static"
            / "chuosmart_v2"
            / "css"
            / "site.css"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "cs-v2-dashboard-panel",
            template,
        )

        self.assertIn(
            "CHUOSMART DASHBOARD THEME HARDENING V1",
            css,
        )

    def test_course_owner_helper_accepts_instructor_profile(self):
        user = SimpleNamespace(
            pk=17,
            is_authenticated=True,
        )

        course = SimpleNamespace(
            instructor=SimpleNamespace(
                user_id=17
            )
        )

        self.assertTrue(
            user_owns_course(user, course)
        )

    def test_non_owner_is_rejected(self):
        user = SimpleNamespace(
            pk=18,
            is_authenticated=True,
        )

        course = SimpleNamespace(
            instructor=SimpleNamespace(
                user_id=17
            )
        )

        self.assertFalse(
            user_owns_course(user, course)
        )

    def test_course_delete_route_and_template_exist(self):
        urls = (
            self.root
            / "lms"
            / "urls.py"
        ).read_text(encoding="utf-8")

        views = (
            self.root
            / "lms"
            / "views.py"
        ).read_text(encoding="utf-8")

        template = (
            self.root
            / "lms"
            / "templates"
            / "lms"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "name='course_delete'",
            urls,
        )

        self.assertIn(
            "_course_delete_require_POST",
            views,
        )

        self.assertIn(
            "Delete course",
            template,
        )

        self.assertIn(
            "is_course_instructor",
            template,
        )

    def test_manifest_exists(self):
        self.assertTrue(
            (
                self.root
                / "static"
                / "manifest.json"
            ).exists()
        )
