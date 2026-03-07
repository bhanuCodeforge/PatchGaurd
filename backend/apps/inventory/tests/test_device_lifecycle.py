import pytest
from django.urls import reverse
from rest_framework import status
from apps.inventory.models import Device

@pytest.mark.django_db
class TestDeviceLifecycle:
    def test_list_devices(self, auth_client, sample_device):
        url = reverse('device-list')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_create_device(self, auth_client):
        url = reverse('device-list')
        data = {
            "hostname": "new-server",
            "ip_address": "10.0.0.5",
            "os_family": "windows",
            "os_version": "Server 2022"
        }
        response = auth_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Device.objects.filter(hostname="new-server").exists()

    def test_get_device_detail(self, auth_client, sample_device):
        url = reverse('device-detail', args=[sample_device.id])
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['hostname'] == "test-host"

    def test_update_device(self, auth_client, sample_device):
        url = reverse('device-detail', args=[sample_device.id])
        data = {"description": "Updated Description"}
        response = auth_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        sample_device.refresh_from_db()
        assert sample_device.description == "Updated Description"

    def test_delete_device(self, auth_client, sample_device):
        url = reverse('device-detail', args=[sample_device.id])
        response = auth_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Device.objects.filter(id=sample_device.id).exists()
