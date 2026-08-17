import os

environment = os.getenv('DJANGO_ENV', 'development').strip().lower()

if environment == 'production':
    from .prod import *
else:
    from .dev import *
