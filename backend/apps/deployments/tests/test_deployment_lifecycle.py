import pytest
from django.urls import reverse
from rest_framework import status
from apps.deployments.models import Deployment

@pytest.mark.django_db
class TestDeploymentLifecycle:
    def test_list_deployments(self, auth_client):
        url = reverse('deployment-list')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_deployment(self, auth_client, sample_device, sample_patch):
        url = reverse('deployment-list')
        data = {
            "name": "Test Deployment",
            "description": "Deployment description",
            "patch_id": sample_patch.id,
            "device_ids": [str(sample_device.id)]
        }
        response = auth_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Deployment.objects.filter(name="Test Deployment").exists()

    def test_get_deployment_detail(self, auth_client, sample_device, sample_patch):
        # Create deployment first
        d = Deployment.objects.create(
            name="Manual Deployment",
            patch=sample_patch,
            status="scheduled",
            created_by_id=1 # Admin
        )
        url = reverse('deployment-detail', args=[d.id])
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Manual Deployment"

    def test_deployment_stats(self, auth_client):
        url = reverse('deployment-stats')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_deployments' in response.data

    def test_compliance_report(self, auth_client):
        url = reverse('compliance-report')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'overall_compliance' in response.data
