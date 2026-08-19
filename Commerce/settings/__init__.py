import os
from dotenv import load_dotenv

load_dotenv()

environment = os.getenv('DJANGO_ENV', 'development').strip().lower()

if environment == 'production':
    from .prod import *
else:
    from .dev import *
