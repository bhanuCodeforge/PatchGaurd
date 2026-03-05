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
        patches = []
        try:
            # Using PowerShell to list missing updates (this is a simplified mock)
            # In real usage, this would call Windows Update API or WSUS.
            cmd = ["Get-HotFix", "|", "Select-Object", "HotFixID", "Description", "InstalledOn"]
            res = subprocess.run([self.powershell, "-Command", " ".join(cmd)], capture_output=True, text=True)
            for line in res.stdout.splitlines()[2:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 1:
                        patches.append({"id": parts[0], "name": f"KB{parts[0]}", "severity": "important"})
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
