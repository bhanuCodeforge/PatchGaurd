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
        import psutil
        import time
        import socket
        
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // (24 * 3600))
        hours = int((uptime_seconds % (24 * 3600)) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
        
        disk = psutil.disk_usage('/')
        
        cpu_model = "Unknown"
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":")[1].strip()
                        break
        except Exception:
            pass

        return {
            "os_family": "linux",
            "os_name": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "package_manager": self.mgr,
            "cpu_count": psutil.cpu_count(),
            "total_ram": psutil.virtual_memory().total,
            "total_disk": disk.total,
            "uptime": uptime_str,
            "ComputerName": socket.gethostname(),
            "UserName": "root",
            "OSCaption": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
            "OSVersion": platform.release(),
            "OSBuild": platform.version(),
            "OSArchitecture": platform.machine(),
            "CPU": cpu_model,
            "CPUCores": psutil.cpu_count(logical=False),
            "CPULogical": psutil.cpu_count(logical=True),
            "RAM_GB": round(psutil.virtual_memory().total / (1024**3), 2),
            "DiskFree_GB": round(disk.free / (1024**3), 2),
            "DiskUsed_GB": round((disk.total - disk.free) / (1024**3), 2),
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
            print(f"Linux inventory error: {e}")
        return inventory

    @trace
    def reboot(self) -> bool:
        try:
            subprocess.run(["reboot"], check=True)
            return True
        except Exception:
            return False
