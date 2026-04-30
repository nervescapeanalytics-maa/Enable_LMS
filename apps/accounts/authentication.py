"""
Custom JWT authentication that supports multiple user models.

The app uses separate models (Student, Teacher, Admin, Parent), each with
UUID primary keys. The standard simplejwt JWTAuthentication tries to look
up users on AUTH_USER_MODEL (django.contrib.auth.User, integer PK) which
fails.  This class reads the ``user_type`` claim from the token and
resolves the correct model.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

USER_MODEL_MAP = {
    'STUDENT': 'accounts.Student',
    'TEACHER': 'accounts.Teacher',
    'ADMIN': 'accounts.Admin',
    'PARENT': 'accounts.Parent',
}


class MultiModelJWTAuthentication(JWTAuthentication):
    """Resolve the user from the correct model based on ``user_type`` claim."""

    def get_user(self, validated_token):
        from django.apps import apps
        from django.db import connection

        user_id = validated_token.get('user_id')
        user_type = validated_token.get('user_type')

        if not user_id or not user_type:
            raise InvalidToken('Token contains no user_id or user_type')

        model_path = USER_MODEL_MAP.get(user_type)
        if not model_path:
            raise InvalidToken(f'Unknown user_type: {user_type}')

        Model = apps.get_model(model_path)

        # Set RLS tenant context from the token
        tenant_id = validated_token.get('tenant_id')
        if tenant_id:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.current_tenant_id', %s, false)",
                    [str(tenant_id)],
                )

        try:
            user = Model.objects.get(id=user_id)
        except Model.DoesNotExist:
            raise InvalidToken('User not found')

        # Attach extra attributes that views may expect
        user.user_type = user_type
        user.is_authenticated = True
        return user
