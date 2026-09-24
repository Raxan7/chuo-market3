import sys
import types
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .admin import CourseEnrollmentAdmin
from .models import CertificateTemplate, Course, CourseEnrollment, StudentCertificate


class _FakeHTML:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def write_pdf(self):
        return b'%PDF-1.4\nchuosmart-test\n'


class AdminCertificateAndCompletionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-controls',
            password='testpassword',
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username='student-controls',
            password='testpassword',
        )
        self.course = Course.objects.create(
            title='Admin Controls Course',
            summary='Course used to verify administrative certificate controls.',
        )
        self.template = CertificateTemplate.objects.create(
            course=self.course,
            title='Admin Controls Certificate',
            status='active',
        )
        self.certificate = StudentCertificate.objects.create(
            student=self.student,
            course=self.course,
            template=self.template,
        )
        self.enrollment = CourseEnrollment.objects.create(
            student=self.student.lms_profile,
            course=self.course,
        )

    def test_admin_certificate_download_is_available_and_returns_pdf(self):
        self.client.force_login(self.admin)
        url = reverse(
            'lms:admin_download_certificate',
            args=[self.certificate.certificate_id],
        )
        fake_weasyprint = types.SimpleNamespace(HTML=_FakeHTML)
        with patch.dict(sys.modules, {'weasyprint': fake_weasyprint}), patch(
            'django.template.loader.render_to_string',
            return_value='<html><body>certificate</body></html>',
        ):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(self.certificate.certificate_id, response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-1.4'))

    def test_non_admin_cannot_use_admin_certificate_download(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse(
                'lms:admin_download_certificate',
                args=[self.certificate.certificate_id],
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('lms:student_dashboard'))

    def test_staff_admin_can_override_course_completion(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                'lms:override_course_completion',
                args=[self.course.slug, self.student.lms_profile.id],
            )
        )
        self.assertEqual(response.status_code, 302)

        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.admin_override_completion)
        self.assertEqual(self.enrollment.granted_by, self.admin)

    def test_non_admin_override_is_denied_without_server_error(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse(
                'lms:override_course_completion',
                args=[self.course.slug, self.student.lms_profile.id],
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('lms:course_detail', kwargs={'slug': self.course.slug}),
        )

        self.enrollment.refresh_from_db()
        self.assertFalse(self.enrollment.admin_override_completion)

    def test_override_course_completion_is_registered_as_admin_action(self):
        self.assertIn('override_course_completion', CourseEnrollmentAdmin.actions)
