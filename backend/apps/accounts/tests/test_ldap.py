import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock ldap module before any imports
sys.modules['ldap'] = MagicMock()

from django.contrib.auth import get_user_model
from apps.accounts.ldap_backend import LDAPBackend

User = get_user_model()

@pytest.fixture
def ldap_backend():
    return LDAPBackend()

@pytest.mark.django_db
@patch('apps.accounts.ldap_backend.ldap.initialize')
def test_ldap_authenticate_success(mock_initialize, ldap_backend, settings):
    settings.LDAP_URI = 'ldap://test'
    settings.LDAP_BIND_DN_TEMPLATE = 'uid=%s,dc=test'
    settings.LDAP_SEARCH_BASE = 'dc=test'
    
    mock_conn = MagicMock()
    mock_initialize.return_value = mock_conn
    
    # Mock result
    mock_conn.search.return_value = 1
    mock_conn.result.return_value = (None, [
        ('uid=testuser,dc=test', {
            'mail': [b'test@test.com'],
            'givenName': [b'Test'],
            'sn': [b'User'],
            'memberOf': [b'CN=PatchMgr-Admins,OU=Groups,DC=test']
        })
    ])

    user = ldap_backend.authenticate(None, username='testuser', password='password')
    
    assert user is not None
    assert user.username == 'testuser'
    assert user.role == 'admin'
    assert user.is_ldap_user is True

@pytest.mark.django_db
@patch('apps.accounts.ldap_backend.ldap.initialize')
def test_ldap_authenticate_invalid_credentials(mock_initialize, ldap_backend, settings):
    settings.LDAP_URI = 'ldap://test'
    
    mock_conn = MagicMock()
    mock_initialize.return_value = mock_conn
    
    import ldap
    mock_conn.simple_bind_s.side_effect = ldap.INVALID_CREDENTIALS()

    user = ldap_backend.authenticate(None, username='testuser', password='wrong')
    
    assert user is None
