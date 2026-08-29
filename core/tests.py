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


class SecurityRegressionTests(TestCase):
    def setUp(self):
        from core.models import Product

        self.user = User.objects.create_user(
            username='buyer', email='buyer@example.com', password='password12345'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='password12345'
        )
        self.product = Product.objects.create(
            user=self.other,
            title='Test product',
            category='El',
            description='Test',
            price=1000,
            image='product_images/test.jpg',
        )
        self.client.login(username='buyer', password='password12345')

    def test_newsletter_is_opt_in_by_default(self):
        self.assertFalse(self.user.newsletter_preference.newsletter)

    def test_add_to_cart_rejects_get(self):
        response = self.client.get(reverse('add-to-cart'), {'product_id': self.product.pk})
        self.assertEqual(response.status_code, 405)

    def test_order_cannot_use_another_users_customer_profile(self):
        response = self.client.post(reverse('order_placed'), {
            'customer_id': self.other.customer.pk,
            'product_id': self.product.pk,
            'quantity': 1,
        })
        self.assertEqual(response.status_code, 404)

    def test_non_staff_cannot_target_another_user_notification(self):
        response = self.client.post(
            reverse('send_notification_to_user', kwargs={'user_id': self.other.pk}),
            {'head': 'Nope', 'body': 'Nope'},
        )
        self.assertEqual(response.status_code, 403)
