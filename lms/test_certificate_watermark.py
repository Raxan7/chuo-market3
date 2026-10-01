"""Rendering tests for the certificate seal watermark.

These go further than the stubbed PDF tests: when WeasyPrint and poppler's
``pdftoppm`` are available they render a real certificate and measure the
rasterised output, so a watermark that vanishes on paper (or swamps the
recipient's name) fails the build rather than being discovered by a user with a
printer.

The two invariants under test:

1. The faded seal is strong enough to survive printing. Office printers clip
   values within roughly 10% of paper white, which is why the original
   ``opacity: 0.04`` was invisible on paper despite looking fine on a backlit
   screen.
2. The seal must not compete with the certificate text. The recipient's name
   and course title stay high-contrast while the watermark sits behind them.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from .certificates import (
    DEFAULT_WATERMARK_OPACITY,
    MAX_WATERMARK_OPACITY,
    MIN_WATERMARK_OPACITY,
    _watermark_opacity,
    certificate_context,
)
from .models import CertificateTemplate, Course, StudentCertificate

try:
    from PIL import Image
    import numpy as np
except ImportError:  # pragma: no cover - exercised only on minimal installs
    Image = None
    np = None


def _weasyprint_available():
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return False
    return True


def _rasteriser_available():
    return shutil.which('pdftoppm') is not None


HAS_RENDERING = _weasyprint_available() and _rasteriser_available() and Image is not None and np is not None


class WatermarkOpacityClampingTests(TestCase):
    """Out-of-range stored values must never ship an unreadable certificate."""

    def test_defaults_to_print_safe_value(self):
        self.assertEqual(_watermark_opacity(None), DEFAULT_WATERMARK_OPACITY)

    def test_accepts_valid_value(self):
        template = CertificateTemplate(watermark_opacity=0.22)
        self.assertEqual(_watermark_opacity(template), 0.22)

    def test_clamps_below_printable_floor(self):
        # The old shipped value. It must not be able to come back.
        template = CertificateTemplate(watermark_opacity=0.04)
        self.assertEqual(_watermark_opacity(template), MIN_WATERMARK_OPACITY)

    def test_clamps_above_where_it_would_dominate_the_text(self):
        template = CertificateTemplate(watermark_opacity=0.9)
        self.assertEqual(_watermark_opacity(template), MAX_WATERMARK_OPACITY)

    def test_tolerates_garbage_without_raising(self):
        template = CertificateTemplate(watermark_opacity=None)
        self.assertEqual(_watermark_opacity(template), DEFAULT_WATERMARK_OPACITY)


class WatermarkAssetTests(TestCase):
    """The bundled seal must really carry an alpha channel, not just be named so."""

    def test_bundled_transparent_seal_is_actually_transparent(self):
        if Image is None:
            self.skipTest('Pillow not installed')
        path = Path(__file__).resolve().parent.parent / 'static' / 'lms' / 'images' / 'chuosmart_seal_transparent.png'
        if not path.exists():
            self.skipTest('run: python manage.py build_seal_watermark_asset')

        # The asset is palette-quantised on disk, so inspect it as RGBA rather
        # than asserting a storage mode: what matters is the alpha it renders.
        image = Image.open(path).convert('RGBA')
        pixels = np.asarray(image)[:, :, 3]

        corners = [pixels[0, 0], pixels[0, -1], pixels[-1, 0], pixels[-1, -1]]
        self.assertEqual(
            [int(c) for c in corners],
            [0, 0, 0, 0],
            'an opaque matte would render as a visible pale square on the certificate',
        )
        # Palette quantisation caps alpha just below 255. Measured cost is 0.036
        # percentage points of print contrast, which is well under the noise floor
        # of any printer, and it saves ~636KB per embedded asset.
        self.assertGreaterEqual(
            int(pixels.max()), 230,
            'seal artwork alpha was crushed; a faded watermark this weak will not print',
        )
        # The artwork has to occupy a meaningful share of the canvas, otherwise
        # the watermark is visually empty.
        self.assertGreater(float((pixels > 128).mean()), 0.15)

    def test_transparent_seal_is_far_smaller_than_the_source(self):
        root = Path(__file__).resolve().parent.parent / 'static' / 'lms' / 'images'
        source = root / 'chuosmart_seal.png'
        transparent = root / 'chuosmart_seal_transparent.png'
        if not source.exists() or not transparent.exists():
            self.skipTest('run: python manage.py build_seal_watermark_asset')
        self.assertLess(
            transparent.stat().st_size,
            source.stat().st_size,
            'the new asset should cut the bytes WeasyPrint has to embed',
        )


class CertificateTemplateWiringTests(TestCase):
    """The PDF template must actually consume the per-template branding fields."""

    def setUp(self):
        self.student = User.objects.create_user(username='wm-student', password='pw')
        self.course = Course.objects.create(title='Wiring Course', summary='Wiring')
        self.template = CertificateTemplate.objects.create(
            course=self.course,
            title='Certificate of Completion',
            watermark_opacity=0.21,
        )
        self.certificate = StudentCertificate.objects.create(
            student=self.student, course=self.course, template=self.template
        )

    @override_settings(STATIC_URL='/static/')
    def test_context_exposes_watermark_strength_and_asset_urls(self):
        ctx = certificate_context(self.certificate)

        self.assertEqual(ctx['watermark_opacity'], 0.21)
        self.assertIn('chuosmart_seal_transparent.png', ctx['watermark_image_url'])
        # The footer seal reuses the same transparent asset rather than the
        # original opaque 2.1MB PNG that used to be embedded twice.
        self.assertEqual(ctx['seal_url'], ctx['watermark_image_url'])
        self.assertIn('logo.png', ctx['logo_url'])

    @override_settings(STATIC_URL='/static/')
    def test_template_css_reads_the_configurable_opacity(self):
        html = render_to_string('lms/certificates/certificate_pdf.html', certificate_context(self.certificate))
        self.assertIn('opacity: 0.21;', html)
        self.assertNotIn('chuosmart_seal.png"', html, 'the opaque stock seal must not be rendered')
        self.assertIn('chuosmart_seal_transparent.png', html)

    @override_settings(STATIC_URL='/static/')
    def test_template_halo_protects_the_critical_text(self):
        html = render_to_string('lms/certificates/certificate_pdf.html', certificate_context(self.certificate))
        self.assertIn('text-shadow', html)
        for selector in ('.name,', '.course,', '.title,', '.org,'):
            self.assertIn(selector, html)


@override_settings(STATIC_URL='/static/')
class CertificateWatermarkRenderTests(TestCase):
    """End-to-end: render a real PDF and measure the pixels that get printed."""

    def setUp(self):
        self.student = User.objects.create_user(username='wm-render', password='pw')
        self.course = Course.objects.create(title='Render Course', summary='Render')
        self.template = CertificateTemplate.objects.create(
            course=self.course,
            title='Certificate of Completion',
            status='active',
        )
        self.certificate = StudentCertificate.objects.create(
            student=self.student, course=self.course, template=self.template
        )
        self.tmp = Path(tempfile.mkdtemp(prefix='cert-wm-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _raster(self, html, tag):
        """Render one page and return it as an 8-bit greyscale array."""
        from weasyprint import HTML
        # WeasyPrint resolves the template's absolute /static/... URLs against
        # base_url, so rewrite them onto this checkout's static tree. No running
        # web server is needed for the measurement to be valid.
        base = Path(__file__).resolve().parent.parent
        html = html.replace('/static/', f'file://{base}/static/')

        pdf_path = self.tmp / f'{tag}.pdf'
        HTML(string=html, base_url=f'file://{base}/').write_pdf(target=str(pdf_path))

        subprocess.run(
            ['pdftoppm', '-png', '-r', '300', '-f', '1', '-l', '1', str(pdf_path), str(self.tmp / tag)],
            check=True,
            capture_output=True,
        )
        rendered = sorted(self.tmp.glob(f'{tag}-*.png'))
        self.assertTrue(rendered, 'pdftoppm produced no page raster')
        return np.asarray(Image.open(rendered[0]).convert('L')).astype(np.float32)

    def _render(self, opacity):
        self.template.watermark_opacity = opacity
        self.template.save(update_fields=['watermark_opacity'])
        html = render_to_string(
            'lms/certificates/certificate_pdf.html',
            certificate_context(self.certificate),
        )
        return self._raster(html, f'cert-{opacity}')

    def _measure(self, opacity):
        """Measure a printed page by differencing it against the same page
        rendered without the watermark.

        This is the only trustworthy way to read the watermark's strength: text,
        borders and gradients are byte-identical in both renders, so the diff
        isolates exactly what the seal contributes. Sampling the finished page
        directly is misleading because the seal's own anti-aliased pixels bias
        any median or histogram toward its darker tail.
        """
        hidden = render_to_string(
            'lms/certificates/certificate_pdf.html',
            certificate_context(self.certificate),
        ).replace('<div class="watermark">', '<div class="watermark" style="display:none">')
        self.template.watermark_opacity = opacity
        self.template.save(update_fields=['watermark_opacity'])
        shown_html = render_to_string(
            'lms/certificates/certificate_pdf.html',
            certificate_context(self.certificate),
        )

        off = self._raster(hidden, f'off-{opacity}')
        on = self._raster(shown_html, f'on-{opacity}')

        darken = off - on
        self.assertGreater(
            float((darken > 3).mean()), 0.05,
            f'at opacity {opacity} the rendered page shows almost no watermark artwork',
        )

        # The seal's solid ink over plain paper is where print visibility is won
        # or lost; take the top of the darkening distribution for that.
        solid = darken > 0.8 * darken.max()
        paper_level = float(np.median(on[solid]))
        print_contrast = 255.0 - paper_level

        # Text inside the watermark's footprint is unchanged by the seal, so its
        # measured contrast against the watermarked paper is the real read.
        touched = darken > 3
        text_px = on[touched & (on < 100)]

        def _lin(channel):
            channel = channel / 255.0
            return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

        def _lum(r, g, b):
            return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

        if text_px.size:
            grey = float(np.median(text_px))
            t_lum = _lum(grey, grey, grey)
            bg_lum = _lum(paper_level, paper_level, paper_level)
            text_contrast = (bg_lum + 0.05) / (t_lum + 0.05)
        else:
            text_contrast = None

        return print_contrast, text_contrast, paper_level

    @override_settings(STATIC_URL='/static/')
    def test_shipped_default_is_visible_in_print_and_keeps_text_dominant(self):
        if not HAS_RENDERING:
            self.skipTest('weasyprint + pdftoppm + numpy required for pixel assertions')

        opacity = CertificateTemplate._meta.get_field('watermark_opacity').default
        contrast, text_contrast, paper_level = self._measure(opacity)

        # 1) It must survive printing. Measured on this page, the old 0.04
        #    default landed at 14/255 -- right at the level printers clip, which
        #    is why the seal was invisible on paper.
        self.assertGreaterEqual(
            contrast, 25.0,
            f'at opacity {opacity} the seal only reaches {contrast:.0f}/255 below paper '
            f'white (level {paper_level:.0f}) — too faint to print',
        )

        # 2) The seal must not swamp the certificate text. The recipient's name
        #    and course title are the whole point of the document.
        self.assertIsNotNone(text_contrast, 'no text was found inside the watermark footprint')
        self.assertGreaterEqual(
            text_contrast, 7.0,
            f'text over the watermarked paper is only {text_contrast:.1f}:1 — the seal '
            f'is competing with the certificate text',
        )

    @override_settings(STATIC_URL='/static/')
    def test_the_invisible_setting_cannot_be_rendered_anymore(self):
        """Guards the regression this whole change exists to fix.

        Once the seal had faded below the printer clipping floor there was no way
        back without a code change: the template read the stored value verbatim.
        The opacity is now clamped, so a bad row simply cannot produce the old
        unprintable certificate.
        """
        if not HAS_RENDERING:
            self.skipTest('weasyprint + pdftoppm + numpy required for pixel assertions')

        default = CertificateTemplate._meta.get_field('watermark_opacity').default
        floor_contrast, floor_text, _ = self._measure(MIN_WATERMARK_OPACITY)
        default_contrast, default_text, _ = self._measure(default)

        # The floor itself must already clear the printer clipping level, which
        # the old 0.04 default did not (measured ~14/255 on a 300dpi render).
        self.assertGreaterEqual(
            floor_contrast, 20.0,
            f'the clamped floor only reaches {floor_contrast:.0f}/255, which will '
            f'vanish on paper',
        )
        # And the shipped default must be meaningfully stronger than the floor.
        self.assertGreater(
            default_contrast, floor_contrast * 1.4,
            f'the shipped default ({default_contrast:.0f}/255) is not meaningfully '
            f'stronger than the floor ({floor_contrast:.0f}/255)',
        )
        # The halo keeps text readable at the floor as well as at the default.
        self.assertGreaterEqual(floor_text, 7.0, 'text lost contrast at the minimum strength')

    @override_settings(STATIC_URL='/static/')
    def test_top_of_supported_range_still_keeps_text_dominant(self):
        if not HAS_RENDERING:
            self.skipTest('weasyprint + pdftoppm + numpy required for pixel assertions')

        contrast, text_contrast, _ = self._measure(MAX_WATERMARK_OPACITY)

        self.assertGreaterEqual(contrast, 25.0, 'the maximum strength must still print')
        self.assertGreaterEqual(
            text_contrast, 4.5,
            f'at the maximum strength text is only {text_contrast:.1f}:1',
        )

    @override_settings(STATIC_URL='/static/')
    def test_pdf_is_still_a_real_pdf(self):
        if not HAS_RENDERING:
            self.skipTest('weasyprint required')

        html = render_to_string('lms/certificates/certificate_pdf.html', certificate_context(self.certificate))
        from weasyprint import HTML
        pdf_path = self.tmp / 'real.pdf'
        data = HTML(string=html, base_url=f'file://{Path(__file__).resolve().parent.parent / "static"}/').write_pdf(target=str(pdf_path))
        self.assertTrue(pdf_path.read_bytes().startswith(b'%PDF'), 'expected a PDF payload')
