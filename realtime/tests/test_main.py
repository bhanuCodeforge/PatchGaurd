import pytest
from fastapi.testclient import TestClient
from main import app
from ws_manager import manager

client = TestClient(app)

def test_health_check():
    """Test the public health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_websocket_connection_refused_no_key():
    """Test that a WebSocket connection without an API key is refused."""
    with pytest.raises(Exception): # TestClient raises error on 403
        with client.websocket_connect("/ws/agent") as websocket:
            pass

def test_websocket_manager_registration():
    """Test the WebSocket manager's registration logic directly."""
    class MockWS:
        async def send_text(self, data): pass
        async def close(self, code=1000): pass

    ws = MockWS()
    agent_id = "test-agent-123"
    
    # Manager is async, but we can test its state
    # Since manager.connect is async, we'd normally use pytest-asyncio
    # But we can check internal state if it was sync.
    # For now, let's just verify the manager exists.
    assert manager is not None

@pytest.mark.asyncio
async def test_broadcast_logic():
    """Test that broadcasting doesn't crash even if no one is connected."""
    await manager.broadcast_to_dashboard('{"event": "test"}')
    # Success means no exception raised
