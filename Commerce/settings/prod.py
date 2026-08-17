from .base import *

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
