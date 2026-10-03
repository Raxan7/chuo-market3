from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CourseCatalogueDesktopColumnsTests(SimpleTestCase):
    def test_catalogue_defines_explicit_responsive_columns(self):
        root = Path(settings.BASE_DIR)

        css = ""

        for relative in (
            "static/chuosmart_v2/css/site.css",
            "static/chuosmart_v2/css/density.css",
        ):
            path = root / relative

            if path.exists():
                css += path.read_text(
                    encoding="utf-8"
                )

        self.assertIn(
            "CHUOSMART COURSE GRID DESKTOP COLUMNS V3",
            css,
        )

        self.assertIn(
            "repeat(4, minmax(0, 1fr))",
            css,
        )

        self.assertIn(
            "repeat(3, minmax(0, 1fr))",
            css,
        )

        self.assertIn(
            "repeat(2, minmax(0, 1fr))",
            css,
        )

    def test_mobile_still_has_single_column(self):
        root = Path(settings.BASE_DIR)

        css = ""

        for relative in (
            "static/chuosmart_v2/css/site.css",
            "static/chuosmart_v2/css/density.css",
        ):
            path = root / relative

            if path.exists():
                css += path.read_text(
                    encoding="utf-8"
                )

        self.assertIn(
            "grid-template-columns: 1fr !important;",
            css,
        )
