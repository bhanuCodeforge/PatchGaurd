import pytest
from django.urls import reverse
from rest_framework import status
from apps.patches.models import Patch

@pytest.mark.django_db
class TestPatchWorkflow:
    def test_list_patches(self, auth_client, sample_patch):
        url = reverse('patch-list')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_approve_patch(self, auth_client, sample_patch):
        url = reverse('patch-approve', args=[sample_patch.id])
        response = auth_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        sample_patch.refresh_from_db()
        assert sample_patch.is_published is True

    def test_patch_catalog_summary(self, auth_client, sample_patch):
        url = reverse('patch-summary')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_available' in response.data
        assert 'by_severity' in response.data

    def test_compliance_summary(self, auth_client):
        url = reverse('compliance-summary')
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'overall_compliance' in response.data
