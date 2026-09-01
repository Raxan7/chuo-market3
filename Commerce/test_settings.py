import os
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
        'DIRS': ['/home/saidi/Projects/chuo-market3', '/home/saidi/Projects/chuo-market3/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

USE_TZ = True
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
STATIC_URL = '/static/'
STATIC_ROOT = '/tmp/static_test/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CEREBRAS_API_KEY = None
CEREBRAS_STRICT_ASSESSMENTS = False
SNIPPE_API_KEY = ''
SNIPPE_WEBHOOK_SECRET = ''
CERTIFICATE_DOWNLOADS_ENABLED = True
CERTIFICATE_PRICE = 15000
CERTIFICATE_SIGNING_SECRET = 'test-secret'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CANONICAL_DOMAIN = 'testserver'

CANONICAL_REDIRECT_ENABLED = False
