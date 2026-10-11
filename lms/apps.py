from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lms'

    def ready(self):

        from . import pricing_signals  # noqa: F401
        import lms.signals
