"""Regression checks for reusable sharing; no external network calls."""
from urllib.parse import parse_qs, urlsplit

from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from core.templatetags.share_tags import share_buttons


class SocialSharingTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get('/products/example/?secret=do-not-share')
        self.context = {'request': self.request, 'base_url': 'https://chuosmart.com'}

    def test_share_targets_are_public_absolute_paths_without_query_secrets(self):
        data = share_buttons(self.context, 'A&B #1', '/products/example/?token=private#part')
        url = 'https://chuosmart.com/products/example/'
        self.assertEqual(data['share_url'], url)
        self.assertEqual(parse_qs(urlsplit(data['share_facebook']).query)['u'], [url])
        self.assertEqual(parse_qs(urlsplit(data['share_x']).query), {'text': ['A&B #1'], 'url': [url]})
        self.assertEqual(parse_qs(urlsplit(data['share_whatsapp']).query)['text'], [f'A&B #1 {url}'])
        self.assertEqual(parse_qs(urlsplit(data['share_linkedin']).query)['url'], [url])
        self.assertEqual(parse_qs(urlsplit(data['share_email']).query)['subject'], ['A&B #1'])
        self.assertNotIn('private', str(data))

    def test_external_paths_cannot_redirect_shared_destination(self):
        for candidate in ('https://example.org/pay', '//example.org/pay', 'javascript:alert(1)'):
            with self.subTest(candidate=candidate):
                data = share_buttons(self.context, 'Test', candidate)
                self.assertEqual(data['share_url'], 'https://chuosmart.com/products/example/')

    def test_inclusion_tag_renders_accessible_buttons_and_escapes_title(self):
        markup = Template(
            '{% load share_tags %}'
            '{% share_buttons title public_path compact=True %}'
        ).render(Context({**self.context, 'title': 'One <script>alert(1)</script>', 'public_path': '/courses/first/'}))
        self.assertIn('https://chuosmart.com/courses/first/', markup)
        self.assertNotIn('<script>', markup)
        for action in ('WhatsApp', 'Facebook', 'X', 'LinkedIn', 'Copy share link', 'Share by email'):
            self.assertIn(action, markup)

    def test_public_routes_exist(self):
        self.assertTrue(reverse('lms:course_detail', kwargs={'slug': 'sample'}).endswith('/courses/sample/'))
        self.assertTrue(reverse('product-detail', kwargs={'slug': 'sample'}).endswith('/product/sample/'))
        self.assertTrue(reverse('blog_detail', kwargs={'slug': 'sample'}).endswith('/blogs/sample/'))
