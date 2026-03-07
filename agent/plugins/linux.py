import os
import subprocess
import platform
import shutil
from typing import List, Dict, Any
from .base import OSPlugin
from logging_utils import trace

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

    @trace
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
                        patches.append({
                            "vendor_id": pkg,
                            "title": pkg,
                            "version": ver,
                            "severity": "medium",
                            "installed": False,
                            "vendor": "ubuntu" if "ubuntu" in self.get_system_info()["os_name"].lower() else "debian"
                        })
            elif self.mgr in ["dnf", "yum"]:
                res = subprocess.run([self.mgr, "check-update"], capture_output=True, text=True)
                # Parse dnf output...
                pass
        except Exception as e:
            print(f"Linux scan error: {e}")
        return patches

    @trace
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

    @trace
    def get_inventory(self) -> Dict[str, Any]:
        inventory = {
            "apps": [],
            "network": [],
            "storage": [],
        }
        try:
            if self.mgr == "apt":
                # dpkg-query logic
                cmd = ["dpkg-query", "-W", "-f=${Package};${Version};${Maintainer}\n"]
                res = subprocess.run(cmd, capture_output=True, text=True)
                for line in res.stdout.splitlines():
                    parts = line.split(";")
                    if len(parts) >= 3:
                        inventory["apps"].append({
                            "name": parts[0],
                            "version": parts[1],
                            "publisher": parts[2]
                        })
            elif self.mgr in ["dnf", "yum"]:
                # rpm logic
                pass

            # Network info (psutil is cross-platform)
            import psutil, socket
            for name, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET:
                        inventory["network"].append({
                            "interface": name,
                            "ip": snic.address,
                            "netmask": snic.netmask
                        })
        except Exception as e:
            print(f"Linux inventory error: {e}")
        return inventory

    @trace
    def reboot(self) -> bool:
        try:
            subprocess.run(["reboot"], check=True)
            return True
        except Exception:
            return False
