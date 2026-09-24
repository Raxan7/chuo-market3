from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.middleware import SecurityHeadersMiddleware


class SecurityHeadersMiddlewareTests(SimpleTestCase):
    @override_settings(DEBUG=False, CANONICAL_DOMAIN='chuosmart.com')
    def test_form_action_allows_canonical_payment_origin_from_www_alias(self):
        request = RequestFactory().get(
            '/lms/courses/example/payment/',
            HTTP_HOST='www.chuosmart.com',
            secure=True,
        )
        response = SecurityHeadersMiddleware(lambda _request: HttpResponse('ok'))(request)

        csp = response['Content-Security-Policy']
        form_action = next(
            part.strip()
            for part in csp.split(';')
            if part.strip().startswith('form-action ')
        )
        self.assertEqual(
            form_action,
            "form-action 'self' https://chuosmart.com",
        )

    @override_settings(DEBUG=False, CANONICAL_DOMAIN='*')
    def test_form_action_does_not_add_wildcard_canonical_domain(self):
        request = RequestFactory().get('/', HTTP_HOST='example.test', secure=True)
        response = SecurityHeadersMiddleware(lambda _request: HttpResponse('ok'))(request)

        csp = response['Content-Security-Policy']
        form_action = next(
            part.strip()
            for part in csp.split(';')
            if part.strip().startswith('form-action ')
        )
        self.assertEqual(form_action, "form-action 'self'")
