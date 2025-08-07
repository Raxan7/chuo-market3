from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'
    
    def ready(self):
        """
        Initialize scheduler when the app is ready.
        This will start the background job to fetch jobs from APIs periodically.
        """
        # Import here to avoid AppRegistryNotReady exception
        try:
            from .scheduler import start_scheduler
            start_scheduler()
        except ImportError:
            # If django-apscheduler is not installed, log a warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("django-apscheduler is not installed. Automatic job fetching will not work.")
