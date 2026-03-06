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

try:
    import aiohttp
    _AIOHTTP = True
except ImportError:
    _AIOHTTP = False

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
        self._set_log_level()
        self.device_id: Optional[str] = self._get_device_id()
        self.plugin = self._load_plugin()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = True
        self._connected = False
        self._rest_session: Optional[Any] = None  # aiohttp.ClientSession

    # ------------------------------------------------------------------ #
    # Config & initialisation                                              #
    # ------------------------------------------------------------------ #

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning(f"Config file {path} not found. Using defaults.")
            return {
                "server_url": "ws://localhost:8001/ws/agent",
                "rest_url": "http://localhost:8000/api/v1",
                "api_key": "",
                "heartbeat_interval": 60,
                "rest_heartbeat_interval": 300,
                "log_level": "info",
                "auto_register": False,
                "auto_register_environment": "production",
            }
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _set_log_level(self):
        level_str = self.config.get("log_level", "info").upper()
        level = getattr(logging, level_str, logging.INFO)
        logging.getLogger().setLevel(level)
        logger.setLevel(level)

    def _get_device_id(self) -> Optional[str]:
        override = self.config.get("device_id_override")
        if override:
            return str(override)
        # MAC-based UUID — stable across reboots on most hardware
        return str(uuid.UUID(int=uuid.getnode()))

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

    def _rest_url(self, path: str) -> str:
        base = self.config.get("rest_url", "http://localhost:8000/api/v1").rstrip("/")
        return f"{base}{path}"

    def _rest_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Agent-API-Key": self.config.get("api_key", ""),
        }

    # ------------------------------------------------------------------ #
    # Auto-register                                                        #
    # ------------------------------------------------------------------ #

    async def maybe_auto_register(self):
        """
        If auto_register is enabled and the api_key looks like a placeholder
        (or is blank), register this device via REST and persist the returned
        api_key + device_id back to config.yaml.
        """
        if not self.config.get("auto_register", False):
            return

        api_key = self.config.get("api_key", "")
        if api_key and api_key != "AGENT_SECRET_KEY_PLACEHOLDER":
            logger.debug("Auto-register skipped — api_key already set.")
            return

        if not _AIOHTTP:
            logger.warning("aiohttp not installed — auto-register skipped.")
            return

        try:
            hostname = self.config.get("auto_register_hostname") or socket.gethostname()
            os_family = self.config.get("auto_register_os_family") or platform.system().lower()
            environment = self.config.get("auto_register_environment", "production")

            try:
                ip_address = socket.gethostbyname(hostname)
            except Exception:
                ip_address = "127.0.0.1"

            payload = {
                "hostname": hostname,
                "ip_address": ip_address,
                "os_family": os_family,
                "environment": environment,
                "agent_version": "1.0.0",
            }

            logger.info(f"Auto-registering device '{hostname}' with PatchGuard server...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._rest_url("/devices/"),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        new_api_key = data.get("agent_api_key", "")
                        new_device_id = str(data.get("id", ""))

                        if new_api_key:
                            logger.info(f"Auto-register succeeded. Device ID: {new_device_id}")
                            self.config["api_key"] = new_api_key
                            self.config["device_id_override"] = new_device_id
                            self.device_id = new_device_id
                            self._persist_config()
                        else:
                            logger.warning("Auto-register response missing agent_api_key.")
                    else:
                        body = await resp.text()
                        logger.warning(f"Auto-register failed [{resp.status}]: {body[:200]}")
        except Exception as e:
            logger.error(f"Auto-register error: {e}")

    def _persist_config(self):
        """Write updated api_key + device_id_override back to config.yaml."""
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r") as f:
                content = f.read()

            import re
            content = re.sub(
                r'^(api_key:\s*).*$',
                f'api_key: "{self.config["api_key"]}"',
                content, flags=re.MULTILINE
            )
            content = re.sub(
                r'^(device_id_override:\s*).*$',
                f'device_id_override: "{self.config["device_id_override"]}"',
                content, flags=re.MULTILINE
            )
            with open(config_path, "w") as f:
                f.write(content)
            logger.info("config.yaml updated with new api_key and device_id_override.")
        except Exception as e:
            logger.warning(f"Failed to persist config: {e}")

    # ------------------------------------------------------------------ #
    # REST heartbeat                                                       #
    # ------------------------------------------------------------------ #

    async def rest_heartbeat_loop(self):
        """
        POST /devices/{id}/heartbeat/ via REST at a configurable interval.
        This updates last_seen + status even when the WebSocket is offline.
        """
        interval = self.config.get("rest_heartbeat_interval", 300)
        if not interval or interval <= 0:
            return
        if not _AIOHTTP:
            logger.warning("aiohttp not installed — REST heartbeat disabled.")
            return

        await asyncio.sleep(10)  # brief initial delay before first REST beat

        while self.running:
            try:
                device_id = self.device_id
                if not device_id:
                    await asyncio.sleep(interval)
                    continue

                cpu = psutil.cpu_percent(interval=0)
                mem = psutil.virtual_memory().percent
                disk = self._disk_usage()

                payload = {
                    "cpu_usage": cpu,
                    "ram_usage": mem,
                    "disk_usage": disk,
                    "agent_version": "1.0.0",
                    "status": "online",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self._rest_url(f"/devices/{device_id}/heartbeat/"),
                        json=payload,
                        headers=self._rest_headers(),
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            logger.debug(f"REST heartbeat OK (device={device_id})")
                        else:
                            body = await resp.text()
                            logger.warning(f"REST heartbeat [{resp.status}]: {body[:120]}")
            except Exception as e:
                logger.warning(f"REST heartbeat error: {e}")

            await asyncio.sleep(interval)

    # ------------------------------------------------------------------ #
    # WebSocket connection                                                 #
    # ------------------------------------------------------------------ #

    async def connect(self):
        # Auto-register before connecting, if configured
        await self.maybe_auto_register()

        server_url = self.config.get("server_url", "ws://localhost:8001/ws/agent")
        api_key = self.config.get("api_key", "")
        url = f"{server_url}?api_key={api_key}"
        backoff = 1

        while self.running:
            try:
                logger.info(f"Connecting to {server_url} (device_id={self.device_id})...")
                async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
                    self.ws = ws
                    self._connected = True
                    logger.info("WebSocket connected.")
                    backoff = 1  # reset on success

                    await self.send_system_info()

                    await asyncio.gather(
                        self.heartbeat_loop(),
                        self.message_handler(),
                        return_exceptions=True
                    )
            except (websockets.ConnectionClosed, websockets.WebSocketException, OSError) as e:
                logger.warning(f"Connection lost: {e}. Retrying in {backoff}s...")
            except Exception as e:
                logger.error(f"Unexpected error: {e}. Retrying in {backoff}s...")
            finally:
                self._connected = False
                self.ws = None

            if not self.running:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    # ------------------------------------------------------------------ #
    # WebSocket helpers                                                    #
    # ------------------------------------------------------------------ #

    async def send_system_info(self):
        try:
            info = self.plugin.get_system_info()
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            info = {
                "os_family": platform.system().lower(),
                "os_name": platform.system(),
                "os_version": platform.release(),
                "architecture": platform.machine(),
            }

        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
        except Exception:
            hostname = "unknown"
            ip_address = "127.0.0.1"

        await self.send_json({
            "event": "system_info",
            "payload": {
                "device_id": self.device_id,
                "hostname": hostname,
                "ip_address": ip_address,
                "os_family": info.get("os_family", ""),
                "os_name": info.get("os_name", ""),
                "os_version": info.get("os_version", ""),
                "architecture": info.get("architecture", ""),
                "agent_version": "1.0.0",
                "cpu_count": psutil.cpu_count(),
                "total_ram": psutil.virtual_memory().total,
                "tags": self.config.get("tags", []),
            }
        })

    async def heartbeat_loop(self):
        interval = self.config.get("heartbeat_interval", 60)
        while self._connected:
            try:
                await self.send_json({
                    "event": "heartbeat",
                    "payload": {
                        "device_id": self.device_id,
                        "cpu_usage": psutil.cpu_percent(interval=0),
                        "ram_usage": psutil.virtual_memory().percent,
                        "disk_usage": self._disk_usage(),
                        "status": "online",
                        "timestamp": time.time(),
                    }
                })
            except Exception as e:
                logger.error(f"WS heartbeat error: {e}")
                break
            await asyncio.sleep(interval)

    def _disk_usage(self) -> float:
        try:
            path = "C:\\" if platform.system() == "Windows" else "/"
            return psutil.disk_usage(path).percent
        except Exception:
            return 0.0

    async def message_handler(self):
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    command = data.get("command") or data.get("event")
                    payload = data.get("payload", {})
                    logger.info(f"Received command: {command}")

                    if command == "START_SCAN":
                        await self.run_scan()
                    elif command == "EXECUTE_PATCH":
                        await self.run_patch(payload.get("patch_id"))
                    elif command == "START_DEPLOYMENT":
                        await self.run_deployment(payload)
                    elif command == "CANCEL_DEPLOYMENT":
                        logger.info(f"Deployment {payload.get('deployment_id')} cancelled by server.")
                    elif command == "REBOOT":
                        self.plugin.reboot()
                    elif command == "PING":
                        await self.send_json({"event": "pong", "payload": {
                            "device_id": self.device_id,
                            "time": time.time(),
                        }})
                    elif command == "GET_SYSTEM_INFO":
                        await self.send_system_info()
                    else:
                        logger.warning(f"Unknown command: {command}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except Exception:
            pass  # Connection closed; connect() handles reconnection

    async def run_scan(self):
        logger.info("Scanning for patches...")
        try:
            patches = self.plugin.scan_patches()
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            patches = []
        await self.send_json({
            "event": "scan_results",
            "payload": {
                "device_id": self.device_id,
                "count": len(patches),
                "patches": patches,
            }
        })

    async def run_deployment(self, payload: dict):
        deployment_id = payload.get("deployment_id", "")
        target_id = payload.get("target_id", "")
        patch_ids = payload.get("patches", [])

        logger.info(f"Running deployment {deployment_id} ({len(patch_ids)} patches) for target {target_id}")
        failed = []
        for pid in patch_ids:
            try:
                success = self.plugin.install_patch(pid)
                if not success:
                    failed.append(pid)
            except Exception as e:
                logger.error(f"Patch {pid} install error: {e}")
                failed.append(pid)

        result_status = "failed" if failed else "completed"
        await self.send_json({
            "event": "patch_result",
            "payload": {
                "device_id": self.device_id,
                "deployment_id": deployment_id,
                "target_id": target_id,
                "status": result_status,
                "patches_installed": len(patch_ids) - len(failed),
                "patches_failed": failed,
                "timestamp": time.time(),
            }
        })
        logger.info(f"Deployment {deployment_id} result: {result_status} ({len(failed)} failed patches)")

    async def run_patch(self, patch_id: str):
        if not patch_id:
            return
        logger.info(f"Installing patch {patch_id}...")
        try:
            success = self.plugin.install_patch(patch_id)
        except Exception as e:
            logger.error(f"Patch install failed: {e}")
            success = False
        await self.send_json({
            "event": "patch_result",
            "payload": {
                "device_id": self.device_id,
                "patch_id": patch_id,
                "status": "completed" if success else "failed",
                "timestamp": time.time(),
            }
        })

    async def send_json(self, data: Dict[str, Any]):
        if self.ws is not None and self._connected:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                logger.warning(f"send_json failed: {e}")
                self._connected = False

    def stop(self):
        self.running = False
        self._connected = False


async def _run(agent: PatchAgent):
    """Run WebSocket connect loop and REST heartbeat concurrently."""
    await asyncio.gather(
        agent.connect(),
        agent.rest_heartbeat_loop(),
        return_exceptions=True,
    )


if __name__ == "__main__":
    agent = PatchAgent()
    try:
        asyncio.run(_run(agent))
    except KeyboardInterrupt:
        agent.stop()
        logger.info("Agent stopped by user.")
