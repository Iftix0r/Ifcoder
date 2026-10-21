import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("iftixor", password="Parol-2026!", first_name="Iftixor")


@pytest.fixture
def client_in(client, user):
    client.force_login(user)
    return client
