import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="adminuser", password="TestPassword123!")
    user.role = "admin"
    user.save()
    return user

@pytest.fixture
def viewer_user(db):
    user = User.objects.create_user(username="vieweruser", password="TestPassword123!")
    user.role = "viewer"
    user.save()
    return user

@pytest.mark.django_db
def test_admin_can_access_users(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    # The viewset is registered at the blank prefix inside the include
    url = "/api/v1/users/" 
    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_viewer_cannot_access_users(api_client, viewer_user):
    api_client.force_authenticate(user=viewer_user)
    url = "/api/v1/users/"
    res = api_client.get(url)
    assert res.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_unauthenticated_gets_401(api_client):
    url = "/api/v1/users/"
    res = api_client.get(url)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
