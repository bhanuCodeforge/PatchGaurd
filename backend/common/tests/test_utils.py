import pytest
from unittest.mock import Mock, patch
from common.utils import generate_api_key, get_client_ip, batch_qs

def test_generate_api_key():
    key = generate_api_key()
    assert len(key) == 64
    assert isinstance(key, str)

def test_get_client_ip_with_x_forwarded():
    request = Mock()
    request.META = {'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1'}
    ip = get_client_ip(request)
    assert ip == '192.168.1.1'

def test_get_client_ip_with_remote_addr():
    request = Mock()
    request.META = {'REMOTE_ADDR': '10.0.0.5'}
    ip = get_client_ip(request)
    assert ip == '10.0.0.5'

def test_batch_qs():
    class DummyQuerySet:
        def __init__(self, data):
            self.data = data
        def count(self):
            return len(self.data)
        def __getitem__(self, item):
            return self.data[item]
            
    qs = DummyQuerySet(list(range(10)))
    
    batches = list(batch_qs(qs, batch_size=3))
    assert len(batches) == 4
    assert batches[0] == [0, 1, 2]
    assert batches[3] == [9]
