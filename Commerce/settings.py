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
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # Add sitemap functionality
    'django.contrib.sites',     # Required for sitemaps
    'tinymce',
    'markdown_deux',
    'widget_tweaks',
    'webpush',  # For push notifications

    'core',
    'talents',
    'chatbotapp',
    'lms',
]

# Site ID for the sites framework
SITE_ID = 1

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),  # Database name from .env
        'USER': os.getenv('DB_USER'),  # Database username from .env
        'PASSWORD': os.getenv('DB_PASSWORD'),  # Database password from .env
        'HOST': os.getenv('DB_HOST', default='localhost'),  # Database host from .env
        'PORT': os.getenv('DB_PORT', default='3306'),  # Database port from .env
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1",
        },
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

TINYMCE_JS_URL = os.path.join(STATIC_URL, "tinymce/tinymce.min.js")
TINYMCE_JS_ROOT = os.path.join(STATIC_URL, "tinymce")

TINYMCE_DEFAULT_CONFIG = {
    'height': 300,
    'plugins': "image,imagetools,media,codesample,link,code,paste,lists,advlist,table,fullscreen,wordcount,searchreplace,visualblocks,visualchars",
    'cleanup_on_startup': True,
    'menubar': 'file edit view insert format tools table',
    'toolbar': "styleselect | undo redo | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist | table | link image media | codesample code visualblocks | searchreplace | fullscreen",
    'image_caption': True,
    'image_advtab': True,
    'custom_undo_redo_levels': 10,
    'file_browser_callback': "myFileBrowser",
    'forced_root_block': 'p',
    'forced_root_block_attrs': {
        'style': 'margin-top: 0; margin-bottom: 0.5em;'
    },
    'paste_remove_styles': True,
    'paste_remove_spans': True,
    'paste_strip_class_attributes': 'all',
    'valid_elements': '*[*]',
    'valid_children': '+body[style],+div[p|h1|h2|h3|h4|h5|h6|blockquote|ul|ol|table|pre],+p[strong|em|span|br|code]',
    'element_format': 'html',
    'content_css': '/static/css/tinymce_custom.css',
    'codesample_languages': [
        { 'text': 'HTML/XML', 'value': 'markup' },
        { 'text': 'JavaScript', 'value': 'javascript' },
        { 'text': 'CSS', 'value': 'css' },
        { 'text': 'PHP', 'value': 'php' },
        { 'text': 'Ruby', 'value': 'ruby' },
        { 'text': 'Python', 'value': 'python' },
        { 'text': 'Java', 'value': 'java' },
        { 'text': 'C', 'value': 'c' },
        { 'text': 'C#', 'value': 'csharp' },
        { 'text': 'C++', 'value': 'cpp' }
    ],
    'extended_valid_elements': 'pre[class|data-language],code[class]',
    'table_default_attributes': {
        'border': '1',
        'class': 'table table-bordered'
    },
    'table_default_styles': {
        'width': '100%',
        'border-collapse': 'collapse'
    },
    'table_responsive_width': True,
    'table_class_list': [
        {'title': 'None', 'value': ''},
        {'title': 'Standard', 'value': 'table table-bordered'},
        {'title': 'Striped', 'value': 'table table-striped table-bordered'},
        {'title': 'Hover', 'value': 'table table-hover table-bordered'},
    ]
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database-backed sessions

# Session configuration
SESSION_COOKIE_AGE = 31536000  # 1 year in seconds - effectively "forever" in web terms
SESSION_SAVE_EVERY_REQUEST = True  # Update the session on every request, resetting the expiry time
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Don't expire when browser closes
SESSION_COOKIE_SECURE = not DEBUG  # Use secure cookies in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing the session cookie
SESSION_IDLE_TIMEOUT = 31536000  # 1 year in seconds - effectively disabled

GENERATIVE_AI_KEY = os.getenv('GENERATIVE_AI_KEY')

if not GENERATIVE_AI_KEY:
    raise ValueError('GENERATIVE_AI_KEY environment variable not set')

# Authentication
LOGIN_URL = 'login'  # Use the name of the login URL pattern, not the URL path