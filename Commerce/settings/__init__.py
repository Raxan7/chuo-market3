import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

environment = os.getenv('DJANGO_ENV', '').strip().lower()

if environment not in {'development', 'production', 'render'}:
    raise ImproperlyConfigured(
        "DJANGO_ENV must be explicitly set to 'development', 'production', or 'render'. "
        "This prevents production from silently booting with development settings."
    )

if environment == 'production':
    from .prod import *
elif environment == 'render':
    from .render import *
else:
    from .dev import *
