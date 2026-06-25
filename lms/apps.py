from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lms'

    def ready(self):
        import lms.signals
        import atexit
        # Ensure the persistent Playwright browser is closed on shutdown.
        try:
            from lms.certificates import _close_playwright
            atexit.register(_close_playwright)
        except ImportError:
            pass
