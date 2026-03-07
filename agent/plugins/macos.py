import os
import subprocess
import platform
import shutil
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
        inventory = {
            "apps": [],
            "network": [],
            "storage": [],
        }
        try:
            # simple app list using system_profiler
            cmd = ["system_profiler", "SPApplicationsDataType", "-json"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.status == 0:
                import json as _json
                data = _json.loads(res.stdout)
                apps = data.get("SPApplicationsDataType", [])
                for a in apps:
                    inventory["apps"].append({
                        "name": a.get("_name"),
                        "version": a.get("version"),
                        "publisher": a.get("obtained_from", "unknown")
                    })
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
