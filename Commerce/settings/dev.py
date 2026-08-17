from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',
    'http://localhost:8000',
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8000',
]

SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False
X_FRAME_OPTIONS = 'SAMEORIGIN'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
