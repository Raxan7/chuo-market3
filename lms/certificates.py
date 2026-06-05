"""Certificate rendering and issuing helpers."""

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


def certificate_pdf_response(certificate, request=None):
    html = certificate_html(certificate, request=request)
    filename = f"{certificate.certificate_id}.pdf"

    try:
        import pdfkit
        pdf_bytes = pdfkit.from_string(html, False)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="{certificate.certificate_id}.html"'
        return response
