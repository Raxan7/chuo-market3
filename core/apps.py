from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError
from copy import copy as _shallow_copy


def _patch_basecontext_copy():
    """Monkeypatch django.template.context.BaseContext.__copy__ to avoid
    calling subclass constructors (like RequestContext) without arguments.

    This prevents TypeError when templates (for example admin change_list)
    call `context.new()` which internally uses `copy()`.
    """
    try:
        from django.template.context import BaseContext
    except Exception:
        return

    # Only patch if not already patched
    if getattr(BaseContext, '_patched_copy', False):
        return

    def _safe_copy(self):
        cls = self.__class__
        duplicate = object.__new__(cls)
        # shallow-copy the dicts list
        duplicate.dicts = self.dicts[:]

        # copy commonly-used attributes if present
        for attr in ('autoescape', 'use_l10n', 'use_tz', 'template_name', 'render_context', 'template', 'request', '_processors', '_processors_index'):
            if hasattr(self, attr):
                try:
                    setattr(duplicate, attr, _shallow_copy(getattr(self, attr)))
                except Exception:
                    setattr(duplicate, attr, getattr(self, attr))

        return duplicate

    setattr(BaseContext, '__copy__', _safe_copy)
    setattr(BaseContext, '_patched_copy', True)

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

        # Apply Django template BaseContext copy patch early to avoid
        # RequestContext copy errors in Django admin (see issue with
        # RequestContext.__init__ expecting `request`).
        try:
            _patch_basecontext_copy()
        except Exception:
            # Don't prevent app startup if patch fails
            pass
