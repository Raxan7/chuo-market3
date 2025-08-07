from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Job, Company, JobCategory

class JobsViewsTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test company
        self.company = Company.objects.create(
            name='Test Company',
            location='Dar es Salaam',
            website='https://example.com',
            description='Test company description',
            user=self.user
        )
        
        # Create a test category
        self.category = JobCategory.objects.create(
            name='Technology',
            slug='technology'
        )
        
        # Create a test job
        self.job = Job.objects.create(
            title='Software Developer',
            company=self.company,
            location='Dar es Salaam',
            description='Test job description',
            job_type='full_time',
            source='internal'
        )
        self.job.categories.add(self.category)
        
        # Initialize client
        self.client = Client()
    
    def test_job_list_view(self):
        """Test job listing page loads correctly"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'jobs/job_list.html')
        self.assertContains(response, 'Software Developer')
        
    def test_job_detail_view(self):
        """Test job detail page loads correctly"""
        response = self.client.get(reverse('jobs:job_detail', args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'jobs/job_detail.html')
        self.assertContains(response, 'Software Developer')
        self.assertContains(response, 'Test Company')
        
    def test_job_search(self):
        """Test job search functionality"""
        response = self.client.get(f"{reverse('jobs:job_list')}?keywords=software")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Developer')
        
        # Test search with no results
        response = self.client.get(f"{reverse('jobs:job_list')}?keywords=nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Software Developer')
        
    def test_category_filter(self):
        """Test filtering jobs by category"""
        response = self.client.get(reverse('jobs:category', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Developer')
        
    def test_authenticated_user_views(self):
        """Test views that require authentication"""
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Test saved jobs page
        response = self.client.get(reverse('jobs:saved_jobs'))
        self.assertEqual(response.status_code, 200)
        
        # Test my applications page
        response = self.client.get(reverse('jobs:my_applications'))
        self.assertEqual(response.status_code, 200)
        
        # Test job preferences page
        response = self.client.get(reverse('jobs:job_preferences'))
        self.assertEqual(response.status_code, 200)
