from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.middleware import AdcashCSPMiddleware


class AdcashSecondaryCSPTests(SimpleTestCase):
    def setUp(self):
        self.middleware = AdcashCSPMiddleware(
            self._response
        )

    def _response(self, request):
        response = HttpResponse("ok")

        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; "
            "connect-src 'self' "
            "https://www.google-analytics.com; "
            "frame-src 'self';"
        )

        return response

    def _policy(self):
        response = self.middleware(
            RequestFactory().get(
                "/lms/courses/"
            )
        )

        return response[
            "Content-Security-Policy"
        ]

    def _directive(self, policy, name):
        for part in policy.split(";"):
            part = part.strip()

            if part.startswith(name + " "):
                return part

        return ""

    def test_primary_adcash_hosts_are_allowed_for_scripts(self):
        policy = self._policy()

        script_src = self._directive(
            policy,
            "script-src",
        )

        self.assertIn(
            "https://acscdn.com",
            script_src,
        )

        self.assertIn(
            "https://*.acscdn.com",
            script_src,
        )

    def test_secondary_provider_hosts_are_allowed_for_connections(self):
        policy = self._policy()

        connect_src = self._directive(
            policy,
            "connect-src",
        )

        required = (
            "https://my.rtmark.net",
            "https://jhnwr.com",
            "https://ldrws.com",
        )

        for host in required:
            self.assertIn(
                host,
                connect_src,
            )

    def test_secondary_hosts_are_not_unnecessarily_added_to_script_src(self):
        policy = self._policy()

        script_src = self._directive(
            policy,
            "script-src",
        )

        self.assertNotIn(
            "https://my.rtmark.net",
            script_src,
        )

        self.assertNotIn(
            "https://jhnwr.com",
            script_src,
        )

        self.assertNotIn(
            "https://ldrws.com",
            script_src,
        )

    def test_existing_csp_origins_are_preserved(self):
        policy = self._policy()

        self.assertIn(
            "https://cdn.jsdelivr.net",
            policy,
        )

        self.assertIn(
            "https://www.google-analytics.com",
            policy,
        )

    def test_adcash_runtime_connect_hosts_are_allowed(self):
        policy = self._policy()

        connect_src = self._directive(
            policy,
            "connect-src",
        )

        self.assertIn(
            "https://adexchangerapid.com",
            connect_src,
        )
        self.assertIn(
            "https://usrpubtrk.com",
            connect_src,
        )

    def test_adcash_blob_worker_is_allowed(self):
        policy = self._policy()

        worker_src = self._directive(
            policy,
            "worker-src",
        )

        self.assertIn("blob:", worker_src)
