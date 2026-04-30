"""
Custom authentication backend that allows Django admin login
with either username or email address.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    """
    Authenticate against username or email.
    Django admin sends the value of the 'username' field,
    so we first try a normal username lookup; if that fails
    we try treating the value as an email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # 1. Try by username (default behaviour)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 2. Try by email
            try:
                user = User.objects.get(email=username)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
