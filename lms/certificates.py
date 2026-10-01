"""Certificate rendering and issuing helpers."""

import base64
import hashlib
import hmac
import io
import logging

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

# Keep the watermark faint enough that the recipient's name and course title stay
# dominant, but far enough above the printer clipping floor that the seal still
# shows on paper rather than only on a backlit screen.
#
# These bounds come from measuring a real 300dpi print render of the PDF
# template, diffing a watermark-on page against a watermark-off page:
#
#   opacity  paper level  print contrast  text contrast
#   0.04     241          14 (clipped)    6.4:1  <- the old default: vanishes
#   0.08     235          20              7.1:1
#   0.15     219          36              11.1:1 <- shipped default
#   0.22     203          52               9.6:1
#   0.30     191          64               8.9:1
#   0.45     153          102              5.6:1  <- reads as a solid seal
MIN_WATERMARK_OPACITY = 0.08
MAX_WATERMARK_OPACITY = 0.30
DEFAULT_WATERMARK_OPACITY = 0.15


def _watermark_opacity(template):
    """Clamp a template's stored watermark strength into the printable range.

    Guards against legacy rows, hand-edited values and nulls, none of which
    should be able to produce an unreadable or invisible certificate.
    """
    if template is None:
        return DEFAULT_WATERMARK_OPACITY
    try:
        value = float(template.watermark_opacity)
    except (TypeError, ValueError, AttributeError):
        return DEFAULT_WATERMARK_OPACITY
    return max(MIN_WATERMARK_OPACITY, min(MAX_WATERMARK_OPACITY, value))

PLACEHOLDER_KEYS = (
    'student_name',
    'course_title',
    'completion_date',
    'instructor_name',
    'certificate_id',
    'organization_name',
)


def _signing_key():
    """Return the HMAC key used to sign certificate verification URLs."""
    key = getattr(settings, 'CERTIFICATE_SIGNING_SECRET', '') or settings.SECRET_KEY
    return key.encode('utf-8')


def _sign_certificate(certificate):
    """Produce an HMAC-SHA256 signature for a ``StudentCertificate``.

    Signs ``{certificate_id}:{issued_at_iso}[:{expires_at_iso}]`` so that
    anyone can verify the certificate was issued by this server.
    The signature is returned as a URL-safe base64 string (no padding).
    """
    message = f"{certificate.certificate_id}:{certificate.issued_at.isoformat()}"
    if certificate.expires_at:
        message += f":{certificate.expires_at.isoformat()}"
    digest = hmac.new(_signing_key(), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def _signed_verification_url(certificate, request=None):
    """Build the verification URL with an HMAC signature as ``?sig=``.

    Example:  ``/lms/certificates/verify/CHUO-20260625-ABCD/?sig=<token>``
    """
    path = reverse('lms:certificate_verify', kwargs={'certificate_id': certificate.certificate_id})
    sig = _sign_certificate(certificate)
    signed_path = f"{path}?sig={sig}"
    if request:
        return request.build_absolute_uri(signed_path)
    return signed_path


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


def _asset_url(field_value, fallback=None):
    """Return the uploaded URL, or ``fallback`` when no file is configured."""
    if field_value and getattr(field_value, 'name', ''):
        return field_value.url
    return fallback or ''


def _default_seal_url():
    """The bundled transparent seal, unless the deployment overrode it."""
    return staticfiles_storage.url('lms/images/chuosmart_seal_transparent.png')


def certificate_context(certificate, request=None):
    """Build the template context for certificate rendering."""
    template = certificate.template
    student_name = _resolve_student_name(certificate.student)
    instructor_name = _resolve_instructor_name(certificate.course, template)
    completion_date = timezone.localtime(certificate.issued_at).strftime('%B %d, %Y')
    verification_path = reverse('lms:certificate_verify', kwargs={'certificate_id': certificate.certificate_id})
    verification_url = request.build_absolute_uri(verification_path) if request else verification_path
    signed_verify_url = _signed_verification_url(certificate, request=request)
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

    footer_note = (template.footer_note if template else '') or ''
    for key in PLACEHOLDER_KEYS:
        footer_note = footer_note.replace('{{ ' + key + ' }}', values[key]).replace('{{' + key + '}}', values[key])

    return {
        'certificate': certificate,
        'template': template,
        'student_name': student_name,
        'instructor_name': instructor_name,
        'completion_date': completion_date,
        'verification_url': verification_url,
        'signed_verification_url': signed_verify_url,
        'rendered_body': body,
        'qr_data_uri': _qr_data_uri(signed_verify_url) if (template and template.show_qr_code) else '',
        'logo_url': _asset_url(template.logo if template else None, staticfiles_storage.url('app/images/logo.png')),
        'signature_image_url': _asset_url(template.signature_image if template else None, ''),
        'seal_url': _asset_url(template.seal_image if template else None, _default_seal_url()),
        'watermark_image_url': _asset_url(template.watermark_image if template else None, _default_seal_url()),
        'watermark_opacity': _watermark_opacity(template),
        'footer_note': footer_note,
        'signature_name': (template.instructor_signature_text if template else '') or instructor_name,
        **values,
    }
