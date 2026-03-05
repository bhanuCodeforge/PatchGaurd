import asyncio
import json
import logging
import os
import platform
import socket
import time
import uuid
import yaml
import websockets
import psutil
from typing import Dict, Any, Optional

from plugins.linux import LinuxPlugin
from plugins.windows import WindowsPlugin
from plugins.macos import MacOSPlugin

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PatchAgent")

class PatchAgent:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.device_id = self._get_device_id()
        self.plugin = self._load_plugin()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = True

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning(f"Config file {path} not found. using defaults.")
            return {
                "server_url": "ws://localhost:8001/ws/agents",
                "api_key": "default_key",
                "heartbeat_interval": 60
            }
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _get_device_id(self) -> str:
        # Use hardware UUID or persistent file
        unique_id = str(uuid.getnode())
        return unique_id

    def _load_plugin(self):
        sys_type = platform.system().lower()
        if sys_type == "linux":
            return LinuxPlugin()
        elif sys_type == "windows":
            return WindowsPlugin()
        elif sys_type == "darwin":
            return MacOSPlugin()
        else:
            raise RuntimeError(f"Unsupported OS: {sys_type}")

    async def connect(self):
        url = f"{self.config['server_url']}/{self.device_id}"
        headers = {"X-Agent-Key": self.config["api_key"]}
        backoff = 1
        
        while self.running:
            try:
                logger.info(f"Connecting to {url}...")
                async with websockets.connect(url, extra_headers=headers) as ws:
                    self.ws = ws
                    logger.info("Connected successfully.")
                    backoff = 1
                    
                    # Send initial system info
                    await self.send_system_info()
                    
                    # Run loops
                    await asyncio.gather(
                        self.heartbeat_loop(),
                        self.message_handler()
                    )
            except Exception as e:
                logger.error(f"Connection failed: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def send_system_info(self):
        info = self.plugin.get_system_info()
        data = {
            "event": "system_info",
            "payload": {
                "hostname": socket.gethostname(),
                "ip_address": socket.gethostbyname(socket.gethostname()),
                "os_family": info["os_family"],
                "os_name": info["os_name"],
                "os_version": info["os_version"],
                "architecture": info["architecture"],
                "agent_version": "1.0.0",
                "cpu_count": psutil.cpu_count(),
                "total_ram": psutil.virtual_memory().total
            }
        }
        await self.send_json(data)

    async def heartbeat_loop(self):
        while self.ws and self.ws.open:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            
            data = {
                "event": "heartbeat",
                "payload": {
                    "cpu_usage": cpu,
                    "ram_usage": mem,
                    "disk_usage": disk,
                    "status": "online",
                    "timestamp": time.time()
                }
            }
            await self.send_json(data)
            await asyncio.sleep(self.config.get("heartbeat_interval", 60))

    async def message_handler(self):
        async for message in self.ws:
            try:
                data = json.loads(message)
                command = data.get("command")
                payload = data.get("payload", {})
                
                logger.info(f"Received command: {command}")
                
                if command == "START_SCAN":
                    await self.run_scan()
                elif command == "EXECUTE_PATCH":
                    await self.run_patch(payload.get("patch_id"))
                elif command == "REBOOT":
                    self.plugin.reboot()
                elif command == "PING":
                    await self.send_json({"event": "pong", "payload": {"time": time.time()}})
                
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def run_scan(self):
        logger.info("Scanning for patches...")
        patches = self.plugin.scan_patches()
        await self.send_json({
            "event": "scan_results",
            "payload": {
                "count": len(patches),
                "patches": patches
            }
        })

    async def run_patch(self, patch_id: str):
        if not patch_id: return
        logger.info(f"Installing patch {patch_id}...")
        success = self.plugin.install_patch(patch_id)
        await self.send_json({
            "event": "patch_result",
            "payload": {
                "patch_id": patch_id,
                "status": "completed" if success else "failed"
            }
        })

    async def send_json(self, data: Dict[str, Any]):
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps(data))

if __name__ == "__main__":
    agent = PatchAgent()
    try:
        asyncio.run(agent.connect())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
