"""Certificate rendering and issuing helpers."""

import logging
import os
import tempfile

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone


PLACEHOLDER_KEYS = (
    'student_name',
    'course_title',
    'completion_date',
    'instructor_name',
    'certificate_id',
    'organization_name',
)


def _resolve_student_name(user):
    """Prefer the user's saved legal name, then full name, then username."""
    if not user:
        return ''
    profile = getattr(user, 'lms_profile', None)
    if profile and profile.has_legal_name:
        return profile.display_legal_name
    return (user.get_full_name() or user.username or '').strip()


def _resolve_instructor_name(course, template=None):
    """Build the instructor name shown on the certificate.

    Falls back to the template's stored ``instructor_name`` for backwards
    compatibility, but always prefers the live ``legal_name`` of the
    course's instructors when available.
    """
    instructors = list(course.instructors.all()[:2]) if course else []
    names = []
    for instructor in instructors:
        if instructor.has_legal_name:
            names.append(instructor.display_legal_name)
        else:
            full = instructor.user.get_full_name() or instructor.user.username
            if full:
                names.append(full)

    if names:
        return ', '.join(names)
    if template and template.instructor_name:
        return template.instructor_name
    return 'Course Instructor'


def certificate_context(certificate, request=None):
    template = certificate.template
    student_name = _resolve_student_name(certificate.student)
    instructor_name = _resolve_instructor_name(certificate.course, template)
    completion_date = timezone.localtime(certificate.issued_at).strftime('%B %d, %Y')
    verification_path = reverse('lms:certificate_verify', kwargs={'certificate_id': certificate.certificate_id})
    verification_url = request.build_absolute_uri(verification_path) if request else verification_path
    values = {
        'student_name': student_name,
        'course_title': certificate.course.title,
        'completion_date': completion_date,
        'instructor_name': instructor_name,
        'certificate_id': certificate.certificate_id,
        'organization_name': template.organization_name if template else 'ChuoSmart Academy',
    }
    body = template.certificate_body if template else ''
    for key in PLACEHOLDER_KEYS:
        body = body.replace('{{ ' + key + ' }}', values[key]).replace('{{' + key + '}}', values[key])

    return {
        'certificate': certificate,
        'template': template,
        'student_name': student_name,
        'instructor_name': instructor_name,
        'completion_date': completion_date,
        'verification_url': verification_url,
        'rendered_body': body,
        **values,
    }


def certificate_html(certificate, request=None):
    return render_to_string(
        'lms/certificates/certificate_print.html',
        certificate_context(certificate, request=request),
    )


def _pdf_link_callback(uri, rel):
    """Resolve static file URIs for xhtml2pdf."""
    from django.conf import settings
    from django.contrib.staticfiles import finders

    if not uri.startswith(settings.STATIC_URL):
        return uri

    relative = uri[len(settings.STATIC_URL):].lstrip('/')

    # 1) Try finders.find — the canonical Django static-file lookup
    result = finders.find(relative)
    if result:
        if isinstance(result, (list, tuple)):
            return result[0]
        return result

    # 2) Fallback: walk STATICFILES_DIRS
    for d in settings.STATICFILES_DIRS:
        candidate = os.path.join(d, relative).replace('/', os.sep)
        if os.path.exists(candidate):
            return candidate

    # 3) Last-ditch: guess based on BASE_DIR + 'static'
    candidate = os.path.join(settings.BASE_DIR, 'static', relative).replace('/', os.sep)
    if os.path.exists(candidate):
        return candidate

    return uri


def _pdf_via_playwright(html, filename):
    """Generate PDF using Playwright with Chrome channel."""
    from playwright.sync_api import sync_playwright

    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
        f.write(html)
        html_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel='chrome')
            page = browser.new_page()
            page.goto('file:///' + html_path.replace(os.sep, '/'))
            page.wait_for_load_state('networkidle')
            pdf_bytes = page.pdf(
                format='A4',
                landscape=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
                print_background=True,
            )
            browser.close()
        return pdf_bytes
    finally:
        try:
            os.unlink(html_path)
        except Exception:
            pass


def certificate_pdf_response(certificate, request=None):
    """Generate and return a high-quality PDF certificate download.

    Strategies (in order):
    1. Playwright + Chrome (full CSS support: grid, gradients, pseudo-elements, flexbox)
    2. xhtml2pdf (pure Python, limited CSS)
    3. fpdf2 (pure Python, programmatic layout)
    4. HTML download fallback
    """
    logger = logging.getLogger(__name__)
    html = certificate_html(certificate, request=request)
    filename = f"{certificate.certificate_id}.pdf"

    # --- Strategy 1: Playwright with Chrome (best fidelity) ---
    try:
        pdf_bytes = _pdf_via_playwright(html, filename)
        if pdf_bytes and pdf_bytes[:5] == b'%PDF-':
            logger.info(
                "Playwright OK: cert=%s size=%d bytes",
                certificate.certificate_id, len(pdf_bytes),
            )
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        logger.warning("Playwright generated invalid PDF for %s", certificate.certificate_id)
    except Exception as exc:
        logger.warning("Playwright failed for %s: %s", certificate.certificate_id, exc)

    # --- Strategy 2: xhtml2pdf (pure Python, limited CSS) ---
    try:
        from xhtml2pdf import pisa
        from io import BytesIO

        result = BytesIO()
        pisa_status = pisa.CreatePDF(
            BytesIO(html.encode('utf-8')),
            dest=result,
            link_callback=_pdf_link_callback,
        )
        pdf_bytes = result.getvalue()
        if not pisa_status.err and pdf_bytes:
            logger.info(
                "xhtml2pdf OK: cert=%s size=%d bytes",
                certificate.certificate_id, len(pdf_bytes),
            )
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        logger.warning("xhtml2pdf generated empty PDF for %s", certificate.certificate_id)
    except Exception as exc:
        logger.warning("xhtml2pdf failed for %s: %s", certificate.certificate_id, exc)

    # --- Strategy 3: fpdf2 pure-Python fallback ---
    try:
        from fpdf import FPDF
        import html as html_mod

        ctx = certificate_context(certificate, request=request)
        student = html_mod.unescape(ctx.get('student_name', ''))
        course = html_mod.unescape(ctx.get('course_title', ''))
        date = ctx.get('completion_date', '')
        instructor = html_mod.unescape(ctx.get('instructor_name', ''))

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=False)

        pdf.set_fill_color(11, 20, 55)
        pdf.rect(0, 0, 297, 6, 'F')

        pdf.ln(10)
        pdf.set_font('Helvetica', 'B', 24)
        pdf.set_text_color(13, 110, 253)
        pdf.cell(0, 14, 'CERTIFICATE OF COMPLETION', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(75, 85, 99)
        pdf.cell(0, 8, 'This certificate is proudly presented to', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font('Helvetica', 'B', 32)
        pdf.set_text_color(13, 110, 253)
        pdf.cell(0, 20, student, align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(75, 85, 99)
        pdf.cell(0, 10, 'for successfully completing the course', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(13, 110, 253)
        pdf.cell(0, 12, course, align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(75, 85, 99)
        pdf.cell(0, 10, f'Issued on {date}', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.ln(10)
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(0, 6, f'Signed by: {instructor}', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.ln(4)
        pdf.set_font('Courier', '', 8)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(0, 6, f'Certificate ID: {certificate.certificate_id}', align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.set_fill_color(245, 193, 72)
        pdf.rect(0, 204, 297, 6, 'F')

        pdf_bytes = pdf.output()
        logger.info("fpdf2 OK: cert=%s size=%d bytes", certificate.certificate_id, len(pdf_bytes))
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as exc:
        logger.warning("fpdf2 failed for %s: %s", certificate.certificate_id, exc)

    # --- Final fallback: downloadable HTML ---
    logger.warning("All PDF strategies failed for %s; returning HTML", certificate.certificate_id)
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="{certificate.certificate_id}.html"'
    return response
