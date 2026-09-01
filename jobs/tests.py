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
