"""Certificate rendering and issuing helpers."""

import base64
import io
import logging

from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

PLACEHOLDER_KEYS = (
    'student_name',
    'course_title',
    'completion_date',
    'instructor_name',
    'certificate_id',
    'organization_name',
)


def _qr_data_uri(text, box_size=4, border=1):
    """Generate a QR code for *text* and return it as a ``data:image/png;base64,…`` URI.

    Falls back to empty string if the ``qrcode`` library is unavailable.
    """
    try:
        import qrcode
        from PIL import Image
    except ImportError:
        logger.warning("qrcode or Pillow not installed — skipping QR code generation")
        return ''

    try:
        qr = qrcode.make(text, box_size=box_size, border=border)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/png;base64,{b64}'
    except Exception as exc:
        logger.error("QR code generation failed for %r: %s", text[:60], exc)
        return ''


def _resolve_student_name(user):
    """Prefer the user's saved legal name, then full name, then username."""
    if not user:
        return ''
    profile = getattr(user, 'lms_profile', None)
    if profile and profile.has_legal_name:
        return profile.display_legal_name
    return (user.get_full_name() or user.username or '').strip()


def _resolve_instructor_name(course, template=None):
    """Build the instructor name shown on the certificate."""
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
    """Build the template context for certificate rendering."""
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
        'qr_data_uri': _qr_data_uri(verification_url) if (template and template.show_qr_code) else '',
        **values,
    }
