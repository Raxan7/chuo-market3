from copy import copy as _shallow_copy

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _patch_basecontext_copy():
    """Keep the legacy RequestContext copy compatibility patch isolated."""
    try:
        from django.template.context import BaseContext
    except Exception:
        return

    if getattr(BaseContext, '_patched_copy', False):
        return

    def _safe_copy(self):
        cls = self.__class__
        duplicate = object.__new__(cls)
        duplicate.dicts = self.dicts[:]
        for attr in (
            'autoescape', 'use_l10n', 'use_tz', 'template_name',
            'render_context', 'template', 'request', '_processors', '_processors_index',
        ):
            if hasattr(self, attr):
                try:
                    setattr(duplicate, attr, _shallow_copy(getattr(self, attr)))
                except Exception:
                    setattr(duplicate, attr, getattr(self, attr))
        return duplicate

    setattr(BaseContext, '__copy__', _safe_copy)
    setattr(BaseContext, '_patched_copy', True)


def _populate_default_subscriptions(sender, **kwargs):
    """Seed subscription defaults only after migrations, never during app import."""
    from .models import Subscription
    Subscription.populate_default_data()


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Register application signals.
        import core.signals  # noqa: F401

        # Database access in AppConfig.ready() makes startup/tests fragile.
        # Seed only after this app's migrations complete.
        post_migrate.connect(
            _populate_default_subscriptions,
            sender=self,
            dispatch_uid='core.populate_default_subscriptions',
        )

        try:
            _patch_basecontext_copy()
        except Exception:
            # Compatibility patch failure must not prevent application startup.
            pass
