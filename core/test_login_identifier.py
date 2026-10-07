from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class UsernameOrEmailLoginTests(TestCase):
    password = 'SafePassword123!'

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='erick.creator',
            email='Creator@Example.com',
            password=self.password,
        )

    def _post_login(self, identifier, password=None):
        return self.client.post(
            reverse('login'),
            {'username': identifier, 'password': password or self.password},
        )

    def _assert_logged_in_as(self, user):
        self.assertEqual(
            self.client.session.get('_auth_user_id'),
            str(user.pk),
        )

    def test_username_login_still_works(self):
        self._post_login('erick.creator')
        self._assert_logged_in_as(self.user)

    def test_email_login_works_case_insensitively(self):
        self._post_login('creator@example.COM')
        self._assert_logged_in_as(self.user)

    def test_email_login_trims_surrounding_whitespace(self):
        self._post_login('  Creator@Example.com  ')
        self._assert_logged_in_as(self.user)

    def test_wrong_password_does_not_authenticate_by_email(self):
        response = self._post_login('Creator@Example.com', 'wrong-password')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Invalid username/email or password.', status_code=200)

    def test_duplicate_legacy_email_is_rejected_instead_of_guessing(self):
        User = get_user_model()
        User.objects.create_user(
            username='other.creator',
            email='creator@example.com',
            password=self.password,
        )

        response = self._post_login('creator@example.com')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Invalid username/email or password.', status_code=200)

    def test_username_takes_precedence_if_it_looks_like_an_email(self):
        User = get_user_model()
        email_like_username = User.objects.create_user(
            username='alias@example.com',
            email='different@example.com',
            password=self.password,
        )
        User.objects.create_user(
            username='another-user',
            email='alias@example.com',
            password='DifferentPassword123!',
        )

        self._post_login('alias@example.com')
        self._assert_logged_in_as(email_like_username)
