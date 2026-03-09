"""
Slow Lane Collector — heavy inventory & patch data (every ~15 minutes).

Cross-platform: Windows · Linux/Ubuntu · macOS
Runs expensive subprocess calls (PowerShell, dpkg, softwareupdate, etc.)
in a background thread to avoid blocking the async event loop.
"""

import json
import os
import platform
import shutil
import subprocess
import time
import logging
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PatchAgent.SlowLane")

OS = platform.system()  # "Windows" | "Linux" | "Darwin"


# ═══════════════════════════════════════════════════════════════
# SHARED UTILS
# ═══════════════════════════════════════════════════════════════

def _run(cmd: list, shell: bool = False, timeout: int = 60) -> Optional[str]:
    """Run a shell command and return stdout, or None on failure."""
    try:
        r = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            timeout=timeout, errors="replace"
        )
        out = r.stdout.strip()
        return out if out else None
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return None
    except Exception:
        return None


def _run_ps(cmd: str, timeout: int = 60) -> Optional[str]:
    """Windows-only: run a PowerShell command."""
    ps = "pwsh" if shutil.which("pwsh") else "powershell"
    return _run([ps, "-NoProfile", "-NonInteractive", "-Command", cmd], timeout=timeout)


def _safe_json(raw: Optional[str]) -> Any:
    """Parse JSON safely; wrap single-object into list."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return [parsed] if isinstance(parsed, dict) else parsed
    except json.JSONDecodeError:
        return None


def _parse_lines(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [l.strip() for l in raw.splitlines() if l.strip()]


# ═══════════════════════════════════════════════════════════════
# WINDOWS SLOW LANE
# ═══════════════════════════════════════════════════════════════

class WindowsSlowCollector:
    """Heavy Windows data: patches, apps, missing updates, drivers, security."""

    def installed_patches(self) -> list:
        cmd = """Get-HotFix |
            Select HotFixID, Description, InstalledBy,
            @{N='InstalledOn';E={if($_.InstalledOn){$_.InstalledOn.ToString("yyyy-MM-dd")}else{"Unknown"}}} |
            Sort InstalledOn -Desc | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def update_history(self) -> list:
        cmd = """
        $s = New-Object -ComObject Microsoft.Update.Session
        $h = $s.CreateUpdateSearcher()
        $c = $h.GetTotalHistoryCount()
        $hist = $h.QueryHistory(0,$c)
        $list = @()
        foreach ($u in $hist) {
            $list += [PSCustomObject]@{
                Title  = $u.Title
                Date   = $u.Date.ToString("yyyy-MM-dd HH:mm:ss")
                Result = switch($u.ResultCode){0{"NotStarted"}1{"InProgress"}2{"Succeeded"}3{"SucceededWithErrors"}4{"Failed"}5{"Aborted"}default{"Unknown"}}
                KB     = if($u.Title -match "KB(\\d+)"){"KB$($matches[1])"}else{""}
            }
        }
        $list | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd, timeout=90)) or []

    def missing_updates(self) -> list:
        cmd = """
        $s = New-Object -ComObject Microsoft.Update.Session
        $r = $s.CreateUpdateSearcher().Search("IsInstalled=0 and Type='Software'")
        $list = @()
        foreach ($u in $r.Updates) {
            $list += [PSCustomObject]@{
                Title    = $u.Title
                KB       = ($u.KBArticleIDs -join ",")
                Severity = if($u.MsrcSeverity){$u.MsrcSeverity}else{"None"}
                Size_MB  = [math]::Round($u.MaxDownloadSize/1MB,2)
                RebootRequired = $u.RebootRequired
            }
        }
        $list | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd, timeout=120)) or []

    def defender_status(self) -> dict:
        cmd = """
        try {
            $s = Get-MpComputerStatus
            [PSCustomObject]@{
                AntivirusEnabled   = $s.AntivirusEnabled
                RealTimeProtection = $s.RealTimeProtectionEnabled
                SignatureVersion   = $s.AntivirusSignatureVersion
                SignatureAge_days  = $s.AntivirusSignatureAge
                LastFullScan       = if($s.FullScanEndTime){$s.FullScanEndTime.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}
                LastQuickScan      = if($s.QuickScanEndTime){$s.QuickScanEndTime.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}
                DefenderVersion    = $s.AMProductVersion
            } | ConvertTo-Json
        } catch { @{} | ConvertTo-Json }"""
        r = _safe_json(_run_ps(cmd))
        return r[0] if isinstance(r, list) and r else {}

    def registry_apps(self) -> list:
        cmd = r"""
        $paths=@("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
                 "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                 "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*")
        $apps = foreach($p in $paths){
            Get-ItemProperty $p -EA SilentlyContinue |
            Where{$_.DisplayName} |
            Select DisplayName,DisplayVersion,Publisher,InstallDate,
                @{N='Size_MB';E={[math]::Round($_.EstimatedSize/1024,2)}}
        }
        $apps | Sort DisplayName -Unique | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def store_apps(self) -> list:
        cmd = "Get-AppxPackage | Select Name,Version,Publisher,Architecture | Sort Name | ConvertTo-Json"
        return _safe_json(_run_ps(cmd)) or []

    def drivers(self) -> list:
        cmd = """Get-WmiObject Win32_PnPSignedDriver | Where{$_.DeviceName} |
            Select DeviceName,DriverVersion,Manufacturer,DeviceClass,IsSigned | Sort DeviceClass,DeviceName | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd, timeout=90)) or []

    def services(self) -> list:
        cmd = "Get-Service | Select Name,DisplayName,Status,StartType | Sort Status,DisplayName | ConvertTo-Json"
        return _safe_json(_run_ps(cmd)) or []

    def firewall(self) -> list:
        cmd = "Get-NetFirewallProfile | Select Name,Enabled,DefaultInboundAction,DefaultOutboundAction | ConvertTo-Json"
        return _safe_json(_run_ps(cmd)) or []

    def scheduled_tasks(self) -> list:
        cmd = """Get-ScheduledTask | Where{$_.State -ne "Disabled"} |
            Select TaskName,TaskPath,State,
            @{N='RunAs';E={$_.Principal.UserId}} | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd, timeout=90)) or []

    def local_users(self) -> list:
        cmd = """Get-LocalUser | Select Name,Enabled,FullName,
            @{N='LastLogon';E={if($_.LastLogon){$_.LastLogon.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}}} | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def event_log_errors(self) -> list:
        cmd = """Get-EventLog -LogName System -EntryType Error,Warning -Newest 50 |
            Select @{N='Time';E={$_.TimeGenerated.ToString("yyyy-MM-dd HH:mm:ss")}},
            Source,EventID,@{N='EntryType';E={$_.EntryType.ToString()}},
            @{N='Message';E={$_.Message -replace "`r`n"," "}} | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd, timeout=60)) or []

    def windows_features(self) -> list:
        cmd = "Get-WindowsOptionalFeature -Online | Where{$_.State -eq 'Enabled'} | Select FeatureName,State | Sort FeatureName | ConvertTo-Json"
        return _safe_json(_run_ps(cmd, timeout=90)) or []

    def startup_programs(self) -> list:
        cmd = r"""
        $list=@()
        $reg=@("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
               "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        foreach($p in $reg){
            if(Test-Path $p){
                (Get-ItemProperty $p).PSObject.Properties|Where{$_.Name -notlike "PS*"}|ForEach{
                    $list+=[PSCustomObject]@{Name=$_.Name;Command=$_.Value;Source=$p}
                }
            }
        }
        $list | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def disk_health(self) -> list:
        cmd = """Get-PhysicalDisk | Select FriendlyName,MediaType,HealthStatus,OperationalStatus,
            @{N='Size_GB';E={[math]::Round($_.Size/1GB,2)}},BusType | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def network_info(self) -> list:
        cmd = """Get-NetIPConfiguration | Select InterfaceAlias,
            @{N='IPv4';E={$_.IPv4Address.IPAddress -join ", "}},
            @{N='Gateway';E={$_.IPv4DefaultGateway.NextHop -join ", "}},
            @{N='DNS';E={$_.DNSServer.ServerAddresses -join ", "}} | ConvertTo-Json"""
        return _safe_json(_run_ps(cmd)) or []

    def collect(self) -> Dict[str, Any]:
        logger.info("Windows slow-lane collection starting...")
        data = {}
        collectors = [
            ("installed_patches", self.installed_patches),
            ("update_history", self.update_history),
            ("missing_updates", self.missing_updates),
            ("defender_status", self.defender_status),
            ("registry_apps", self.registry_apps),
            ("store_apps", self.store_apps),
            ("drivers", self.drivers),
            ("services", self.services),
            ("firewall", self.firewall),
            ("scheduled_tasks", self.scheduled_tasks),
            ("local_users", self.local_users),
            ("event_log_errors", self.event_log_errors),
            ("windows_features", self.windows_features),
            ("startup_programs", self.startup_programs),
            ("disk_health", self.disk_health),
            ("network_info", self.network_info),
        ]
        for key, fn in collectors:
            try:
                logger.debug(f"  Collecting {key}...")
                data[key] = fn()
            except Exception as e:
                logger.warning(f"  {key} failed: {e}")
                data[key] = []
        logger.info(f"Windows slow-lane collection complete ({len(data)} sections)")
        return data


# ═══════════════════════════════════════════════════════════════
# LINUX / UBUNTU SLOW LANE
# ═══════════════════════════════════════════════════════════════

class LinuxSlowCollector:
    """Heavy Linux data: packages, security updates, patch history, services, etc."""

    def installed_packages(self) -> list:
        if shutil.which("dpkg"):
            raw = _run(["dpkg-query", "-W",
                        "-f=${Package}\t${Version}\t${Architecture}\t${Status}\n"])
            if raw:
                pkgs = []
                for line in raw.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        pkgs.append({"name": parts[0], "version": parts[1],
                                     "arch": parts[2],
                                     "status": parts[3] if len(parts) > 3 else "unknown"})
                return pkgs
        if shutil.which("rpm"):
            raw = _run(["rpm", "-qa", "--queryformat",
                        "%{NAME}\t%{VERSION}\t%{ARCH}\t%{INSTALLTIME:date}\n"])
            if raw:
                pkgs = []
                for line in raw.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        pkgs.append({"name": parts[0], "version": parts[1],
                                     "arch": parts[2],
                                     "install_date": parts[3] if len(parts) > 3 else ""})
                return pkgs
        return []

    def security_updates(self) -> list:
        if shutil.which("apt"):
            raw = _run(["apt", "list", "--upgradable"], timeout=60)
            if raw:
                pkgs = []
                for line in raw.splitlines()[1:]:
                    if line:
                        parts = line.split()
                        pkgs.append({"package": parts[0].split("/")[0] if parts else line,
                                     "available_version": parts[1] if len(parts) > 1 else ""})
                return pkgs
        if shutil.which("dnf"):
            raw = _run(["dnf", "check-update", "--security"], timeout=90)
            if raw:
                pkgs = []
                for line in raw.splitlines():
                    if line and not line.startswith(("Last", "Security", "Added")):
                        parts = line.split()
                        if len(parts) >= 2:
                            pkgs.append({"package": parts[0], "available_version": parts[1]})
                return pkgs
        return []

    def patch_history(self) -> list:
        results = []
        for log_path in sorted(Path("/var/log").glob("dpkg.log*"), reverse=True)[:3]:
            try:
                for line in log_path.read_text(errors="replace").splitlines():
                    if "install" in line or "upgrade" in line:
                        results.append(line.strip())
            except (PermissionError, OSError):
                pass
        apt_history = Path("/var/log/apt/history.log")
        if apt_history.exists():
            try:
                for line in apt_history.read_text(errors="replace").splitlines():
                    if line.startswith(("Start-Date", "Upgrade:", "Install:", "End-Date")):
                        results.append(line.strip())
            except (PermissionError, OSError):
                pass
        if shutil.which("dnf"):
            raw = _run(["dnf", "history", "list", "last-20"], timeout=30)
            if raw:
                results.extend(raw.splitlines())
        return results[-200:]

    def kernel_patches(self) -> list:
        results = []
        if shutil.which("dpkg"):
            raw = _run(["dpkg", "-l", "linux-image-*"])
            if raw:
                for line in raw.splitlines():
                    if line.startswith("ii"):
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({"package": parts[1], "version": parts[2], "status": "installed"})
        elif shutil.which("rpm"):
            raw = _run(["rpm", "-qa", "kernel"])
            if raw:
                results = [{"package": k, "version": ""} for k in raw.splitlines()]
        cur = _run(["uname", "-r"])
        return [{"running_kernel": cur}] + results

    def services(self) -> list:
        if not shutil.which("systemctl"):
            return []
        raw = _run(["systemctl", "list-units", "--type=service",
                     "--all", "--no-pager", "--no-legend"], timeout=30)
        if not raw:
            return []
        services = []
        for line in raw.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 4:
                services.append({"unit": parts[0], "load": parts[1],
                                 "active": parts[2], "sub": parts[3],
                                 "description": parts[4] if len(parts) > 4 else ""})
        return services

    def running_processes(self) -> list:
        raw = _run(["ps", "aux", "--sort=-%mem"])
        if not raw:
            return []
        procs = []
        for line in raw.splitlines()[1:51]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                procs.append({"user": parts[0], "pid": parts[1],
                              "cpu_pct": parts[2], "mem_pct": parts[3],
                              "command": parts[10]})
        return procs

    def network_info(self) -> list:
        results = []
        raw = _run(["ip", "-brief", "addr"])
        if raw:
            for line in raw.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    results.append({"interface": parts[0], "state": parts[1],
                                    "addresses": parts[2:] if len(parts) > 2 else []})
        gw = _run(["ip", "route", "show", "default"])
        if gw:
            results.append({"default_route": gw})
        return results

    def open_ports(self) -> list:
        if shutil.which("ss"):
            raw = _run(["ss", "-tlnup"])
        elif shutil.which("netstat"):
            raw = _run(["netstat", "-tlnup"])
        else:
            return []
        return _parse_lines(raw)

    def firewall(self) -> dict:
        result = {}
        if shutil.which("ufw"):
            result["ufw"] = _run(["ufw", "status", "verbose"])
        if shutil.which("iptables"):
            result["iptables_rules"] = _parse_lines(_run(["iptables", "-L", "-n", "--line-numbers"]))
        if shutil.which("firewall-cmd"):
            result["firewalld_zones"] = _run(["firewall-cmd", "--list-all"])
        return result

    def disk_health(self) -> list:
        results = []
        raw = _run(["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL", "--json"])
        if raw:
            parsed = _safe_json(raw)
            if parsed:
                results.append({"lsblk": parsed})
        df = _run(["df", "-h", "--output=source,fstype,size,used,avail,pcent,target"])
        if df:
            results.append({"df": _parse_lines(df)})
        return results

    def users(self) -> list:
        users = []
        try:
            for line in Path("/etc/passwd").read_text().splitlines():
                parts = line.split(":")
                if len(parts) >= 7:
                    uid = int(parts[2])
                    if uid >= 1000 or parts[0] == "root":
                        users.append({"username": parts[0], "uid": uid,
                                      "home": parts[5], "shell": parts[6]})
        except (PermissionError, OSError):
            pass
        return users

    def cron_jobs(self) -> list:
        jobs = []
        for path in [Path("/etc/crontab")] + list(Path("/etc/cron.d").glob("*")):
            try:
                jobs.append({"file": str(path), "content": path.read_text(errors="replace")})
            except (PermissionError, OSError):
                pass
        raw = _run(["crontab", "-l"])
        if raw:
            jobs.append({"user_crontab": raw})
        return jobs

    def security_config(self) -> dict:
        result = {}
        if shutil.which("getenforce"):
            result["selinux"] = _run(["getenforce"])
        if shutil.which("apparmor_status") or Path("/sys/kernel/security/apparmor").exists():
            result["apparmor"] = _run(["aa-status", "--json"]) or _run(["apparmor_status"])
        sysctl_keys = ["kernel.randomize_va_space", "net.ipv4.ip_forward"]
        sysctl_vals = {}
        for key in sysctl_keys:
            val = _run(["sysctl", "-n", key])
            if val:
                sysctl_vals[key] = val
        result["sysctl_security"] = sysctl_vals
        return result

    def installed_snaps(self) -> list:
        if not shutil.which("snap"):
            return []
        raw = _run(["snap", "list"])
        if not raw:
            return []
        snaps = []
        for line in raw.splitlines()[1:]:
            parts = line.split(None, 5)
            if len(parts) >= 4:
                snaps.append({"name": parts[0], "version": parts[1],
                              "rev": parts[2], "tracking": parts[3]})
        return snaps

    def flatpaks(self) -> list:
        if not shutil.which("flatpak"):
            return []
        raw = _run(["flatpak", "list", "--columns=name,version,origin,installation"])
        if not raw:
            return []
        apps = []
        for line in raw.splitlines():
            parts = line.split("\t")
            if parts:
                apps.append({"name": parts[0],
                             "version": parts[1] if len(parts) > 1 else ""})
        return apps

    def recent_log_errors(self) -> list:
        if shutil.which("journalctl"):
            raw = _run(["journalctl", "-p", "err", "-n", "50",
                        "--no-pager", "--output=short-iso"], timeout=30)
            return _parse_lines(raw)
        syslog = Path("/var/log/syslog")
        if syslog.exists():
            try:
                lines = syslog.read_text(errors="replace").splitlines()
                return [l for l in lines[-200:] if "error" in l.lower() or "fail" in l.lower()][-50:]
            except (PermissionError, OSError):
                pass
        return []

    def collect(self) -> Dict[str, Any]:
        logger.info("Linux slow-lane collection starting...")
        data = {}
        collectors = [
            ("installed_packages", self.installed_packages),
            ("security_updates", self.security_updates),
            ("patch_history", self.patch_history),
            ("kernel_patches", self.kernel_patches),
            ("services", self.services),
            ("running_processes", self.running_processes),
            ("network_info", self.network_info),
            ("open_ports", self.open_ports),
            ("firewall", self.firewall),
            ("disk_health", self.disk_health),
            ("users", self.users),
            ("cron_jobs", self.cron_jobs),
            ("security_config", self.security_config),
            ("snap_packages", self.installed_snaps),
            ("flatpak_apps", self.flatpaks),
            ("recent_errors", self.recent_log_errors),
        ]
        for key, fn in collectors:
            try:
                logger.debug(f"  Collecting {key}...")
                data[key] = fn()
            except Exception as e:
                logger.warning(f"  {key} failed: {e}")
                data[key] = []
        logger.info(f"Linux slow-lane collection complete ({len(data)} sections)")
        return data


# ═══════════════════════════════════════════════════════════════
# macOS SLOW LANE
# ═══════════════════════════════════════════════════════════════

class MacOSSlowCollector:
    """Heavy macOS data: software updates, homebrew, apps, security configs."""

    def software_updates(self) -> list:
        raw = _run(["softwareupdate", "-l"], timeout=90)
        if not raw:
            return []
        updates = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("*") or line.startswith("-"):
                updates.append({"update": line.lstrip("*- ").strip()})
        return updates

    def update_history(self) -> list:
        hist_path = Path("/Library/Receipts/InstallHistory.plist")
        if not hist_path.exists():
            return []
        raw = _run(["plutil", "-p", str(hist_path)])
        if not raw:
            return []
        history = []
        current = {}
        for line in raw.splitlines():
            line = line.strip()
            if '"displayName"' in line:
                current["name"] = line.split("=>")[-1].strip().strip('"')
            elif '"displayVersion"' in line:
                current["version"] = line.split("=>")[-1].strip().strip('"')
            elif '"date"' in line:
                current["date"] = line.split("=>")[-1].strip().strip('"')
            elif '"processName"' in line:
                current["process"] = line.split("=>")[-1].strip().strip('"')
                if current:
                    history.append(current.copy())
                    current = {}
        return history[-100:]

    def homebrew_packages(self) -> list:
        if not shutil.which("brew"):
            return []
        packages = []
        raw = _run(["brew", "list", "--versions"], timeout=60)
        if raw:
            for line in raw.splitlines():
                parts = line.split()
                packages.append({"name": parts[0], "versions": parts[1:], "type": "formula"})
        raw_casks = _run(["brew", "list", "--cask", "--versions"], timeout=60)
        if raw_casks:
            for line in raw_casks.splitlines():
                parts = line.split()
                packages.append({"name": parts[0], "versions": parts[1:], "type": "cask"})
        return packages

    def homebrew_outdated(self) -> list:
        if not shutil.which("brew"):
            return []
        raw = _run(["brew", "outdated", "--verbose"], timeout=60)
        if not raw:
            return []
        outdated = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                outdated.append({"name": parts[0], "current": parts[1], "latest": parts[-1]})
        return outdated

    def app_store_apps(self) -> list:
        if shutil.which("mas"):
            raw = _run(["mas", "list"], timeout=30)
            if raw:
                apps = []
                for line in raw.splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        apps.append({"id": parts[0], "name": parts[1]})
                return apps
        apps = []
        for path in Path("/Applications").glob("*.app"):
            info_plist = path / "Contents" / "Info.plist"
            version = ""
            if info_plist.exists():
                v = _run(["defaults", "read", str(info_plist), "CFBundleShortVersionString"])
                version = v or ""
            apps.append({"name": path.stem, "version": version, "path": str(path)})
        return apps

    def system_integrity_protection(self) -> dict:
        result = {}
        sip = _run(["csrutil", "status"])
        result["sip"] = sip or "unknown"
        gk = _run(["spctl", "--status"])
        result["gatekeeper"] = gk or "unknown"
        return result

    def services(self) -> list:
        raw = _run(["launchctl", "list"])
        if not raw:
            return []
        services = []
        for line in raw.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                services.append({"pid": parts[0], "status": parts[1], "label": parts[2]})
        return services

    def running_processes(self) -> list:
        raw = _run(["ps", "aux", "-r"])
        if not raw:
            return []
        procs = []
        for line in raw.splitlines()[1:51]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                procs.append({"user": parts[0], "pid": parts[1],
                              "cpu_pct": parts[2], "mem_pct": parts[3],
                              "command": parts[10]})
        return procs

    def network_info(self) -> list:
        results = []
        raw = _run(["ifconfig"])
        if raw:
            results.append({"ifconfig": raw[:3000]})
        gw = _run(["netstat", "-nr"])
        if gw:
            results.append({"routing_table": _parse_lines(gw)})
        return results

    def open_ports(self) -> list:
        raw = _run(["lsof", "-i", "-n", "-P", "-sTCP:LISTEN"], timeout=30)
        return _parse_lines(raw)

    def firewall(self) -> dict:
        result = {}
        fw = _run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
        result["application_firewall"] = fw or "unknown"
        pf = _run(["pfctl", "-s", "info"])
        result["pf"] = pf or "unknown"
        return result

    def disk_health(self) -> list:
        results = []
        raw = _run(["diskutil", "list"])
        if raw:
            results.append({"diskutil_list": _parse_lines(raw)})
        smart = _run(["diskutil", "info", "/dev/disk0"])
        if smart:
            results.append({"disk0_info": _parse_lines(smart)})
        return results

    def users(self) -> list:
        raw = _run(["dscl", ".", "-list", "/Users"])
        users = []
        if raw:
            for user in raw.splitlines():
                if not user.startswith("_"):
                    users.append({"username": user})
        return users

    def security_config(self) -> dict:
        result = {}
        fv = _run(["fdesetup", "status"])
        result["filevault"] = fv or "unknown"
        mrt = Path("/Library/Apple/System/Library/CoreServices/MRT.app/Contents/version.plist")
        result["mrt_exists"] = mrt.exists()
        return result

    def login_items(self) -> list:
        script = 'tell application "System Events" to get the name of every login item'
        raw = _run(["osascript", "-e", script], timeout=15)
        if raw:
            return [item.strip() for item in raw.split(",") if item.strip()]
        return []

    def recent_log_errors(self) -> list:
        raw = _run(["log", "show", "--last", "1h",
                     "--predicate", "messageType == 16 OR messageType == 17",
                     "--style", "compact", "--info"], timeout=30)
        if raw:
            return _parse_lines(raw)[-50:]
        return []

    def collect(self) -> Dict[str, Any]:
        logger.info("macOS slow-lane collection starting...")
        data = {}
        collectors = [
            ("software_updates", self.software_updates),
            ("update_history", self.update_history),
            ("homebrew_packages", self.homebrew_packages),
            ("homebrew_outdated", self.homebrew_outdated),
            ("app_store_apps", self.app_store_apps),
            ("system_integrity", self.system_integrity_protection),
            ("services", self.services),
            ("running_processes", self.running_processes),
            ("network_info", self.network_info),
            ("open_ports", self.open_ports),
            ("firewall", self.firewall),
            ("disk_health", self.disk_health),
            ("users", self.users),
            ("security_config", self.security_config),
            ("login_items", self.login_items),
            ("recent_errors", self.recent_log_errors),
        ]
        for key, fn in collectors:
            try:
                logger.debug(f"  Collecting {key}...")
                data[key] = fn()
            except Exception as e:
                logger.warning(f"  {key} failed: {e}")
                data[key] = []
        logger.info(f"macOS slow-lane collection complete ({len(data)} sections)")
        return data


# ═══════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════

def get_slow_collector():
    """Return the appropriate slow-lane collector for the current OS."""
    if OS == "Windows":
        return WindowsSlowCollector()
    elif OS == "Linux":
        return LinuxSlowCollector()
    elif OS == "Darwin":
        return MacOSSlowCollector()
    else:
        raise RuntimeError(f"Unsupported OS: {OS}")
