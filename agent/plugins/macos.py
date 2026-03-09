import subprocess
import platform
from typing import List, Dict, Any
from .base import OSPlugin
from logging_utils import trace

class MacOSPlugin(OSPlugin):
    """
    macOS-specific plugin using the softwareupdate CLI.
    """

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "os_family": "macos",
            "os_name": "macOS",
            "os_version": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "package_manager": "softwareupdate",
        }

    @trace
    def scan_patches(self) -> List[Dict[str, Any]]:
        patches = []
        try:
            # softwareupdate -l --no-scan
            res = subprocess.run(["softwareupdate", "-l"], capture_output=True, text=True)
            # Logic to parse the softwareupdate output...
            for line in res.stdout.splitlines():
                if line.startswith("* "):
                    pkg = line.split()[1]
                    patches.append({
                        "vendor_id": pkg,
                        "title": pkg,
                        "severity": "medium",
                        "installed": False,
                        "vendor": "apple"
                    })
        except Exception as e:
            print(f"macOS scan error: {e}")
        return patches

    @trace
    def install_patch(self, patch_id: str) -> bool:
        try:
            res = subprocess.run(["softwareupdate", "-i", patch_id], check=True)
            return res.returncode == 0
        except Exception:
            return False

    @trace
    def get_inventory(self) -> Dict[str, Any]:
        """Collect basic inventory (network, storage). Heavy collection handled by slow-lane."""
        import psutil, socket
        inventory: Dict[str, Any] = {"apps": [], "network": [], "storage": []}
        try:
            for name, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET:
                        inventory["network"].append({"interface": name, "ip": snic.address, "netmask": snic.netmask})
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    inventory["storage"].append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent})
                except Exception:
                    continue
        except Exception as e:
            print(f"macOS inventory error: {e}")
        return inventory

    @trace
    def reboot(self) -> bool:
        try:
            # osascript -e 'tell app "System Events" to restart'
            subprocess.run(["shutdown", "-r", "now"], check=True)
            return True
        except Exception:
            return False
