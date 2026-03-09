import os
import subprocess
import platform
import shutil
import socket
from typing import List, Dict, Any
from .base import OSPlugin
from logging_utils import trace

class WindowsPlugin(OSPlugin):
    """
    Windows-specific plugin using PowerShell and wusa.exe (Windows Update Standalone Installer).
    """

    def __init__(self):
        self.powershell = self._detect_powershell()

    def _detect_powershell(self) -> str:
        if shutil.which("pwsh"):
            return "pwsh"
        elif shutil.which("powershell"):
            return "powershell"
        return ""

    def get_system_info(self) -> Dict[str, Any]:
        import psutil
        import time
        
        # Calculate uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // (24 * 3600))
        hours = int((uptime_seconds % (24 * 3600)) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        serial = "N/A"
        try:
            if self.powershell:
                res = subprocess.run(
                    [self.powershell, "-NoProfile", "-Command", "(Get-CimInstance Win32_Bios).SerialNumber"],
                    capture_output=True, text=True, timeout=10
                )
                if res.returncode == 0:
                    serial = res.stdout.strip()
        except: pass

        return {
            "os_family": "windows",
            "os_name": "Windows",
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "serial_number": serial,
            "package_manager": "wusa",
            "cpu_count": psutil.cpu_count(),
            "total_ram": psutil.virtual_memory().total,
            "total_disk": psutil.disk_usage('C:\\').total,
            "uptime": uptime_str,
        }

    @trace
    def scan_patches(self) -> List[Dict[str, Any]]:
        """
        Returns installed hotfixes via Get-HotFix, formatted for process_scan_results.
        Each entry uses: vendor_id, title, installed, severity, vendor.
        """
        patches = []
        if not self.powershell:
            return patches
        try:
            script = "Get-HotFix | Select-Object HotFixID, Description | ConvertTo-Json -Compress"
            res = subprocess.run(
                [self.powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=60
            )
            if res.returncode == 0 and res.stdout.strip():
                import json as _json
                data = _json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    hotfix_id = (item.get("HotFixID") or "").strip()
                    if not hotfix_id:
                        continue
                    patches.append({
                        "vendor_id": hotfix_id,
                        "title": (item.get("Description") or hotfix_id).strip(),
                        "installed": True,
                        "severity": "medium",
                        "vendor": "microsoft",
                        "package_name": hotfix_id,
                    })
        except Exception as e:
            print(f"Windows scan error: {e}")
        return patches

    @trace
    def install_patch(self, patch_id: str) -> bool:
        try:
            # Simplified mock: In production, this would use a URL to download a .msu file
            # then run: wusa.exe <path_to_msu> /quiet /norestart
            print(f"Windows install: wusa /quiet {patch_id}")
            return True
        except Exception:
            return False

    @trace
    def get_inventory(self) -> Dict[str, Any]:
        """Collect basic inventory (network, storage, battery). Heavy collection handled by slow-lane."""
        import psutil
        inventory: Dict[str, Any] = {"apps": [], "network": [], "storage": []}
        try:
            for name, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET:
                        inventory["network"].append({"interface": name, "ip": snic.address, "netmask": snic.netmask})
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and 'cdrom' in part.opts:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    inventory["storage"].append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent})
                except Exception:
                    continue
            battery = psutil.sensors_battery()
            if battery:
                inventory["battery"] = {"percent": battery.percent, "secsleft": battery.secsleft, "power_plugged": battery.power_plugged}
        except Exception as e:
            print(f"Windows inventory error: {e}")
        return inventory

    @trace
    def reboot(self) -> bool:
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
            return True
        except Exception:
            return False
