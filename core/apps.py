from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import django.db.models.signals  # Ensure models are loaded
        # from .models import Subscription
        # Subscription.populate_default_data()
