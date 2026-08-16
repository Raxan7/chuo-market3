from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class CorePageSmokeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/home.html')

    def test_search_page_loads(self):
        response = self.client.get(reverse('search'), {'q': 'django'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/global_search.html')

    def test_dashboard_loads_for_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('user_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/dashboard.html')

    def test_dashboard_shows_materials_tab(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('user_dashboard'))
        self.assertContains(response, 'My Materials')
