import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin_test",
        password="TestPass123!",
        email="admin@test.com",
    )


@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
