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
        import json
        
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // (24 * 3600))
        hours = int((uptime_seconds % (24 * 3600)) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        wmi_data = {}
        if self.powershell:
            script = """
            $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
            $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
            $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
            $bios = Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue
            $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
            [PSCustomObject]@{
                ComputerName = $cs.Name
                UserName = $cs.PrimaryOwnerName
                OSCaption = $os.Caption
                OSVersion = $os.Version
                OSBuild = $os.BuildNumber
                OSArchitecture = $os.OSArchitecture
                InstallDate = if($os.InstallDate){$os.InstallDate.ToString("yyyy-MM-dd")}else{""}
                LastBootTime = if($os.LastBootUpTime){$os.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss")}else{""}
                CPU = $cpu.Name
                CPUCores = $cpu.NumberOfCores
                CPULogical = $cpu.NumberOfLogicalProcessors
                RAM_GB = [math]::Round($cs.TotalPhysicalMemory/1GB, 2)
                DiskFree_GB = [math]::Round($disk.FreeSpace/1GB, 2)
                DiskUsed_GB = [math]::Round(($disk.Size - $disk.FreeSpace)/1GB, 2)
                BIOSVersion = $bios.SMBIOSBIOSVersion
                BIOSDate = if($bios.ReleaseDate){$bios.ReleaseDate.ToString("yyyy-MM-dd")}else{""}
                TimeZone = (Get-TimeZone).Id
                SerialNumber = $bios.SerialNumber
            } | ConvertTo-Json -Compress
            """
            try:
                res = subprocess.run(
                    [self.powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True, text=True, timeout=15
                )
                if res.returncode == 0 and res.stdout.strip():
                    wmi_data = json.loads(res.stdout)
            except Exception:
                pass

        info = {
            "os_family": "windows",
            "os_name": "Windows",
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "kernel": platform.version(),
            "serial_number": wmi_data.get("SerialNumber", "N/A"),
            "package_manager": "wusa",
            "cpu_count": psutil.cpu_count(),
            "total_ram": psutil.virtual_memory().total,
            "total_disk": psutil.disk_usage('C:\\').total,
            "uptime": uptime_str,
        }
        
        info.update(wmi_data)
        return info

    @trace
    def scan_patches(self) -> List[Dict[str, Any]]:
        """
        Returns missing updates via Windows Update Agent API, 
        plus installed hotfixes via Get-HotFix.
        """
        patches = []
        if not self.powershell:
            return patches
            
        # 1. Get MISSING updates via COM object
        missing_script = """
        $updateSession = New-Object -ComObject Microsoft.Update.Session
        $updateSearcher = $updateSession.CreateUpdateSearcher()
        $searchResult = $updateSearcher.Search("IsInstalled=0 and Type='Software'")
        $searchResult.Updates | ForEach-Object {
            [PSCustomObject]@{
                KB = if ($_.KBArticleIDs.Count -gt 0) { "KB" + $_.KBArticleIDs[0] } else { "" }
                Title = $_.Title
                Severity = switch ($_.MsrcSeverity) {
                    "Critical"  { "critical" }
                    "Important" { "high" }
                    "Moderate"  { "medium" }
                    "Low"       { "low" }
                    default     { "medium" }
                }
                UpdateID = $_.Identity.UpdateID
            }
        } | ConvertTo-Json -Compress
        """
        try:
            res = subprocess.run(
                [self.powershell, "-NoProfile", "-NonInteractive", "-Command", missing_script],
                capture_output=True, text=True, timeout=120
            )
            if res.returncode == 0 and res.stdout.strip():
                import json as _json
                data = _json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    vendor_id = item.get("KB") or item.get("UpdateID")
                    if not vendor_id: continue
                    patches.append({
                        "vendor_id": str(vendor_id),
                        "title": item.get("Title", vendor_id),
                        "installed": False,
                        "severity": item.get("Severity", "medium"),
                        "vendor": "microsoft",
                        "package_name": str(vendor_id),
                    })
        except Exception as e:
            print(f"Windows missing updates scan error: {e}")

        # 2. Get INSTALLED hotfixes for completeness
        try:
            installed_script = "Get-HotFix | Select-Object HotFixID, Description | ConvertTo-Json -Compress"
            res = subprocess.run(
                [self.powershell, "-NoProfile", "-NonInteractive", "-Command", installed_script],
                capture_output=True, text=True, timeout=60
            )
            if res.returncode == 0 and res.stdout.strip():
                import json as _json
                data = _json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    hotfix_id = (item.get("HotFixID") or "").strip()
                    if not hotfix_id: continue
                    patches.append({
                        "vendor_id": hotfix_id,
                        "title": (item.get("Description") or hotfix_id).strip(),
                        "installed": True,
                        "severity": "medium",
                        "vendor": "microsoft",
                        "package_name": hotfix_id,
                    })
        except Exception as e:
            print(f"Windows installed hotfix scan error: {e}")
            
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
