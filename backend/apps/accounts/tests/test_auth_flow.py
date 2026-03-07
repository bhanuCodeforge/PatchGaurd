import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestAuthFlow:
    def test_login_success(self, api_client, admin_user):
        url = reverse('login')
        data = {
            "username": "admin",
            "password": "password123"
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_invalid_password(self, api_client, admin_user):
        url = reverse('login')
        data = {
            "username": "admin",
            "password": "wrongpassword"
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, admin_user):
        # Login to get refresh token
        login_url = reverse('login')
        login_data = {"username": "admin", "password": "password123"}
        login_res = api_client.post(login_url, login_data)
        refresh_token = login_res.data['refresh']

        # Refresh
        refresh_url = reverse('token_refresh')
        response = api_client.post(refresh_url, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_get_current_user(self, auth_client, admin_user):
        url = reverse('me')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == "admin"
        assert response.data['role'] == "admin"
