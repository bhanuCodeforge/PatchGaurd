import os
import subprocess
import platform
import shutil
from typing import List, Dict, Any
from .base import OSPlugin

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
        return {
            "os_family": "windows",
            "os_name": "Windows",
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "package_manager": "wusa",
        }

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

    def install_patch(self, patch_id: str) -> bool:
        try:
            # Simplified mock: In production, this would use a URL to download a .msu file
            # then run: wusa.exe <path_to_msu> /quiet /norestart
            print(f"Windows install: wusa /quiet {patch_id}")
            return True
        except Exception:
            return False

    def reboot(self) -> bool:
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
            return True
        except Exception:
            return False
