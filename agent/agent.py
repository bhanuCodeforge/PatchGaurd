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
from dotenv import load_dotenv

# Load .env file
load_dotenv()

try:
    import aiohttp
    _AIOHTTP = True
except ImportError:
    _AIOHTTP = False

from plugins.linux import LinuxPlugin
from plugins.windows import WindowsPlugin
from plugins.macos import MacOSPlugin
from collectors.scheduler import LaneScheduler
from logging_utils import trace

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
        self.version = "1.0.0"
        self._scheduler: Optional[LaneScheduler] = None

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
        level_str = os.getenv("AGENT_LOG_LEVEL", self.config.get("log_level", "info")).upper()
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
        """Standardised persistence for all config fields."""
        config_path = "config.yaml"
        try:
            with open(config_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info("config.yaml successfully updated.")
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

                info = self.plugin.get_system_info()
                payload = {
                    "cpu_usage": cpu,
                    "ram_usage": mem,
                    "disk_usage": disk,
                    "agent_version": self.version,
                    "status": "online",
                    "cpu_count": info.get("cpu_count"),
                    "total_ram": info.get("total_ram"),
                    "total_disk": info.get("total_disk"),
                    "uptime": info.get("uptime"),
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

    @trace
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
                    await self.send_inventory()
                    # Trigger initial scan to sync patch state immediately
                    asyncio.create_task(self.run_scan())

                    # Initialise lane scheduler (fast=5s, slow=15min)
                    self._scheduler = LaneScheduler(
                        send_fn=self._send_lane_event,
                        device_id=self.device_id,
                        fast_interval=self.config.get("fast_lane_interval", 5),
                        slow_interval=self.config.get("slow_lane_interval", 900),
                        fast_concurrency=self.config.get("fast_lane_concurrency", 2),
                        slow_concurrency=self.config.get("slow_lane_concurrency", 1),
                    )

                    await asyncio.gather(
                        self.heartbeat_loop(),
                        self.message_handler(),
                        self._scheduler.start(),
                        return_exceptions=True
                    )
            except (websockets.ConnectionClosed, websockets.WebSocketException, OSError) as e:
                logger.warning(f"Connection lost: {e}. Retrying in {backoff}s...")
            except Exception as e:
                logger.error(f"Unexpected error: {e}. Retrying in {backoff}s...")
            finally:
                self._connected = False
                self.ws = None
                if self._scheduler:
                    self._scheduler.stop()
                    self._scheduler = None

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
                "mac_address": str(uuid.UUID(int=uuid.getnode())),
                "os_family": info.get("os_family", ""),
                "os_name": info.get("os_name", ""),
                "os_version": info.get("os_version", ""),
                "architecture": info.get("architecture", ""),
                "agent_version": self.version,
                "cpu_count": info.get("cpu_count", psutil.cpu_count()),
                "total_ram": info.get("total_ram", psutil.virtual_memory().total),
                "total_disk": info.get("total_disk", 0),
                "uptime": info.get("uptime", ""),
                "serial_number": info.get("serial_number", "—"),
                "log_level": self.config.get("log_level", "info"),
                "heartbeat_interval": self.config.get("heartbeat_interval", 60),
                "tags": self.config.get("tags", []),
            }
        })

    async def send_inventory(self):
        try:
            logger.info("Collecting detailed inventory...")
            inv = self.plugin.get_inventory()
            await self.send_json({
                "event": "inventory_info",
                "payload": {
                    "device_id": self.device_id,
                    "inventory": inv
                }
            })
        except Exception as e:
            logger.error(f"Failed to send inventory: {e}")

    async def _send_lane_event(self, event: str, payload: Dict[str, Any]):
        """Callback used by LaneScheduler to send data over the WebSocket."""
        await self.send_json({"event": event, "payload": payload})

    @trace
    async def heartbeat_loop(self):
        interval = self.config.get("heartbeat_interval", 60)
        full_info_counter = 0
        last_full_info: Dict[str, Any] = {}
        while self._connected:
            try:
                # Read dynamic interval in case it was changed via CONFIG_UPDATE
                interval = self.config.get("heartbeat_interval", 60)

                payload: Dict[str, Any] = {
                    "device_id": self.device_id,
                    "cpu_usage": psutil.cpu_percent(interval=0),
                    "ram_usage": psutil.virtual_memory().percent,
                    "disk_usage": self._disk_usage(),
                    "status": "online",
                    "timestamp": time.time(),
                    "agent_version": self.version,
                }

                # Send full system info every 10th heartbeat or on first connect
                full_info_counter += 1
                if full_info_counter >= 10 or not last_full_info:
                    info = self.plugin.get_system_info()
                    payload.update({
                        "cpu_count": info.get("cpu_count"),
                        "total_ram": info.get("total_ram"),
                        "total_disk": info.get("total_disk"),
                        "uptime": info.get("uptime"),
                        "serial_number": info.get("serial_number", "—"),
                        "log_level": self.config.get("log_level", "info"),
                        "heartbeat_interval": interval,
                    })
                    last_full_info = payload.copy()
                    full_info_counter = 0

                await self.send_json({"event": "heartbeat", "payload": payload})
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
                    # Enveloped message: { "event": "...", "payload": { ... } }
                    command = data.get("command") or data.get("event")
                    payload = data.get("payload", {})
                    
                    if not command:
                        logger.warning(f"Received malformed message (no command/event): {message}")
                        continue
                        
                    logger.info(f"Received command: {command}")

                    if command == "START_SCAN":
                        await self.run_scan()
                    elif command == "COLLECT_FAST_LANE":
                        if self._scheduler:
                            metrics = self._scheduler._fast.collect()
                            metrics["device_id"] = self.device_id
                            await self._send_lane_event("metrics", metrics)
                        else:
                            # Fallback if scheduler not ready yet
                            payload = {
                                "device_id": self.device_id,
                                "cpu_percent": psutil.cpu_percent(interval=0),
                                "memory_percent": psutil.virtual_memory().percent,
                                "disk_usage_percent": self._disk_usage(),
                                "timestamp": time.time(),
                            }
                            await self._send_lane_event("metrics", payload)
                    elif command == "COLLECT_SLOW_LANE":
                        if self._scheduler:
                            loop = asyncio.get_event_loop()
                            t0 = time.monotonic()
                            data = await loop.run_in_executor(self._scheduler._executor, self._scheduler._slow.collect)
                            elapsed = round(time.monotonic() - t0, 1)
                            await self._send_lane_event("slow_lane_data", {
                                "device_id": self.device_id,
                                "data": data,
                                "collection_time_sec": elapsed,
                                "timestamp": time.time(),
                            })
                        else:
                            await self.send_inventory()
                    elif command == "EXECUTE_PATCH":
                        lane = payload.get("lane", "fast")
                        await self.run_patch(payload.get("patch_id"), lane=lane, initiated_by=payload.get("initiated_by"))
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
                    elif command == "HEALTH_CHECK":
                        await self.run_health_check(payload)
                    elif command == "GET_SYSTEM_INFO":
                        await self.send_system_info()
                    elif command == "CONFIG_UPDATE":
                        new_cfg = payload.get("config", {})
                        if new_cfg:
                            logger.info(f"Applying remote config update: {new_cfg}")
                            
                            self.config.update(new_cfg)
                            self._persist_config()
                            
                            if "log_level" in new_cfg:
                                self._set_log_level()
                            
                            # Update lane scheduler intervals if changed
                            if self._scheduler:
                                self._scheduler.update_intervals(
                                    fast=new_cfg.get("fast_lane_interval"),
                                    slow=new_cfg.get("slow_lane_interval"),
                                    fast_concurrency=new_cfg.get("fast_lane_concurrency"),
                                    slow_concurrency=new_cfg.get("slow_lane_concurrency"),
                                )
                            
                            # If heartbeat interval changed, the loop will adapt on next sleep
                            # as it reads from self.config each iteration
                            logger.info("Agent configuration updated from server.")
                    elif command == "UPDATE_AGENT":
                        await self.run_self_update(payload)
                    elif command == "KEY_ROTATED":
                        # Task 11.7 — server rotated our API key
                        new_key = payload.get("new_api_key", "")
                        if new_key:
                            logger.info("Received KEY_ROTATED command — updating api_key in config.yaml.")
                            self.config["api_key"] = new_key
                            self._persist_config()
                            logger.info(
                                "API key updated. Reconnecting with new key after current session ends."
                            )
                            # Signal the connect loop to reconnect so WS auth uses the new key
                            self._connected = False
                        else:
                            logger.warning("KEY_ROTATED payload missing new_api_key — ignoring.")
                    else:
                        logger.warning(f"Unknown command: {command}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except Exception:
            pass  # Connection closed; connect() handles reconnection

    @trace
    async def run_health_check(self, payload: dict):
        """
        Report current resource metrics immediately to allow the server 
        to perform pre-deployment safety checks.
        """
        logger.info("Running pre-flight health check...")
        try:
            cpu = psutil.cpu_percent(interval=1)  # 1s sample for accuracy
            mem = psutil.virtual_memory().percent
            disk = self._disk_usage()
            
            await self.send_json({
                "event": "health_check_result",
                "payload": {
                    "device_id": self.device_id,
                    "request_id": payload.get("request_id"),
                    "cpu_usage": cpu,
                    "ram_usage": mem,
                    "disk_usage": disk,
                    "status": "healthy" if (cpu < 80 and mem < 90) else "busy",
                    "timestamp": time.time()
                }
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    @trace
    async def run_self_update(self, payload: dict):
        """
        Download and apply agent update from server.
        Expected payload: { "download_url": "...", "version": "...", "checksum": "..." }
        """
        download_url = payload.get("download_url")
        target_version = payload.get("version", "unknown")
        expected_checksum = payload.get("checksum")

        if not download_url:
            logger.error("UPDATE_AGENT: no download_url provided")
            return

        logger.info(f"Starting self-update to version {target_version} from {download_url}")
        await self.send_json({
            "event": "update_progress",
            "payload": {"device_id": self.device_id, "status": "downloading", "version": target_version}
        })

        try:
            import hashlib
            import subprocess
            import sys
            import tempfile

            if _AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url, headers=self._rest_headers(), ssl=False) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"Download failed: HTTP {resp.status}")
                        update_data = await resp.read()
            else:
                raise RuntimeError("aiohttp required for self-update")

            # Verify checksum if provided
            if expected_checksum:
                actual = hashlib.sha256(update_data).hexdigest()
                if actual != expected_checksum:
                    raise RuntimeError(f"Checksum mismatch: expected {expected_checksum}, got {actual}")

            # Write update package to temp file
            update_path = os.path.join(tempfile.gettempdir(), f"patchguard-agent-{target_version}.tar.gz")
            with open(update_path, "wb") as f:
                f.write(update_data)

            await self.send_json({
                "event": "update_progress",
                "payload": {"device_id": self.device_id, "status": "applying", "version": target_version}
            })

            # Extract and restart — platform-dependent
            agent_dir = os.path.dirname(os.path.abspath(__file__))
            if platform.system().lower() == "windows":
                subprocess.Popen(
                    ["powershell", "-Command", f"Expand-Archive -Force '{update_path}' '{agent_dir}'; Start-Process python '{os.path.join(agent_dir, 'agent.py')}'"],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                subprocess.Popen(
                    ["sh", "-c", f"tar -xzf '{update_path}' -C '{agent_dir}' && exec python3 '{os.path.join(agent_dir, 'agent.py')}'"],
                    start_new_session=True,
                )

            await self.send_json({
                "event": "update_progress",
                "payload": {"device_id": self.device_id, "status": "restarting", "version": target_version}
            })
            logger.info(f"Self-update to {target_version} applied. Restarting...")
            self.running = False

        except Exception as e:
            logger.error(f"Self-update failed: {e}")
            await self.send_json({
                "event": "update_progress",
                "payload": {"device_id": self.device_id, "status": "failed", "error": str(e), "version": target_version}
            })

    @trace
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

    @trace
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

    @trace
    async def run_patch(self, patch_id: str, lane: str = "fast", initiated_by: str = ""):
        if not patch_id:
            return
        logger.info(f"Installing patch {patch_id} via {lane} lane...")

        # Emit start event
        await self.send_json({
            "event": "patch_install_start",
            "payload": {
                "device_id": self.device_id,
                "patch_id": patch_id,
                "lane": lane,
                "initiated_by": initiated_by,
            }
        })

        t0 = time.time()
        try:
            success = self.plugin.install_patch(patch_id)
        except Exception as e:
            logger.error(f"Patch install failed: {e}")
            success = False
        duration_ms = int((time.time() - t0) * 1000)

        result_status = "completed" if success else "failed"
        await self.send_json({
            "event": "patch_install_result",
            "payload": {
                "device_id": self.device_id,
                "patch_id": patch_id,
                "status": result_status,
                "lane": lane,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
            }
        })
        logger.info(f"Patch {patch_id} [{lane}]: {result_status} in {duration_ms}ms")

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
        if self._scheduler:
            self._scheduler.stop()


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
