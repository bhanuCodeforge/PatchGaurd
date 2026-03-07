import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.inventory.models import Device, DeviceGroup
from apps.patches.models import Patch
from django.utils import timezone

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin", 
        email="admin@patchguard.local", 
        password="password123",
        role="admin"
    )

@pytest.fixture
def operator_user(db):
    return User.objects.create_user(
        username="operator", 
        email="operator@patchguard.local", 
        password="password123",
        role="operator"
    )

@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def sample_device(db):
    return Device.objects.create(
        hostname="test-host",
        ip_address="192.168.1.10",
        os_family="linux",
        os_version="Ubuntu 22.04",
        status="online",
        last_seen=timezone.now()
    )

@pytest.fixture
def sample_group(db):
    return DeviceGroup.objects.create(
        name="Test Servers",
        description="Servers for testing"
    )

@pytest.fixture
def sample_patch(db):
    return Patch.objects.create(
        title="KB123456",
        description="Security update",
        severity="critical",
        os_family="windows",
        is_published=True
    )
