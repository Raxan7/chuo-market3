from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Material


class MaterialModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_material_creation(self):
        material = Material.objects.create(
            title='VS Code',
            description='A code editor',
            software_url='https://code.visualstudio.com',
            category='developer_tools',
            created_by=self.user,
        )
        self.assertEqual(Material.objects.count(), 1)
        self.assertEqual(str(material), 'VS Code')
        self.assertEqual(material.get_absolute_url(), reverse('materials:detail', kwargs={'pk': material.pk}))
        self.assertEqual(material.get_edit_url(), reverse('materials:update', kwargs={'pk': material.pk}))
        self.assertEqual(material.get_delete_url(), reverse('materials:delete', kwargs={'pk': material.pk}))

    def test_default_category(self):
        material = Material.objects.create(
            title='Generic tool',
            software_url='https://example.com',
            created_by=self.user,
        )
        self.assertEqual(material.category, 'other')


class MaterialViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpassword'
        )
        self.material = Material.objects.create(
            title='VS Code',
            description='A code editor',
            software_url='https://code.visualstudio.com',
            category='developer_tools',
            created_by=self.user,
        )
        self.inactive_material = Material.objects.create(
            title='Hidden Tool',
            software_url='https://example.com',
            created_by=self.user,
            is_active=False,
        )
        self.client = Client()

    def test_material_list_view(self):
        response = self.client.get(reverse('materials:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'materials/material_list.html')
        self.assertContains(response, 'VS Code')
        self.assertNotContains(response, 'Hidden Tool')

    def test_material_detail_view(self):
        response = self.client.get(reverse('materials:detail', kwargs={'pk': self.material.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VS Code')

    def test_inactive_material_detail_returns_404(self):
        response = self.client.get(reverse('materials:detail', kwargs={'pk': self.inactive_material.pk}))
        self.assertEqual(response.status_code, 404)

    def test_create_view_requires_login(self):
        response = self.client.get(reverse('materials:create'))
        self.assertNotEqual(response.status_code, 200)

    def test_create_view_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('materials:create'), {
            'title': 'New Material',
            'description': 'A new material',
            'software_url': 'https://example.com/new-tool',
            'category': 'education',
        })
        self.assertEqual(response.status_code, 302)
        material = Material.objects.get(title='New Material')
        self.assertEqual(material.created_by, self.user)

    def test_create_view_rejects_invalid_url(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('materials:create'), {
            'title': 'Bad URL',
            'description': '',
            'software_url': 'not-a-url',
            'category': 'other',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Material.objects.filter(title='Bad URL').count(), 0)

    def test_update_view_owner_only(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(
            reverse('materials:update', kwargs={'pk': self.material.pk}),
            {
                'title': 'VS Code Updated',
                'description': 'A code editor',
                'software_url': 'https://code.visualstudio.com',
                'category': 'developer_tools',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, 'VS Code Updated')

    def test_update_view_non_owner_forbidden(self):
        self.client.login(username='otheruser', password='testpassword')
        response = self.client.get(reverse('materials:update', kwargs={'pk': self.material.pk}))
        self.assertEqual(response.status_code, 403)

    def test_delete_view_owner_only(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('materials:delete', kwargs={'pk': self.material.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Material.objects.filter(pk=self.material.pk).count(), 0)

    def test_delete_view_non_owner_forbidden(self):
        self.client.login(username='otheruser', password='testpassword')
        response = self.client.post(reverse('materials:delete', kwargs={'pk': self.material.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Material.objects.filter(pk=self.material.pk).count(), 1)


class MaterialSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.material = Material.objects.create(
            title='Anaconda',
            description='Python data science platform',
            software_url='https://www.anaconda.com',
            category='developer_tools',
            created_by=self.user,
        )
        self.client = Client()

    def test_global_search_finds_materials(self):
        response = self.client.get(reverse('search'), {'q': 'Anaconda'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anaconda')
        self.assertContains(response, 'Materials')
