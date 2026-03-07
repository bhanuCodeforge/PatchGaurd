import pytest
import asyncio
import json
import yaml
from unittest.mock import MagicMock, AsyncMock, patch
from agent import PatchAgent

@pytest.fixture
def mock_config(tmp_path):
    config = {
        "server_url": "ws://localhost:8001/ws/agent",
        "rest_url": "http://localhost:8000/api/v1",
        "api_key": "test_key",
        "device_id_override": "test_device_id",
        "heartbeat_interval": 60,
        "log_level": "info"
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return str(config_file)

@pytest.mark.asyncio
async def test_agent_initialization(mock_config):
    with patch("agent.platform.system", return_value="Linux"):
        with patch("agent.LinuxPlugin") as mock_plugin:
            agent = PatchAgent(config_path=mock_config)
            assert agent.device_id == "test_device_id"
            assert agent.config["api_key"] == "test_key"
            assert agent.plugin is not None

@pytest.mark.asyncio
async def test_agent_load_plugin_windows():
    with patch("agent.platform.system", return_value="Windows"):
        with patch("agent.WindowsPlugin") as mock_plugin:
            agent = PatchAgent(config_path="non_existent.yaml")
            assert agent.plugin is not None

@pytest.mark.asyncio
async def test_agent_message_handler_scan(mock_config):
    with patch("agent.platform.system", return_value="Linux"):
        with patch("agent.LinuxPlugin") as mock_plugin:
            agent = PatchAgent(config_path=mock_config)
            agent.ws = AsyncMock()
            agent.plugin.scan_patches = MagicMock(return_value=[])
            
            # Simulate START_SCAN message
            message = json.dumps({"command": "START_SCAN", "payload": {}})
            
            # We need to mock the ws iterator
            agent.ws.__aiter__.return_value = [message]
            
            # Run the handler for one message
            await agent.message_handler()
            
            # Verify scan_patches was called
            agent.plugin.scan_patches.assert_called_once()
            # Verify results were sent
            agent.ws.send.assert_called()
            sent_data = json.loads(agent.ws.send.call_args[0][0])
            assert sent_data["event"] == "scan_results"

@pytest.mark.asyncio
async def test_agent_message_handler_reboot(mock_config):
    with patch("agent.platform.system", return_value="Linux"):
        with patch("agent.LinuxPlugin") as mock_plugin:
            agent = PatchAgent(config_path=mock_config)
            agent.ws = AsyncMock()
            agent.plugin.reboot = MagicMock()
            
            # Simulate REBOOT message
            message = json.dumps({"command": "REBOOT", "payload": {}})
            agent.ws.__aiter__.return_value = [message]
            
            await agent.message_handler()
            
            agent.plugin.reboot.assert_called_once()
