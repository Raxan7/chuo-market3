"""Authentication views with production-safe ChuoSmart email defaults."""
import hashlib
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views

logger = logging.getLogger('email')


class ChuoSmartPasswordResetView(auth_views.PasswordResetView):
    """Use the support mailbox explicitly and leave useful server-side diagnostics.

    Django intentionally returns the same public response whether an account exists
    or not. The log entry therefore records only a short hash of the submitted email
    plus match counts, so production operators can diagnose delivery without exposing
    account existence to the requester.
    """

    def dispatch(self, request, *args, **kwargs):
        # Read this setting at request time instead of URL import time, so the
        # production environment is always authoritative.
        self.from_email = getattr(
            settings,
            'PASSWORD_RESET_FROM_EMAIL',
            'support@chuosmart.com',
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip()
        UserModel = get_user_model()
        candidates = UserModel._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )
        usable_count = sum(1 for user in candidates if user.has_usable_password())
        email_hash = hashlib.sha256(email.lower().encode('utf-8')).hexdigest()[:12] if email else 'empty'
        logger.info(
            'Password reset requested: email_hash=%s active_matches=%s usable_password_matches=%s backend=%s from=%s',
            email_hash,
            candidates.count(),
            usable_count,
            getattr(settings, 'EMAIL_BACKEND', ''),
            self.from_email,
        )
        return super().form_valid(form)
