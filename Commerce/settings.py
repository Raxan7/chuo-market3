import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql
pymysql.install_as_MySQLdb()

# Load environment variables from .env file
load_dotenv()

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Define the canonical domain (without www)
CANONICAL_DOMAIN = 'chuosmart.com'

ALLOWED_HOSTS = ['chuo-market3.onrender.com', 'localhost', '127.0.0.1', 'chuosmart.com', 'www.chuosmart.com']
# CSRF_TRUSTED_ORIGINS = ['https://chuo-market3.onrender.com', 'http://localhost:8000']
CSRF_TRUSTED_ORIGINS = [
    'https://chuo-market3.onrender.com',
    'http://localhost:8000',
    'https://www.chuosmart.com',
    'https://chuosmart.com'
]
# CSRF_COOKIE_SECURE = True
# CSRF_COOKIE_SAMESITE = 'None'
# CSRF_COOKIE_HTTPONLY = True
# CSRF_COOKIE_SECURE = True
# CSRF_COOKIE_SAMESITE = 'None'
# CSRF_COOKIE_HTTPONLY = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',  # Cloudinary storage backend
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # Add sitemap functionality
    'django.contrib.sites',     # Required for sitemaps
    'cloudinary',  # Cloudinary integration
    'tinymce',
    'markdown_deux',
    'widget_tweaks',
    'webpush',  # For push notifications
    'rest_framework',  # For the API
    
    'core',
    'talents',
    'chatbotapp',
    'lms',
    'landing',
    'affiliates',
    # 'promotions',
    'jobs',  # Our new job portal app
]

# Site ID and domain for the sites framework
SITE_ID = 1
SITE_DOMAIN = 'chuosmart.com'

# filepath: /home/saidi/Projects/KOMBA/chuo-market3/Commerce/settings.py
# Web Push Notification Settings
WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": os.getenv('VAPID_PUBLIC_KEY'),
    "VAPID_PRIVATE_KEY": os.getenv('VAPID_PRIVATE_KEY'),
    "VAPID_ADMIN_EMAIL": os.getenv('VAPID_ADMIN_EMAIL')
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # Ensure this is included
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.canonicalization.CanonicalDomainMiddleware',  # URL canonicalization
    'core.canonicalization.TrailingSlashMiddleware',    # Ensure trailing slashes
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SessionIdleTimeoutMiddleware',  # Custom middleware for session idle timeout
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
                'core.context_processors.auth_status',  # Authentication status
                'core.seo_context.seo_context',  # SEO context data
                'core.context_processors.dashboard_notification',  # Dashboard notification
            ],
        },
    },
]

WSGI_APPLICATION = 'Commerce.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# DATABASES = {
#     'default': dj_database_url.parse("postgresql://manyerere201:exHjyP9UQFX0@ep-shy-mud-a5gs0r74.us-east-2.aws.neon."
#                                      "tech/chuo-market3?sslmode=require")
# }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'chuosmart_db',
#         'USER': 'komba',
#         'PASSWORD': 'komba123',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Production MySQL Database Configuration (Fixed for emoji support)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),  # Database name from .env
        'USER': os.getenv('DB_USER'),  # Database username from .env
        'PASSWORD': os.getenv('DB_PASSWORD'),  # Database password from .env
        'HOST': os.getenv('DB_HOST', default='localhost'),  # Database host from .env
        'PORT': os.getenv('DB_PORT', default='3306'),  # Database port from .env
        'OPTIONS': {
            'charset': 'utf8mb4',  # Use utf8mb4 for full UTF-8 support including emojis
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1, NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
            'use_unicode': True,
        },
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

TINYMCE_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/tinymce/5.10.7/tinymce.min.js'
TINYMCE_JS_ROOT = 'https://cdnjs.cloudflare.com/ajax/libs/tinymce/5.10.7/'

TINYMCE_DEFAULT_CONFIG = {
    'height': 300,
    'plugins': 'advlist autolink lists link image charmap print preview hr anchor pagebreak',
    'toolbar_mode': 'floating',
    'menubar': False,
    'toolbar': 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | link image',
    'image_advtab': False,
    'paste_data_images': True,
    'content_css': '/static/css/tinymce_custom.css',
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database-backed sessions

# Session configuration
SESSION_COOKIE_AGE = 31536000  # 1 year in seconds - effectively "forever" in web terms
SESSION_SAVE_EVERY_REQUEST = True  # Update the session on every request, resetting the expiry time
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Don't expire when browser closes
SESSION_COOKIE_SECURE = not DEBUG  # Use secure cookies in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing the session cookie
SESSION_IDLE_TIMEOUT = 31536000  # 1 year in seconds - effectively disabled

# Cerebras AI configuration
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')

# Only raise error if not in test mode or check command
import sys
if not CEREBRAS_API_KEY and 'test' not in sys.argv and 'check' not in sys.argv:
    raise ValueError('CEREBRAS_API_KEY environment variable not set')

# Authentication
LOGIN_URL = 'login'  # Use the name of the login URL pattern, not the URL path

# Email backend configuration for user verification
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'chuosmart.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'support@chuosmart.com'
EMAIL_HOST_PASSWORD = os.getenv('SUPPORT_EMAIL_HOST_PASSWORD')  # Set this in your .env file
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'ChuoSmart <support@chuosmart.com>'

# Password reset settings
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours in seconds

# Cloudinary Configuration
import cloudinary

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Use Cloudinary for media storage
if os.getenv('CLOUDINARY_CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = '/media/'
else:
    # Fallback to local storage if Cloudinary not configured
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

JOBS_MAINTENANCE_TOKEN = os.getenv('JOBS_MAINTENANCE_TOKEN', 'default_token_for_dev')