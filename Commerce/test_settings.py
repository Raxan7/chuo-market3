"""Portable settings for ChuoSmart automated tests.

This module deliberately avoids developer-machine absolute paths and external
services so the test suite can run consistently in CI or a clean checkout.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'test-secret-key-for-testing-only'
DEBUG = False
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'tinymce',
    'markdown_deux',
    'widget_tweaks',
    'webpush',
    'rest_framework',
    'core',
    'lms',
    'landing',
    'affiliates',
    'jobs',
    'materials',
]

SITE_ID = 1
SITE_DOMAIN = 'testserver'
ROOT_URLCONF = 'Commerce.urls'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.auth_status',
                'core.seo_context.seo_context',
                'core.context_processors.dashboard_notification',
                'core.context_processors.site_ad_settings',
                'core.context_processors.certificate_notice',
                'core.context_processors.certificate_available_announcement',
            ],
        },
    },
]

USE_TZ = True
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / '.test-staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / '.test-media'
PRIVATE_MEDIA_ROOT = BASE_DIR / '.test-private-media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

CEREBRAS_API_KEY = None
CEREBRAS_STRICT_ASSESSMENTS = False
SNIPPE_API_KEY = ''
SNIPPE_WEBHOOK_SECRET = ''
CERTIFICATE_DOWNLOADS_ENABLED = True
CERTIFICATE_RELEASE_DATE = None
CERTIFICATE_ANNOUNCEMENT_START = None
CERTIFICATE_PRICE = 15000
CERTIFICATE_SIGNING_SECRET = 'test-secret'

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'ChuoSmart <support@chuosmart.test>'
ADMIN_EMAIL = 'support@chuosmart.test'
MARKETING_EMAIL_BACKEND = EMAIL_BACKEND
MARKETING_EMAIL_MAX_PER_RUN = 10
MARKETING_EMAIL_BURST_CAP = 3
MARKETING_EMAIL_TEN_MINUTE_CAP = 15
MARKETING_EMAIL_HOURLY_CAP = 100
MARKETING_EMAIL_DAILY_CAP = 1500
MARKETING_EMAIL_SECONDS_BETWEEN_SENDS = 0
MARKETING_EMAIL_RETRY_BASE_MINUTES = 1
MARKETING_EMAIL_STALE_MINUTES = 30
MARKETING_EMAIL_MAX_ATTEMPTS = 5
MARKETING_SERIALIZE_CAMPAIGNS = True
MARKETING_FROM_EMAIL = DEFAULT_FROM_EMAIL
MARKETING_REPLY_TO = ADMIN_EMAIL
MARKETING_LIST_ID = 'updates.chuosmart.test'
MARKETING_BUSINESS_ADDRESS = 'ChuoSmart, Tanzania'
MARKETING_EMAIL_POLICY_RETRY_MINUTES = 60
MARKETING_EMAIL_POLICY_FAILURE_CIRCUIT_BREAKER = 3
CONTENT_MARKETING_CAMPAIGN_GAP_HOURS = 24
CONTENT_MARKETING_RECIPIENT_GAP_HOURS = 48
CONTENT_MARKETING_RECONCILE_LIMIT = 250
CONTENT_MARKETING_DIGEST_SIZE = 12
CONTENT_MARKETING_INCLUDE_COURSE_CONTENT = False

CANONICAL_DOMAIN = 'testserver'
CANONICAL_REDIRECT_ENABLED = False
LOGIN_URL = 'login'

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
