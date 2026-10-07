"""Authentication backends for ChuoSmart."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate a user with either their username or their email address.

    Username lookup is attempted first to preserve existing behaviour. If there
    is no such username, the same identifier is treated as an email address and
    matched case-insensitively. Ambiguous legacy duplicate email addresses are
    rejected rather than guessing which account should be authenticated.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = username or kwargs.get(UserModel.USERNAME_FIELD)

        if identifier is None or password is None:
            return None

        identifier = str(identifier).strip()
        if not identifier:
            return None

        # Preserve the current username login path exactly as the first choice.
        try:
            user = UserModel._default_manager.get_by_natural_key(identifier)
        except UserModel.DoesNotExist:
            # Email is not unique at the database level for Django's default
            # User model. Fail closed if historical data contains duplicates.
            email_matches = list(
                UserModel._default_manager.filter(email__iexact=identifier)[:2]
            )
            if len(email_matches) != 1:
                return None
            user = email_matches[0]

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
