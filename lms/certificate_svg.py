"""Certificate SVG-to-PDF generation for pixel-perfect output."""

import base64
import functools
import logging
import os
import tempfile

from django.conf import settings
from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

# ── SVG constants (A4 landscape in points, 1 pt = 1/72″) ──────────
W, H = 842, 595
PAD = 40  # canvas → outer frame
GAP = 23  # outer frame → inner border (~8 mm)
INNER_PAD_X = 40  # inner border → content (~14 mm)
INNER_PAD_Y = 28  # inner border → content (~10 mm)

X0 = PAD + GAP + INNER_PAD_X  # content left
X1 = W - X0                   # content right
CX = W // 2                   # centre X
CW = X1 - X0                  # content width

Y0 = PAD + GAP + INNER_PAD_Y  # content top
Y1 = H - Y0                   # content bottom

# ── Helpers ───────────────────────────────────────────────────────


def _b64(path):
    """Return a data-URI for a local image file."""
    with open(path, 'rb') as f:
        raw = f.read()
    ext = os.path.splitext(path)[1].lstrip('.').lower()
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'gif': 'image/gif', 'svg': 'image/svg+xml'}.get(ext, 'image/png')
    return f'data:{mime};base64,{base64.b64encode(raw).decode()}'


def _resolve_img(relative_path):
    """Resolve a static-relative path to an absolute filesystem path."""
    # Django finder (most reliable)
    result = finders.find(relative_path)
    if result:
        if isinstance(result, (list, tuple)):
            return result[0]
        return result
    # Direct file look-up as fallback
    candidates = [settings.BASE_DIR]
    static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
    if isinstance(static_dirs, (list, tuple)):
        candidates.extend(static_dirs)
    for base in candidates:
        candidate = os.path.join(base, relative_path).replace('/', os.sep)
        if os.path.exists(candidate):
            return candidate
    return None


# ── SVG template ──────────────────────────────────────────────────


def _build_defs():
    """Return SVG <defs> block with gradients shared across the page."""
    return f'''\
  <defs>
    <radialGradient id="glowT" cx="50%" cy="-5%" r="70%">
      <stop offset="0%" stop-color="#F5C148" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#F5C148" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="50%" cy="105%" r="60%">
      <stop offset="0%" stop-color="#0B1437" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="#0B1437" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="innerBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#FFFBEB"/>
    </linearGradient>
    <linearGradient id="underline" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="transparent"/>
      <stop offset="25%" stop-color="#1FAA59"/>
      <stop offset="50%" stop-color="#0d6efd"/>
      <stop offset="75%" stop-color="#1FAA59"/>
      <stop offset="100%" stop-color="transparent"/>
    </linearGradient>
  </defs>'''


def _bg():
    """Return background layers."""
    return f'''\
  <rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>
  <rect x="0" y="0" width="{W}" height="{H}" fill="url(#glowT)"/>
  <rect x="0" y="0" width="{W}" height="{H}" fill="url(#glowB)"/>'''


def _corners():
    """Return L‑shaped corner ornaments (gold brackets)."""
    s, t = 44, 3  # size & stroke-width
    g = f' stroke="#F5C148" stroke-width="{t}" fill="none"'
    # top‑left
    tl = f'<path d="M{PAD},{PAD + s} L{PAD},{PAD} L{PAD + s},{PAD}"{g}/>'
    # bottom‑right
    br = f'<path d="M{W - PAD - s},{H - PAD} L{W - PAD},{H - PAD} L{W - PAD},{H - PAD - s}"{g}/>'
    return tl + '\n  ' + br


def _frames():
    """Return outer gold double-border + inner navy border."""
    f1 = PAD
    f2 = PAD + GAP
    fw = W - 2 * f1
    fw2 = W - 2 * f2
    fh = H - 2 * f1
    fh2 = H - 2 * f2
    return f'''\
  <rect x="{f1}" y="{f1}" width="{fw}" height="{fh}" rx="0" ry="0"
        fill="#ffffff" stroke="#F5C148" stroke-width="5"/>
  <rect x="{f1 + 3}" y="{f1 + 3}" width="{fw - 6}" height="{fh - 6}" rx="0" ry="0"
        fill="none" stroke="#F5C148" stroke-width="1.5"/>
  <rect x="{f2}" y="{f2}" width="{fw2}" height="{fh2}" rx="0" ry="0"
        fill="url(#innerBg)" stroke="#0B1437" stroke-width="1.5"/>'''


@functools.lru_cache(maxsize=2)
def _logo_b64():
    """Return base64-URI for the logo, or a fallback circle."""
    path = _resolve_img('app/images/logo.png')
    if path and os.path.exists(path):
        return _b64(path)
    return None


@functools.lru_cache(maxsize=2)
def _seal_b64():
    """Return base64-URI for the seal, or a fallback circle."""
    path = _resolve_img('lms/images/chuosmart_seal.png')
    if path and os.path.exists(path):
        return _b64(path)
    return None


def _escape(text):
    """Escape text for safe embedding in XML/SVG."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))


def _svg_certificate(certificate, request=None):
    """Generate the complete certificate as an SVG string."""
    from .certificates import certificate_context

    ctx = certificate_context(certificate, request=request)

    logo_uri = _logo_b64()
    seal_uri = _seal_b64()

    student = _escape(ctx.get('student_name', ''))
    course = _escape(ctx.get('course_title', ''))
    date = _escape(ctx.get('completion_date', ''))
    instructor = _escape(ctx.get('instructor_name', 'Course Instructor'))
    org = _escape(ctx.get('organization_name', ''))
    title = _escape(ctx.get('template').title if ctx.get('template') else 'Certificate of Completion')
    subtitle = _escape(ctx.get('template').subtitle if ctx.get('template') else 'Awarded in recognition of successful course completion')
    cert_id = _escape(ctx.get('certificate_id', ''))
    verify = _escape(ctx.get('verification_url', ''))
    body = _escape(ctx.get('rendered_body', ''))

    # Y‑positions
    y_logo = Y0 + 10
    y_org = y_logo + 85
    y_title = y_org + 32
    y_subtitle = y_title + 42
    y_presented = y_subtitle + 32
    y_name = y_presented + 26
    y_uline = y_name + 58
    y_body = y_uline + 20
    y_course = y_body + (36 if body else 4)
    y_date = y_course + 36
    y_footer = max(y_date + 40, Y1 - 120)

    return f'''\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{W}px" height="{H}px" viewBox="0 0 {W} {H}">
{_build_defs()}
{_bg()}
{_corners()}
{_frames()}

  <!-- ── Logo ── -->
  <g transform="translate({CX - 40}, {y_logo})">
    <clipPath id="logoClip"><rect width="80" height="80" rx="8"/></clipPath>
    <g clip-path="url(#logoClip)">
      <image x="0" y="0" width="80" height="80"
             xlink:href="{logo_uri if logo_uri else ''}" preserveAspectRatio="xMidYMid meet"/>
    </g>
  </g>

  <!-- ── Organisation ── -->
  <text x="{CX}" y="{y_org}" text-anchor="middle"
        font-family="Arial,Helvetica,sans-serif" font-size="11"
        font-weight="700" letter-spacing="4" fill="#1FAA59">{org}</text>

  <!-- ── Title ── -->
  <text x="{CX}" y="{y_title}" text-anchor="middle"
        font-family="Georgia,Times New Roman,serif" font-size="36"
        font-weight="700" letter-spacing="3" fill="#0d6efd">{title}</text>

  <!-- ── Subtitle ── -->
  <text x="{CX}" y="{y_subtitle}" text-anchor="middle"
        font-family="Georgia,Times New Roman,serif" font-size="14"
        font-style="italic" fill="#4B5563">{subtitle}</text>

  <!-- ── Presented to ── -->
  <text x="{CX}" y="{y_presented}" text-anchor="middle"
        font-family="Arial,Helvetica,sans-serif" font-size="11"
        font-weight="700" letter-spacing="2.5" fill="#6B7280">THIS CERTIFICATE IS PROUDLY PRESENTED TO</text>

  <!-- ── Student name ── -->
  <text x="{CX}" y="{y_name}" text-anchor="middle"
        font-family="Brush Script MT,Lucida Handwriting,cursive" font-size="56"
        font-weight="700" fill="#0d6efd"
        style="text-shadow: 0 1px 0 rgba(13,110,253,0.08)">{student}</text>

  <!-- ── Underline ── -->
  <rect x="{CX - 230}" y="{y_uline}" width="460" height="2" rx="1" fill="url(#underline)"/>

  <!-- ── Body ──
  <text x="{CX}" y="{y_body}" text-anchor="middle"
        font-family="Georgia,Times New Roman,serif" font-size="14"
        fill="#4B5563">{body}</text> -->

  <!-- ── Course title ── -->
  <text x="{CX}" y="{y_course}" text-anchor="middle"
        font-family="Georgia,Times New Roman,serif" font-size="22"
        font-weight="700" fill="#0d6efd">{course}</text>

  <!-- ── Date ── -->
  <text x="{CX}" y="{y_date}" text-anchor="middle"
        font-family="Georgia,Times New Roman,serif" font-size="13"
        fill="#4B5563">Issued on {date}</text>

  <!-- ── Footer ── -->
  <!-- Instructor signature -->
  <g transform="translate({X0 + 20}, {y_footer})">
    <text x="0" y="0"
          font-family="Brush Script MT,Lucida Handwriting,cursive" font-size="24"
          fill="#111827">{instructor}</text>
    <line x1="0" y1="6" x2="200" y2="6" stroke="#111827" stroke-width="1.5"/>
    <text x="0" y="22" font-family="Arial,Helvetica,sans-serif" font-size="10"
          font-weight="700" letter-spacing="1.5" fill="#111827">{instructor}</text>
    <text x="0" y="36" font-family="Arial,Helvetica,sans-serif" font-size="10"
          letter-spacing="1.5" fill="#4B5563">COURSE INSTRUCTOR</text>
  </g>

  <!-- Seal -->
  <g transform="translate({CX - 45}, {y_footer - 10})">
    <image x="0" y="0" width="90" height="90"
           xlink:href="{seal_uri if seal_uri else ''}" preserveAspectRatio="xMidYMid meet"/>
  </g>

  <!-- Certificate ID + verify -->
  <g transform="translate({X1 - 220}, {y_footer})">
    <text x="200" y="0" text-anchor="end"
          font-family="Arial,Helvetica,sans-serif" font-size="9"
          font-weight="700" letter-spacing="1.5" fill="#6B7280">CERTIFICATE ID</text>
    <text x="200" y="16" text-anchor="end"
          font-family="Courier New,monospace" font-size="11"
          fill="#4B5563">{cert_id}</text>
    <text x="200" y="38" text-anchor="end"
          font-family="Arial,Helvetica,sans-serif" font-size="9"
          font-weight="700" letter-spacing="1.5" fill="#6B7280">VERIFY ONLINE</text>
    <text x="200" y="54" text-anchor="end"
          font-family="Arial,Helvetica,sans-serif" font-size="10"
          fill="#0d6efd">{verify}</text>
  </g>

</svg>'''


def certificate_svg_pdf(certificate, request=None):
    """Generate certificate as SVG → convert to PDF.

    Strategies:
    A. Playwright + Chrome (fast, full SVG support)
    B. svglib + reportlab (pure Python, no system deps)
    """
    svg = _svg_certificate(certificate, request=request)

    # Strategy A: Playwright render the SVG in a browser page
    try:
        from playwright.sync_api import sync_playwright

        html_page = f'''<!doctype html>
<html><body style="margin:0;padding:0">
  {svg}
</body></html>'''

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w',
                                         encoding='utf-8') as f:
            f.write(html_page)
            html_path = f.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, channel='chrome')
                page = browser.new_page()
                page.goto('file:///' + html_path.replace(os.sep, '/'))
                page.wait_for_load_state('networkidle')
                pdf_bytes = page.pdf(
                    format='A4', landscape=True,
                    margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
                    print_background=True,
                )
                browser.close()
            logger.info('Playwright SVG PDF OK: size=%d bytes', len(pdf_bytes))
            return pdf_bytes
        finally:
            try:
                os.unlink(html_path)
            except Exception:
                pass
    except Exception as exc:
        logger.warning('Playwright SVG PDF failed: %s', exc)

    # Strategy B: svglib + reportlab (pure Python, no system deps)
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        from io import BytesIO

        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False, mode='w',
                                         encoding='utf-8') as f:
            f.write(svg)
            svg_path = f.name

        try:
            drawing = svg2rlg(svg_path)
            if drawing is None:
                raise ValueError('svg2rlg returned None')

            buf = BytesIO()
            renderPDF.drawToFile(drawing, buf, fmt='PDF')
            pdf_bytes = buf.getvalue()

            logger.info('SVGLIB PDF OK: size=%d bytes', len(pdf_bytes))
            return pdf_bytes
        finally:
            try:
                os.unlink(svg_path)
            except Exception:
                pass
    except Exception as exc:
        logger.warning('svglib/reportlab PDF failed: %s', exc)

    return None
