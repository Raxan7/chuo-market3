from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ManifestRouteTests(SimpleTestCase):
    def test_manifest_source_exists(self):
        manifest = (
            Path(settings.BASE_DIR)
            / 'static'
            / 'manifest.json'
        )

        self.assertTrue(
            manifest.exists()
        )

    def test_manifest_is_available_at_site_root(self):
        response = self.client.get(
            '/manifest.json'
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response['Content-Type'],
            'application/manifest+json',
        )

    def test_base_template_declares_manifest(self):
        base = (
            Path(settings.BASE_DIR)
            / 'templates'
            / 'app'
            / 'base.html'
