from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class CreatorFormStudioUiTests(TestCase):
    password = 'password12345'

    def _make_user(self, username, *, role='student'):
        user = User.objects.create_user(username=username, password=self.password)
        user.lms_profile.role = role
        user.lms_profile.save(update_fields=['role'])
        return user

    def test_job_create_uses_creator_studio_without_dropping_form_fields(self):
        user = self._make_user('job-studio-user')
        self.client.force_login(user)

        response = self.client.get(reverse('jobs:create_job'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-creator-page="job"')
        self.assertContains(response, 'chuosmart_v2/css/creator_forms.css')
        expected_fields = {
            'title', 'description', 'company', 'industry', 'location', 'is_remote',
            'salary_min', 'salary_max', 'salary_currency', 'job_type',
            'experience_level', 'requirements', 'responsibilities', 'benefits',
            'application_deadline', 'is_active', 'skills', 'job_posting_type',
            'external_url',
        }
        self.assertTrue(expected_fields.issubset(response.context['form'].fields))

    def test_course_create_uses_creator_studio_without_dropping_form_fields(self):
        user = self._make_user('course-studio-user', role='instructor')
        self.client.force_login(user)

        response = self.client.get(reverse('lms:course_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-creator-page="course"')
        self.assertContains(response, 'chuosmart_v2/css/creator_forms.css')
        expected_fields = {
            'title', 'course_type', 'code', 'credit', 'summary', 'content',
            'program', 'level', 'year', 'semester', 'is_elective', 'is_free',
            'price', 'instructors', 'image',
        }
        self.assertTrue(expected_fields.issubset(response.context['form'].fields))

    def test_external_job_validation_keeps_external_controls_in_studio(self):
        user = self._make_user('job-studio-validation')
        self.client.force_login(user)

        response = self.client.get(reverse('jobs:create_job'))

        self.assertContains(response, 'id="job_posting_external"')
        self.assertContains(response, 'id="external-url-section"')
        self.assertContains(response, 'data-application-choices')

    def test_course_studio_includes_program_creation_modal(self):
        user = self._make_user('course-studio-program', role='instructor')
        self.client.force_login(user)

        response = self.client.get(reverse('lms:course_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="createProgramModal"')
        self.assertContains(response, 'name="create_program"')
