from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import django.db.models.signals  # Ensure models are loaded
        from .models import Subscription
        # Register signals
        import core.signals
        
        # Try to create default subscriptions if they don't exist
        # Wrapped in try-except to handle case when tables don't exist yet
        try:
            Subscription.populate_default_data()
        except (OperationalError, ProgrammingError):
            # Tables don't exist yet, migrations need to be run
            print("Warning: Could not create default subscriptions - run migrations first")
