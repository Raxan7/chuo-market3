"""Render-specific settings for the disposable/team prototype environment.

This module intentionally lives beside the existing development and production
settings instead of changing them. Namecheap continues to use
``DJANGO_ENV=production`` and therefore keeps exactly the same configuration it
used before Docker support existed.
"""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403,F401


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = False
CANONICAL_REDIRECT_ENABLED = False

# Render exposes these automatically for web services. Keeping local hosts in
# the list also makes ``docker run -p ...`` useful during development.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Optional comma-separated extra hosts are useful for temporary custom domains
# without editing source code.
for host in os.getenv("RENDER_EXTRA_ALLOWED_HOSTS", "").split(","):
    host = host.strip()
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

CSRF_TRUSTED_ORIGINS = []
if RENDER_EXTERNAL_URL:
    CSRF_TRUSTED_ORIGINS.append(RENDER_EXTERNAL_URL)
elif RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

for origin in os.getenv("RENDER_EXTRA_CSRF_ORIGINS", "").split(","):
    origin = origin.strip().rstrip("/")
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

if RENDER_EXTERNAL_HOSTNAME:
    CANONICAL_DOMAIN = RENDER_EXTERNAL_HOSTNAME
    SITE_DOMAIN = RENDER_EXTERNAL_HOSTNAME

# Render terminates TLS at its proxy and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Keep local Docker usable over plain HTTP, while the actual Render service is
# HTTPS-only.
_RUNNING_ON_RENDER = bool(RENDER_EXTERNAL_HOSTNAME)
SECURE_SSL_REDIRECT = _RUNNING_ON_RENDER
CSRF_COOKIE_SECURE = _RUNNING_ON_RENDER
SESSION_COOKIE_SECURE = _RUNNING_ON_RENDER
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY is required for the Render environment. "
        "render.yaml generates one automatically."
    )

# A Render prototype deliberately gets its own database instead of silently
# connecting to the Namecheap MySQL production database. The Blueprint wires
# DATABASE_URL to a Render Postgres instance. A SQLite DATABASE_URL can still be
# supplied explicitly for local Docker smoke testing.
_database_url = os.getenv("DATABASE_URL", "").strip()
if not _database_url:
    raise ImproperlyConfigured(
        "DATABASE_URL is required when DJANGO_ENV=render. "
        "Use the isolated Render Postgres database from render.yaml."
    )

DATABASES = {
    "default": dj_database_url.parse(
        _database_url,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "60")),
    )
}
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# WhiteNoise remains responsible for collected static assets. This is inherited
# from base.py, but declared explicitly here so the deployment contract is easy
# to audit.
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Render's filesystem is ephemeral by default. Existing ChuoSmart Cloudinary
# upload paths continue to work when their credentials are supplied, but local
# MEDIA_ROOT / PRIVATE_MEDIA_ROOT files should be treated as disposable in this
# prototype unless a persistent storage strategy is added later.
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
PRIVATE_MEDIA_ROOT = os.getenv(
    "PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")  # noqa: F405
)

# Free Render web services do not permit outbound SMTP on the common SMTP ports.
# Keep email safe and testable by sending messages to service logs unless the
# operator explicitly opts in on a plan/network that supports the configured
# mail transport.
if not _env_bool("RENDER_ENABLE_OUTBOUND_EMAIL", default=False):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    MARKETING_EMAIL_BACKEND = EMAIL_BACKEND
    MARKETING_EMAIL_HOST = ""
    MARKETING_EMAIL_HOST_USER = ""
    MARKETING_EMAIL_HOST_PASSWORD = ""

# Prototype defaults: an unavailable external AI provider should not prevent a
# tester from exercising the LMS assessment flow. Setting this env var to true
# restores strict behavior.
CEREBRAS_STRICT_ASSESSMENTS = _env_bool(
    "CEREBRAS_STRICT_ASSESSMENTS", default=False
)

# Render streams stdout/stderr into its log viewer. Avoid depending on container
# filesystem log files, which are ephemeral.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "render": {
            "format": "[{asctime}] {levelname} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "render",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("RENDER_LOG_LEVEL", "INFO").upper(),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO").upper(),
            "propagate": False,
        },
        "lms": {
            "handlers": ["console"],
            "level": os.getenv("LMS_LOG_LEVEL", "INFO").upper(),
            "propagate": False,
        },
        "core.email": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
