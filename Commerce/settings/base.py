import os
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv
import pymysql
pymysql.install_as_MySQLdb()

load_dotenv()

import dj_database_url

# Project root is two levels up from Commerce/settings/base.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')

CANONICAL_DOMAIN = 'chuosmart.com'
# Canonical redirects are enabled explicitly by production settings. Do not
# infer this from DEBUG because Django's test runner temporarily forces DEBUG=False.
CANONICAL_REDIRECT_ENABLED = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
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
    # 'promotions',
    'jobs',
    'materials',
]

SITE_ID = 1
SITE_DOMAIN = 'chuosmart.com'

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": os.getenv('VAPID_PUBLIC_KEY'),
    "VAPID_PRIVATE_KEY": os.getenv('VAPID_PRIVATE_KEY'),
    "VAPID_ADMIN_EMAIL": os.getenv('VAPID_ADMIN_EMAIL')
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.canonicalization.CanonicalDomainMiddleware',
    'core.canonicalization.TrailingSlashMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware.SessionIdleTimeoutMiddleware',
]

ROOT_URLCONF = 'Commerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, 'templates'],
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

WSGI_APPLICATION = 'Commerce.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', default='localhost'),
        'PORT': os.getenv('DB_PORT', default='3306'),
    }
}

if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default']['OPTIONS'] = {
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1, NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
        'use_unicode': True,
    }
    DATABASES['default']['TEST'] = {
        'CHARSET': 'utf8mb4',
        'COLLATION': 'utf8mb4_unicode_ci',
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'Africa/Dar_es_Salaam')

CERTIFICATE_DOWNLOADS_ENABLED = True
CERTIFICATE_RELEASE_DATE = date(2026, 6, 24)
CERTIFICATE_ANNOUNCEMENT_START = datetime(2026, 6, 25, 0, 0, 0)

USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
PRIVATE_MEDIA_ROOT = os.getenv('PRIVATE_MEDIA_ROOT', str(BASE_DIR / 'private_media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

TINYMCE_LICENSE_KEY = os.getenv('TINYMCE_LICENSE_KEY', 'gpl')

TINYMCE_DEFAULT_CONFIG = {
    'height': 300,
    'license_key': TINYMCE_LICENSE_KEY,
    'plugins': 'advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen media table help wordcount',
    'toolbar_mode': 'floating',
    'menubar': False,
    'toolbar': 'undo redo | blocks | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | link image media table | code fullscreen',
    'image_advtab': False,
    'paste_data_images': True,
    'content_css': '/static/css/tinymce_custom.css',
    'images_upload_url': '/api/upload-tinymce-image/',
    'images_upload_credentials': True,
    'file_picker_types': 'image',
    'automatic_uploads': True,
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', str(60 * 60 * 24 * 14)))
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_IDLE_TIMEOUT = int(os.getenv('SESSION_IDLE_TIMEOUT', str(60 * 60 * 24 * 7)))

CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')
CEREBRAS_ASSESSMENT_MODEL = os.getenv('CEREBRAS_ASSESSMENT_MODEL', 'zai-glm-4.7')
CEREBRAS_ASSESSMENT_MAX_TOKENS = int(os.getenv('CEREBRAS_ASSESSMENT_MAX_TOKENS', '4000'))
CEREBRAS_CONTEXT_LIMIT = int(os.getenv('CEREBRAS_CONTEXT_LIMIT', '12000'))
CEREBRAS_STRICT_ASSESSMENTS = os.getenv('CEREBRAS_STRICT_ASSESSMENTS', 'True').lower() in ('1', 'true', 'yes')

if not CEREBRAS_API_KEY:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('CEREBRAS_API_KEY is not set; AI-generated assessments will use fallback behavior or remain unavailable.')

SNIPPE_API_KEY = os.getenv('SNIPPE_API_KEY', '')
SNIPPE_WEBHOOK_SECRET = os.getenv('SNIPPE_WEBHOOK_SECRET', '')
CERTIFICATE_SIGNING_SECRET = os.getenv('CERTIFICATE_SIGNING_SECRET', '')
CERTIFICATE_PRICE = 15000

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

LOGIN_URL = 'login'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'server311.web-hosting.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'support@chuosmart.com')
EMAIL_HOST_PASSWORD = os.getenv('SUPPORT_EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'true').lower() in ('1', 'true', 'yes')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'ChuoSmart <support@chuosmart.com>')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'support@chuosmart.com')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '30'))

os.makedirs(BASE_DIR / 'logs', exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'email_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'email.log',
            'maxBytes': 10_485_760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'lms_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'lms.log',
            'maxBytes': 10_485_760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core.email': {
            'handlers': ['email_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'lms': {
            'handlers': ['console', 'lms_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'lms.certificates': {
            'handlers': ['console', 'lms_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'lms.views': {
            'handlers': ['console', 'lms_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

NEWSLETTER_DEBUG = os.getenv('NEWSLETTER_DEBUG', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
NEWSLETTER_TEST_EMAIL = os.getenv('NEWSLETTER_TEST_EMAIL', '').strip()
NEWSLETTER_LOG_EMAIL = os.getenv('NEWSLETTER_LOG_EMAIL', 'manyerere201@gmail.com').strip()
MARKETING_EMAIL_MAX_PER_RUN = int(os.getenv('MARKETING_EMAIL_MAX_PER_RUN', '10'))
MARKETING_EMAIL_BURST_CAP = int(os.getenv('MARKETING_EMAIL_BURST_CAP', '3'))
MARKETING_EMAIL_TEN_MINUTE_CAP = int(os.getenv('MARKETING_EMAIL_TEN_MINUTE_CAP', '15'))
MARKETING_EMAIL_HOURLY_CAP = int(os.getenv('MARKETING_EMAIL_HOURLY_CAP', '100'))
MARKETING_EMAIL_DAILY_CAP = int(os.getenv('MARKETING_EMAIL_DAILY_CAP', '1500'))
MARKETING_EMAIL_SECONDS_BETWEEN_SENDS = float(os.getenv('MARKETING_EMAIL_SECONDS_BETWEEN_SENDS', '1'))
MARKETING_EMAIL_RETRY_BASE_MINUTES = int(os.getenv('MARKETING_EMAIL_RETRY_BASE_MINUTES', '10'))
MARKETING_EMAIL_STALE_MINUTES = int(os.getenv('MARKETING_EMAIL_STALE_MINUTES', '30'))
MARKETING_EMAIL_MAX_ATTEMPTS = int(os.getenv('MARKETING_EMAIL_MAX_ATTEMPTS', '5'))
MARKETING_SERIALIZE_CAMPAIGNS = os.getenv('MARKETING_SERIALIZE_CAMPAIGNS', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
MARKETING_FROM_EMAIL = os.getenv('MARKETING_FROM_EMAIL', DEFAULT_FROM_EMAIL).strip()
MARKETING_REPLY_TO = os.getenv('MARKETING_REPLY_TO', ADMIN_EMAIL).strip()
MARKETING_LIST_ID = os.getenv('MARKETING_LIST_ID', 'updates.chuosmart.com').strip()
MARKETING_BUSINESS_ADDRESS = os.getenv('MARKETING_BUSINESS_ADDRESS', 'ChuoSmart, Tanzania').strip()
CONTENT_MARKETING_CAMPAIGN_GAP_HOURS = int(os.getenv('CONTENT_MARKETING_CAMPAIGN_GAP_HOURS', '48'))
CONTENT_MARKETING_RECIPIENT_GAP_HOURS = int(os.getenv('CONTENT_MARKETING_RECIPIENT_GAP_HOURS', '48'))
CONTENT_MARKETING_RECONCILE_LIMIT = int(os.getenv('CONTENT_MARKETING_RECONCILE_LIMIT', '250'))
CONTENT_MARKETING_INCLUDE_COURSE_CONTENT = os.getenv('CONTENT_MARKETING_INCLUDE_COURSE_CONTENT', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}

PASSWORD_RESET_TIMEOUT = 86400

JOBS_MAINTENANCE_TOKEN = os.getenv('JOBS_MAINTENANCE_TOKEN', 'default_token_for_dev')

CSRF_FAILURE_VIEW = 'core.views.csrf_failure'
