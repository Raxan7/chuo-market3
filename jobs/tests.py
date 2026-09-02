from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Company, CompanyVerificationRequest, Job, JobApplication, UserJobApproval


class JobsRegressionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='employer', email='employer@example.com', password='password12345'
        )
        self.applicant = User.objects.create_user(
            username='student', email='student@example.com', password='password12345'
        )
        self.company = Company.objects.create(
            name='Test Company',
            city='Dar es Salaam',
            country='Tanzania',
            email='jobs@example.com',
            website='https://example.com',
            description='Test company description',
            created_by=self.owner,
            is_verified=True,
        )
        UserJobApproval.objects.update_or_create(
            user=self.owner,
            defaults={
                'is_approved': True,
                'approved_by': self.owner,
                'approved_date': timezone.now(),
            },
        )
        self.job = Job.objects.create(
            title='Software Developer',
            company=self.company,
            location='Dar es Salaam',
            description='Build useful software.',
            requirements='Python and Django',
            responsibilities='Ship product improvements',
            benefits='Learning budget',
            job_type='full_time',
            experience_level='entry',
            application_deadline=timezone.now() + timedelta(days=14),
            created_by=self.owner,
            source='internal',
            job_posting_type='internal',
        )

    def test_public_job_is_listed(self):
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.title)

    def test_company_dashboard_uses_real_job_and_application_fields(self):
        JobApplication.objects.create(
            job=self.job,
            applicant=self.applicant,
            cover_letter='I am interested.',
            resume='jobs/resumes/test.pdf',
        )
        self.client.login(username='employer', password='password12345')
        response = self.client.get(reverse('jobs:company_dashboard', args=[self.company.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Developer')
        self.assertContains(response, 'student')

    def test_hidden_job_cannot_be_applied_to_by_direct_url(self):
        approval = self.owner.job_approval
        approval.is_approved = False
        approval.save(update_fields=['is_approved'])
        self.client.login(username='student', password='password12345')
        response = self.client.get(reverse('jobs:apply_for_job', args=[self.job.id]))
        self.assertEqual(response.status_code, 404)

    def test_external_job_requires_application_url(self):
        self.client.login(username='employer', password='password12345')
        response = self.client.post(reverse('jobs:create_job'), {
            'title': 'External role',
            'description': 'External role description',
            'company': self.company.id,
            'location': 'Arusha',
            'salary_currency': 'TZS',
            'job_type': 'full_time',
            'experience_level': 'entry',
            'requirements': 'Requirements',
            'responsibilities': 'Responsibilities',
            'benefits': '',
            'application_deadline': (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': 'on',
            'job_posting_type': 'external',
            'external_url': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'External application URL is required')
        self.assertFalse(Job.objects.filter(title='External role').exists())

    def test_job_form_does_not_allow_self_service_featured_flag(self):
        self.client.login(username='employer', password='password12345')
        response = self.client.post(reverse('jobs:create_job'), {
            'title': 'Normal role',
            'description': 'Role description',
            'company': self.company.id,
            'location': 'Dodoma',
            'salary_currency': 'TZS',
            'job_type': 'full_time',
            'experience_level': 'entry',
            'requirements': 'Requirements',
            'responsibilities': 'Responsibilities',
            'benefits': '',
            'application_deadline': (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': 'on',
            'job_posting_type': 'internal',
            'external_url': '',
            'is_featured': 'on',
        })
        self.assertEqual(response.status_code, 302)
        created = Job.objects.get(title='Normal role')
        self.assertFalse(created.is_featured)

    def test_verification_request_is_persisted(self):
        self.company.is_verified = False
        self.company.save(update_fields=['is_verified'])
        self.client.login(username='employer', password='password12345')
        certificate = SimpleUploadedFile('registration.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.post(
            reverse('jobs:request_verification', args=[self.company.id]),
            {'business_certificate': certificate, 'verification_notes': 'Please verify us.'},
        )
        self.assertEqual(response.status_code, 302)
        verification = CompanyVerificationRequest.objects.get(company=self.company)
        self.assertEqual(verification.requested_by, self.owner)
        self.assertEqual(verification.status, 'pending')

    def test_company_detail_route_exists(self):
        response = self.client.get(reverse('jobs:company_detail', args=[self.company.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company.name)


class JobPostingReliabilityTests(TestCase):
    """Production-oriented tests for the employer job creation path."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='reliable-employer', email='reliable@example.com', password='password12345'
        )
        self.company = Company.objects.create(
            name='Reliable Company',
            description='A verified employer.',
            city='Dar es Salaam',
            country='Tanzania',
            created_by=self.owner,
            is_verified=True,
        )
        UserJobApproval.objects.update_or_create(
            user=self.owner,
            defaults={
                'is_approved': True,
                'approved_by': self.owner,
                'approved_date': timezone.now(),
            },
        )
        self.client.login(username='reliable-employer', password='password12345')

    def payload(self, **overrides):
        data = {
            'title': 'Production Safe Role',
            'description': 'A real role posted through the employer form.',
            'company': self.company.id,
            'location': 'Dar es Salaam',
            'salary_currency': 'TZS',
            'job_type': 'full_time',
            'experience_level': 'entry',
            'requirements': 'Reliable requirements',
            'responsibilities': 'Reliable responsibilities',
            'benefits': '',
            'application_deadline': (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': 'on',
            'job_posting_type': 'internal',
            'external_url': '',
        }
        data.update(overrides)
        return data

    def test_valid_job_post_redirects_and_persists(self):
        response = self.client.post(reverse('jobs:create_job'), self.payload())
        self.assertEqual(response.status_code, 302)
        job = Job.objects.get(title='Production Safe Role')
        self.assertEqual(job.created_by, self.owner)
        self.assertEqual(job.company, self.company)
        self.assertTrue(job.is_public)

    def test_cached_form_without_currency_uses_safe_default(self):
        payload = self.payload(title='Cached Currency Role')
        payload.pop('salary_currency')
        response = self.client.post(reverse('jobs:create_job'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Job.objects.get(title='Cached Currency Role').salary_currency, 'TZS')

    def test_cached_form_without_posting_type_uses_internal_default(self):
        payload = self.payload(title='Cached Posting Type Role')
        payload.pop('job_posting_type')
        response = self.client.post(reverse('jobs:create_job'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Job.objects.get(title='Cached Posting Type Role').job_posting_type, 'internal')

    def test_external_validation_keeps_external_choice_visible(self):
        response = self.client.post(
            reverse('jobs:create_job'),
            self.payload(title='External Validation Role', job_posting_type='external', external_url=''),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'External application URL is required')
        self.assertContains(response, 'Please fix the following')
        self.assertEqual(response.context['form']['job_posting_type'].value(), 'external')
        self.assertFalse(Job.objects.filter(title='External Validation Role').exists())

    def test_unapproved_employer_can_save_job_without_public_visibility(self):
        approval = self.owner.job_approval
        approval.is_approved = False
        approval.save(update_fields=['is_approved'])
        response = self.client.post(reverse('jobs:create_job'), self.payload(title='Pending Verification Role'))
        self.assertEqual(response.status_code, 302)
        job = Job.objects.get(title='Pending Verification Role')
        self.assertFalse(job.is_public)

    def test_announcement_queue_failure_does_not_break_job_creation(self):
        from unittest.mock import patch

        with patch('jobs.signals.send_job_newsletter', side_effect=RuntimeError('queue unavailable')):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse('jobs:create_job'),
                    self.payload(title='Queue Independent Role'),
                )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Job.objects.filter(title='Queue Independent Role').exists())

    def test_database_save_exception_returns_form_instead_of_http_500(self):
        from unittest.mock import patch

        with patch('jobs.views.Job.save', side_effect=RuntimeError('simulated database write failure')):
            response = self.client.post(
                reverse('jobs:create_job'),
                self.payload(title='Graceful Failure Role'),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'We could not save this job right now')
        self.assertFalse(Job.objects.filter(title='Graceful Failure Role').exists())


    def test_external_job_with_valid_url_posts_successfully(self):
        response = self.client.post(
            reverse('jobs:create_job'),
            self.payload(
                title='External Success Role',
                job_posting_type='external',
                external_url='https://example.com/careers/role-1',
            ),
        )
        self.assertEqual(response.status_code, 302)
        job = Job.objects.get(title='External Success Role')
        self.assertEqual(job.job_posting_type, 'external')
        self.assertEqual(job.external_url, 'https://example.com/careers/role-1')

    def test_approved_employer_can_post_without_company(self):
        response = self.client.post(
            reverse('jobs:create_job'),
            self.payload(title='Independent Employer Role', company=''),
        )
        self.assertEqual(response.status_code, 302)
        job = Job.objects.get(title='Independent Employer Role')
        self.assertIsNone(job.company)
        self.assertTrue(job.is_public)

    def test_employer_cannot_post_for_another_users_company(self):
        other = User.objects.create_user(username='other-employer', password='password12345')
        other_company = Company.objects.create(
            name='Other Company',
            description='Not owned by the current employer.',
            city='Arusha',
            country='Tanzania',
            created_by=other,
            is_verified=True,
        )
        response = self.client.post(
            reverse('jobs:create_job'),
            self.payload(title='Unauthorized Company Role', company=other_company.id),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid choice')
        self.assertFalse(Job.objects.filter(title='Unauthorized Company Role').exists())
