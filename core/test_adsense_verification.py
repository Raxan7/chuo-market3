from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class AdSenseVerificationTests(SimpleTestCase):

    def test_ads_txt(self):
        response = self.client.get("/ads.txt")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "google.com, pub-1815335112679958, DIRECT, f08c47fec0942fa0",
            response.content.decode("utf-8"),
        )

    def test_adsense_verification_meta_exists(self):
        base = (
            Path(settings.BASE_DIR)
            / "templates"
            / "app"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'name="google-adsense-account"',
            base,
        )

        self.assertIn(
            "ca-pub-1815335112679958",
            base,
        )
