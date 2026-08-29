from .base import *
from django.core.exceptions import ImproperlyConfigured
import os

DEBUG = False

ALLOWED_HOSTS = [
    'chuosmart.com',
    'www.chuosmart.com',
    'mail.chuosmart.com',
    '6aa8-154-74-175-23.ngrok-free.app',
]

CSRF_TRUSTED_ORIGINS = [
    'https://www.chuosmart.com',
    'https://chuosmart.com',
    'https://6aa8-154-74-175-23.ngrok-free.app',
]

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

required_environment = {
    'SECRET_KEY': SECRET_KEY,
    'DB_NAME': os.getenv('DB_NAME'),
    'DB_USER': os.getenv('DB_USER'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD'),
    'SUPPORT_EMAIL_HOST_PASSWORD': EMAIL_HOST_PASSWORD,
    'SNIPPE_API_KEY': SNIPPE_API_KEY,
    'SNIPPE_WEBHOOK_SECRET': SNIPPE_WEBHOOK_SECRET,
}
missing = [name for name, value in required_environment.items() if not value]
if missing:
    raise ImproperlyConfigured(
        'Missing required production environment variables: ' + ', '.join(missing)
    )

if EMAIL_USE_SSL and EMAIL_USE_TLS:
    raise ImproperlyConfigured('EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be enabled.')
