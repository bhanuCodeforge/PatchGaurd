import os
import subprocess
import platform
import shutil
from typing import List, Dict, Any
from .base import OSPlugin

class LinuxPlugin(OSPlugin):
    """
    Linux-specific plugin supporting apt (Debian/Ubuntu) and yum/dnf (RHEL/CentOS).
    """

    def __init__(self):
        self.mgr = self._detect_manager()

    def _detect_manager(self) -> str:
        if shutil.which("apt-get"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
        elif shutil.which("yum"):
            return "yum"
        return "unknown"

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "os_family": "linux",
            "os_name": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "package_manager": self.mgr,
        }

    def scan_patches(self) -> List[Dict[str, Any]]:
        patches = []
        try:
            if self.mgr == "apt":
                # apt-get update && apt-get -s upgrade
                subprocess.run(["apt-get", "update"], check=False, capture_output=True)
                res = subprocess.run(["apt-get", "-s", "upgrade"], capture_output=True, text=True)
                # Parsing logic placeholder...
                for line in res.stdout.splitlines():
                    if line.startswith("Inst "): # Inst package (version)
                        pkg = line.split()[1]
                        ver = line.split()[2].strip("()")
                        patches.append({"id": pkg, "name": pkg, "version": ver, "severity": "medium"})
            elif self.mgr in ["dnf", "yum"]:
                res = subprocess.run([self.mgr, "check-update"], capture_output=True, text=True)
                # Parse dnf output...
                pass
        except Exception as e:
            print(f"Linux scan error: {e}")
        return patches

    def install_patch(self, patch_id: str) -> bool:
        try:
            if self.mgr == "apt":
                res = subprocess.run(["apt-get", "install", "-y", patch_id], check=True)
                return res.returncode == 0
            elif self.mgr in ["dnf", "yum"]:
                res = subprocess.run([self.mgr, "install", "-y", patch_id], check=True)
                return res.returncode == 0
        except Exception:
            return False
        return False

    def reboot(self) -> bool:
        try:
            subprocess.run(["reboot"], check=True)
            return True
        except Exception:
            return False
