"""Small, observable wrapper for transactional email delivery."""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger('email')


def send_transactional_email(*, subject, message, recipients, html_message=None, from_email=None, raise_on_error=False):
    """Send a transactional email without hiding SMTP failures.

    Product actions should not normally fail just because notification delivery is
    unavailable, so callers receive False by default. Critical callers can request
    the original exception with ``raise_on_error=True``.
    """
    recipients = [address for address in recipients if address]
    if not recipients:
        logger.warning('Skipped transactional email %r because there are no recipients.', subject)
        return False

    try:
        sent = send_mail(
            subject,
            message,
            from_email or settings.DEFAULT_FROM_EMAIL,
            recipients,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Transactional email failed: subject=%r recipients=%s', subject, recipients)
        if raise_on_error:
            raise
        return False

    if sent != 1:
        logger.error('Transactional email backend returned %s for subject=%r recipients=%s', sent, subject, recipients)
        return False
    return True
