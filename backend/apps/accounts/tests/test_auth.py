import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!"
    )
    user.role = "viewer"
    user.save()
    return user

@pytest.mark.django_db
def test_login_success(api_client, test_user):
    url = reverse('login')
    response = api_client.post(url, {
        "username": "testuser",
        "password": "TestPassword123!"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data

@pytest.mark.django_db
def test_login_invalid_credentials(api_client, test_user):
    url = reverse('login')
    response = api_client.post(url, {
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_account_lockout_after_5_failures(api_client, test_user):
    url = reverse('login')
    for _ in range(5):
        api_client.post(url, {"username": "testuser", "password": "wrongpassword"})
    
    test_user.refresh_from_db()
    assert test_user.locked_until is not None
    assert test_user.locked_until > timezone.now()

    # Even right password should fail now
    response = api_client.post(url, {"username": "testuser", "password": "TestPassword123!"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_token_refresh(api_client, test_user):
    url = reverse('login')
    res = api_client.post(url, {"username": "testuser", "password": "TestPassword123!"})
    refresh = res.data["refresh"]

    refresh_url = reverse('token_refresh')
    refresh_res = api_client.post(refresh_url, {"refresh": refresh})
    assert refresh_res.status_code == status.HTTP_200_OK
    assert "access" in refresh_res.data
    # old token should be fine simplejwt defaults or might be blacklisted if requested

@pytest.mark.django_db
def test_logout_blacklists_refresh(api_client, test_user):
    url = reverse('login')
    res = api_client.post(url, {"username": "testuser", "password": "TestPassword123!"})
    refresh = res.data["refresh"]
    access = res.data["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    logout_url = reverse('logout')
    logout_res = api_client.post(logout_url, {"refresh": refresh})
    
    assert logout_res.status_code == status.HTTP_205_RESET_CONTENT

    # Trying to reuse refresh should fail
    refresh_url = reverse('token_refresh')
    refresh_res = api_client.post(refresh_url, {"refresh": refresh})
    assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED
    
@pytest.mark.django_db
def test_password_change_complexity_validation(api_client, test_user):
    url = reverse('login')
    res = api_client.post(url, {"username": "testuser", "password": "TestPassword123!"})
    access = res.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    change_pw_url = reverse('change_password')
    # Too short
    res1 = api_client.post(change_pw_url, {"old_password": "TestPassword123!", "new_password": "short"})
    assert res1.status_code == status.HTTP_400_BAD_REQUEST

    # Lacks number/special
    res2 = api_client.post(change_pw_url, {"old_password": "TestPassword123!", "new_password": "TestPasswordLong"})
    assert res2.status_code == status.HTTP_400_BAD_REQUEST

    # Valid
    res3 = api_client.post(change_pw_url, {"old_password": "TestPassword123!", "new_password": "NewTestPassword123!"})
    assert res3.status_code == status.HTTP_200_OK
