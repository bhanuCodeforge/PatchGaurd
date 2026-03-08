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
        """
        Collects detailed Windows inventory:
        - Installed Applications (Registry-based)
        - Network Adapters
        - Logical Disks
        """
        inventory = {
            "apps": [],
            "network": [],
            "storage": [],
        }

        if not self.powershell:
            return inventory

        try:
            # 1. Get Installed Apps (Simplified logic using PowerShell)
            # This looks at: HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall
            script = """
            $paths = @("HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*", 
                       "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*")
            Get-ItemProperty $paths | 
                Where-Object { $_.DisplayName -ne $null } | 
                Select-Object DisplayName, DisplayVersion, Publisher, InstallDate | 
                ConvertTo-Json -Compress
            """
            res = subprocess.run(
                [self.powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=30
            )
            if res.returncode == 0 and res.stdout.strip():
                import json as _json
                apps = _json.loads(res.stdout)
                if isinstance(apps, dict): apps = [apps]
                for a in apps:
                    inventory["apps"].append({
                        "name": a.get("DisplayName"),
                        "version": a.get("DisplayVersion"),
                        "publisher": a.get("Publisher"),
                        "install_date": a.get("InstallDate")
                    })

            # 2. Network Info
            import psutil
            wifi_info = {}
            if self.powershell:
                try:
                    res = subprocess.run(
                        [self.powershell, "-NoProfile", "-Command", "netsh wlan show interfaces | ConvertFrom-StringData | ConvertTo-Json"],
                        capture_output=True, text=True, timeout=10
                    )
                    # netsh output is tricky to JSON-ify directly this way, 
                    # but we can try to extract basic SSID/Signal
                    out = res.stdout.strip()
                    if "SSID" in out:
                        for line in out.split('\n'):
                            if "SSID" in line and ":" in line: wifi_info["ssid"] = line.split(":", 1)[1].strip()
                            if "Signal" in line and ":" in line: wifi_info["signal"] = line.split(":", 1)[1].strip()
                except: pass

            for name, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET:
                        inventory["network"].append({
                            "interface": name,
                            "ip": snic.address,
                            "netmask": snic.netmask,
                            "is_wifi": "Wi-Fi" in name or "Wireless" in name,
                            **(wifi_info if ("Wi-Fi" in name or "Wireless" in name) else {})
                        })

            # 3. Storage (All Disks)
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and 'cdrom' in part.opts: continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    inventory["storage"].append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except: continue

            # 4. Battery
            battery = psutil.sensors_battery()
            if battery:
                inventory["battery"] = {
                    "percent": battery.percent,
                    "secsleft": battery.secsleft,
                    "power_plugged": battery.power_plugged
                }

            # 5. Last Login
            if self.powershell:
                try:
                    res = subprocess.run(
                        [self.powershell, "-NoProfile", "-Command", "Get-LocalUser | Sort-Object LastLogon -Descending | Select -First 1 | Select DisplayName, LastLogon | ConvertTo-Json"],
                        capture_output=True, text=True, timeout=10
                    )
                    if res.returncode == 0:
                        inventory["last_login"] = _json.loads(res.stdout)
                except: pass

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
