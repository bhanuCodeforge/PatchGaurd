"""
╔══════════════════════════════════════════════════════════════════╗
║        CROSS-PLATFORM MASSIVE PATCH INFO SCANNER                ║
║        Supports: Windows · Linux / Ubuntu · macOS               ║
║        Output : JSON (file + optional stdout)                   ║
╚══════════════════════════════════════════════════════════════════╝

Usage:
    python patch_scanner.py              # auto-detects OS
    python patch_scanner.py --stdout     # also print JSON to stdout
    python patch_scanner.py --out /tmp/report.json   # custom output path

Requirements:
    Python 3.8+  (no third-party packages needed)
    Linux/Ubuntu: run with sudo for full driver/service detail
    macOS:        run with sudo for full SIP/security detail
    Windows:      run as Administrator for full coverage
"""

import subprocess
import json
import os
import sys
import platform
import datetime
import shutil
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# SHARED UTILS
# ═══════════════════════════════════════════════════════════════

OS = platform.system()   # "Windows" | "Linux" | "Darwin"

def log(section: str):
    print(f"  ➤  {section}...")


def run(cmd: list[str] | str, shell: bool = False, timeout: int = 60) -> str | None:
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


def run_ps(cmd: str, timeout: int = 60) -> str | None:
    """Windows-only: run a PowerShell command."""
    return run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        timeout=timeout
    )


def safe_json(raw: str | None) -> list | dict | None:
    """Parse JSON safely; wrap single-object into list."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return [parsed] if isinstance(parsed, dict) else parsed
    except json.JSONDecodeError:
        return None


def parse_lines(raw: str | None) -> list[str]:
    """Split command output into non-empty lines."""
    if not raw:
        return []
    return [l.strip() for l in raw.splitlines() if l.strip()]


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_root() -> bool:
    """True if running as root / Administrator."""
    try:
        return os.geteuid() == 0
    except AttributeError:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())


# ═══════════════════════════════════════════════════════════════
# ██████████████  WINDOWS COLLECTORS  ██████████████
# ═══════════════════════════════════════════════════════════════

class WindowsCollector:

    def system_info(self) -> dict:
        log("System info")
        cmd = """
        $os  = Get-CimInstance Win32_OperatingSystem
        $cpu = Get-CimInstance Win32_Processor | Select -First 1
        $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,2)
        $disk = Get-PSDrive C | Select @{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}},
                                        @{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}}
        $bios = Get-CimInstance Win32_BIOS
        [PSCustomObject]@{
            ComputerName   = $env:COMPUTERNAME
            UserName       = $env:USERNAME
            OSCaption      = $os.Caption
            OSVersion      = $os.Version
            OSBuild        = $os.BuildNumber
            Architecture   = $os.OSArchitecture
            InstallDate    = $os.InstallDate.ToString("yyyy-MM-dd")
            LastBoot       = $os.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss")
            CPU            = $cpu.Name
            CPUCores       = $cpu.NumberOfCores
            RAM_GB         = $ram
            DiskFree_GB    = $disk.FreeGB
            DiskUsed_GB    = $disk.UsedGB
            BIOSVersion    = $bios.SMBIOSBIOSVersion
            BIOSDate       = $bios.ReleaseDate.ToString("yyyy-MM-dd")
            Domain         = (Get-WmiObject Win32_ComputerSystem).Domain
            TimeZone       = (Get-TimeZone).Id
        } | ConvertTo-Json"""
        r = safe_json(run_ps(cmd))
        return r[0] if isinstance(r, list) and r else {}

    def installed_patches(self) -> list:
        log("Installed patches (HotFix)")
        cmd = """Get-HotFix |
            Select HotFixID, Description, InstalledBy,
            @{N='InstalledOn';E={if($_.InstalledOn){$_.InstalledOn.ToString("yyyy-MM-dd")}else{"Unknown"}}} |
            Sort InstalledOn -Desc | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def update_history(self) -> list:
        log("Windows Update history")
        cmd = """
        $s = New-Object -ComObject Microsoft.Update.Session
        $h = $s.CreateUpdateSearcher()
        $c = $h.GetTotalHistoryCount()
        $hist = $h.QueryHistory(0,$c)
        $list = @()
        foreach ($u in $hist) {
            $list += [PSCustomObject]@{
                Title      = $u.Title
                Date       = $u.Date.ToString("yyyy-MM-dd HH:mm:ss")
                Result     = switch($u.ResultCode){0{"NotStarted"}1{"InProgress"}2{"Succeeded"}3{"SucceededWithErrors"}4{"Failed"}5{"Aborted"}default{"Unknown"}}
                KB         = if($u.Title -match "KB(\d+)"){"KB$($matches[1])"}else{""}
                Categories = ($u.Categories|ForEach-Object{$_.Name}) -join ", "
            }
        }
        $list | ConvertTo-Json"""
        return safe_json(run_ps(cmd, timeout=90)) or []

    def missing_updates(self) -> list:
        log("Missing / pending updates")
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
        return safe_json(run_ps(cmd, timeout=120)) or []

    def defender_status(self) -> dict:
        log("Windows Defender")
        cmd = """
        try {
            $s = Get-MpComputerStatus
            [PSCustomObject]@{
                AntivirusEnabled          = $s.AntivirusEnabled
                RealTimeProtection        = $s.RealTimeProtectionEnabled
                SignatureVersion          = $s.AntivirusSignatureVersion
                SignatureAge_days         = $s.AntivirusSignatureAge
                LastFullScan              = if($s.FullScanEndTime){$s.FullScanEndTime.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}
                LastQuickScan             = if($s.QuickScanEndTime){$s.QuickScanEndTime.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}
                DefenderVersion           = $s.AMProductVersion
                BehaviorMonitor           = $s.BehaviorMonitorEnabled
                IoavProtection            = $s.IoavProtectionEnabled
                NISEnabled                = $s.NISEnabled
            } | ConvertTo-Json
        } catch { @{} | ConvertTo-Json }"""
        r = safe_json(run_ps(cmd))
        return r[0] if isinstance(r, list) and r else {}

    def registry_apps(self) -> list:
        log("Registry apps (all hives)")
        cmd = r"""
        $paths=@("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
                 "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                 "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*")
        $apps = foreach($p in $paths){
            Get-ItemProperty $p -EA SilentlyContinue |
            Where{$_.DisplayName} |
            Select DisplayName,DisplayVersion,Publisher,InstallDate,
                @{N='Size_MB';E={[math]::Round($_.EstimatedSize/1024,2)}},InstallLocation
        }
        $apps | Sort DisplayName -Unique | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def store_apps(self) -> list:
        log("Microsoft Store / AppX apps")
        cmd = "Get-AppxPackage | Select Name,Version,Publisher,Architecture | Sort Name | ConvertTo-Json"
        return safe_json(run_ps(cmd)) or []

    def drivers(self) -> list:
        log("Installed drivers")
        cmd = """Get-WmiObject Win32_PnPSignedDriver | Where{$_.DeviceName} |
            Select DeviceName,DriverVersion,
            @{N='DriverDate';E={if($_.DriverDate){$_.ConvertToDateTime($_.DriverDate).ToString("yyyy-MM-dd")}else{"Unknown"}}},
            Manufacturer,DeviceClass,IsSigned | Sort DeviceClass,DeviceName | ConvertTo-Json"""
        return safe_json(run_ps(cmd, timeout=90)) or []

    def services(self) -> list:
        log("Windows services")
        cmd = "Get-Service | Select Name,DisplayName,Status,StartType | Sort Status,DisplayName | ConvertTo-Json"
        return safe_json(run_ps(cmd)) or []

    def firewall(self) -> list:
        log("Firewall profiles")
        cmd = "Get-NetFirewallProfile | Select Name,Enabled,DefaultInboundAction,DefaultOutboundAction,LogFileName | ConvertTo-Json"
        return safe_json(run_ps(cmd)) or []

    def scheduled_tasks(self) -> list:
        log("Scheduled tasks")
        cmd = """Get-ScheduledTask | Where{$_.State -ne "Disabled"} |
            Select TaskName,TaskPath,State,
            @{N='RunAs';E={$_.Principal.UserId}},
            @{N='Actions';E={($_.Actions|ForEach{$_.Execute})-join"; "}} | ConvertTo-Json"""
        return safe_json(run_ps(cmd, timeout=90)) or []

    def running_processes(self) -> list:
        log("Running processes")
        cmd = """Get-Process | Select ProcessName,Id,CPU,
            @{N='Memory_MB';E={[math]::Round($_.WorkingSet64/1MB,2)}},
            Path,Company,ProductVersion | Sort Memory_MB -Desc | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def network_info(self) -> list:
        log("Network / IP config")
        cmd = """Get-NetIPConfiguration | Select InterfaceAlias,
            @{N='IPv4';E={$_.IPv4Address.IPAddress -join ", "}},
            @{N='Gateway';E={$_.IPv4DefaultGateway.NextHop -join ", "}},
            @{N='DNS';E={$_.DNSServer.ServerAddresses -join ", "}} | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def startup_programs(self) -> list:
        log("Startup programs")
        cmd = r"""
        $list=@()
        $reg=@("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
               "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
               "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")
        foreach($p in $reg){
            if(Test-Path $p){
                (Get-ItemProperty $p).PSObject.Properties|Where{$_.Name -notlike "PS*"}|ForEach{
                    $list+=[PSCustomObject]@{Name=$_.Name;Command=$_.Value;Source=$p}
                }
            }
        }
        $list | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def disk_health(self) -> list:
        log("Disk health (SMART)")
        cmd = """Get-PhysicalDisk | Select FriendlyName,MediaType,HealthStatus,OperationalStatus,
            @{N='Size_GB';E={[math]::Round($_.Size/1GB,2)}},BusType | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def windows_features(self) -> list:
        log("Windows optional features")
        cmd = "Get-WindowsOptionalFeature -Online | Where{$_.State -eq 'Enabled'} | Select FeatureName,State | Sort FeatureName | ConvertTo-Json"
        return safe_json(run_ps(cmd, timeout=90)) or []

    def local_users(self) -> list:
        log("Local user accounts")
        cmd = """Get-LocalUser | Select Name,Enabled,FullName,Description,
            @{N='LastLogon';E={if($_.LastLogon){$_.LastLogon.ToString("yyyy-MM-dd HH:mm:ss")}else{"Never"}}} | ConvertTo-Json"""
        return safe_json(run_ps(cmd)) or []

    def event_log_errors(self) -> list:
        log("Recent event log errors")
        cmd = """Get-EventLog -LogName System -EntryType Error,Warning -Newest 50 |
            Select @{N='Time';E={$_.TimeGenerated.ToString("yyyy-MM-dd HH:mm:ss")}},
            Source,EventID,@{N='EntryType';E={$_.EntryType.ToString()}},
            @{N='Message';E={$_.Message -replace "`r`n"," "}} | ConvertTo-Json"""
        return safe_json(run_ps(cmd, timeout=60)) or []

    def exe_scan(self) -> list:
        log("Program Files EXE scan")
        found = []
        bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA")]
        skip = {"windows", "system32", "syswow64", "winsxs"}
        for base in bases:
            if not base or not os.path.exists(base):
                continue
            try:
                for root, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if d.lower() not in skip]
                    for f in files:
                        if f.lower().endswith(".exe"):
                            fp = os.path.join(root, f)
                            try:
                                s = os.stat(fp)
                                found.append({"name": f, "path": fp,
                                              "size_kb": round(s.st_size / 1024, 2),
                                              "modified": datetime.datetime.fromtimestamp(
                                                  s.st_mtime).strftime("%Y-%m-%d")})
                            except (PermissionError, OSError):
                                pass
            except (PermissionError, OSError):
                pass
        return found

    def collect(self) -> dict:
        data = {
            "system_info":       self.system_info(),
            "installed_patches": self.installed_patches(),
            "update_history":    self.update_history(),
            "missing_updates":   self.missing_updates(),
            "defender_status":   self.defender_status(),
            "registry_apps":     self.registry_apps(),
            "store_apps":        self.store_apps(),
            "drivers":           self.drivers(),
            "services":          self.services(),
            "firewall":          self.firewall(),
            "scheduled_tasks":   self.scheduled_tasks(),
            "running_processes": self.running_processes(),
            "network_info":      self.network_info(),
            "startup_programs":  self.startup_programs(),
            "disk_health":       self.disk_health(),
            "windows_features":  self.windows_features(),
            "local_users":       self.local_users(),
            "event_log_errors":  self.event_log_errors(),
            "exe_scan":          self.exe_scan(),
        }
        return data


# ═══════════════════════════════════════════════════════════════
# ██████████████  LINUX / UBUNTU COLLECTORS  ██████████████
# ═══════════════════════════════════════════════════════════════

class LinuxCollector:

    def _cmd(self, *args, **kw) -> str | None:
        return run(list(args), **kw)

    def system_info(self) -> dict:
        log("System info")
        info = {}

        # Kernel, hostname, arch
        info["hostname"]      = run(["hostname"]) or "unknown"
        info["kernel"]        = run(["uname", "-r"]) or "unknown"
        info["arch"]          = run(["uname", "-m"]) or "unknown"
        info["os_release"]    = {}

        # /etc/os-release
        release_path = Path("/etc/os-release")
        if release_path.exists():
            for line in release_path.read_text().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    info["os_release"][k.strip()] = v.strip().strip('"')

        # Uptime
        uptime_raw = run(["uptime", "-p"])
        info["uptime"] = uptime_raw or run(["uptime"]) or "unknown"

        # CPU
        cpu_info = run(["grep", "-m1", "model name", "/proc/cpuinfo"])
        info["cpu"] = cpu_info.split(":")[-1].strip() if cpu_info else "unknown"
        cpu_cores = run(["nproc"])
        info["cpu_cores"] = int(cpu_cores) if cpu_cores and cpu_cores.isdigit() else None

        # RAM
        mem_raw = run(["grep", "MemTotal", "/proc/meminfo"])
        if mem_raw:
            kb = int("".join(filter(str.isdigit, mem_raw)))
            info["ram_gb"] = round(kb / 1024 / 1024, 2)

        # Disk
        df_raw = run(["df", "-h", "/"])
        if df_raw:
            lines = df_raw.splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                info["disk"] = {"size": parts[1], "used": parts[2],
                                "free": parts[3], "use_pct": parts[4]}

        # Current user
        info["current_user"] = run(["whoami"]) or os.environ.get("USER", "unknown")
        info["timezone"] = run(["date", "+%Z"]) or "unknown"

        return info

    def installed_packages(self) -> list:
        """All installed packages — works for apt (Debian/Ubuntu) and rpm (RHEL/Fedora)."""
        log("Installed packages")

        # apt / dpkg (Debian, Ubuntu)
        if shutil.which("dpkg"):
            raw = run(["dpkg-query", "-W",
                       "-f=${Package}\\t${Version}\\t${Architecture}\\t${Status}\\n"])
            if raw:
                pkgs = []
                for line in raw.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        pkgs.append({"name": parts[0], "version": parts[1],
                                     "arch": parts[2],
                                     "status": parts[3] if len(parts) > 3 else "unknown"})
                return pkgs

        # rpm (RHEL, Fedora, CentOS)
        if shutil.which("rpm"):
            raw = run(["rpm", "-qa", "--queryformat",
                       "%{NAME}\\t%{VERSION}\\t%{ARCH}\\t%{INSTALLTIME:date}\\n"])
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
        """Pending security upgrades (apt/dnf)."""
        log("Security updates available")

        # Ubuntu / Debian
        if shutil.which("apt"):
            raw = run(["apt", "list", "--upgradable"], timeout=60)
            if raw:
                pkgs = []
                for line in raw.splitlines()[1:]:   # skip "Listing..." header
                    if line:
                        parts = line.split()
                        pkgs.append({"package": parts[0].split("/")[0] if parts else line,
                                     "available_version": parts[1] if len(parts) > 1 else "",
                                     "arch": parts[2] if len(parts) > 2 else ""})
                return pkgs

        # RHEL / Fedora / CentOS
        if shutil.which("dnf"):
            raw = run(["dnf", "check-update", "--security"], timeout=90)
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
        """Recent package installs/upgrades from apt/dpkg/yum logs."""
        log("Patch / update history")
        results = []

        # Ubuntu/Debian — /var/log/dpkg.log*
        for log_path in sorted(Path("/var/log").glob("dpkg.log*"), reverse=True)[:3]:
            try:
                for line in log_path.read_text(errors="replace").splitlines():
                    if "install" in line or "upgrade" in line:
                        results.append(line.strip())
            except (PermissionError, OSError):
                pass

        # Also check apt/history.log
        apt_history = Path("/var/log/apt/history.log")
        if apt_history.exists():
            try:
                for line in apt_history.read_text(errors="replace").splitlines():
                    if line.startswith(("Start-Date", "Upgrade:", "Install:", "End-Date")):
                        results.append(line.strip())
            except (PermissionError, OSError):
                pass

        # RHEL/CentOS — yum/dnf history
        if shutil.which("dnf"):
            raw = run(["dnf", "history", "list", "last-20"], timeout=30)
            if raw:
                results.extend(raw.splitlines())

        return results[-200:]   # keep last 200 entries

    def kernel_patches(self) -> list:
        """Installed kernel versions."""
        log("Installed kernel versions")
        results = []

        if shutil.which("dpkg"):
            raw = run(["dpkg", "-l", "linux-image-*"])
            if raw:
                for line in raw.splitlines():
                    if line.startswith("ii"):
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({"package": parts[1], "version": parts[2],
                                            "status": "installed"})

        elif shutil.which("rpm"):
            raw = run(["rpm", "-qa", "kernel"])
            if raw:
                results = [{"package": k, "version": ""} for k in raw.splitlines()]

        # Current running kernel
        cur = run(["uname", "-r"])
        return [{"running_kernel": cur}] + results

    def services(self) -> list:
        """systemd service status."""
        log("systemd services")
        if not shutil.which("systemctl"):
            return []
        raw = run(["systemctl", "list-units", "--type=service",
                   "--all", "--no-pager", "--no-legend"], timeout=30)
        if not raw:
            return []
        services = []
        for line in raw.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 4:
                services.append({
                    "unit": parts[0],
                    "load": parts[1],
                    "active": parts[2],
                    "sub": parts[3],
                    "description": parts[4] if len(parts) > 4 else ""
                })
        return services

    def running_processes(self) -> list:
        """Top processes by memory."""
        log("Running processes")
        raw = run(["ps", "aux", "--sort=-%mem"])
        if not raw:
            return []
        procs = []
        lines = raw.splitlines()
        headers = lines[0].split() if lines else []
        for line in lines[1:51]:    # top 50
            parts = line.split(None, 10)
            if len(parts) >= 11:
                procs.append({"user": parts[0], "pid": parts[1],
                               "cpu_pct": parts[2], "mem_pct": parts[3],
                               "command": parts[10]})
        return procs

    def network_info(self) -> list:
        """Network interfaces and IPs."""
        log("Network info")
        results = []

        # ip addr
        raw = run(["ip", "-brief", "addr"])
        if raw:
            for line in raw.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    results.append({"interface": parts[0], "state": parts[1],
                                    "addresses": parts[2:] if len(parts) > 2 else []})
        # routing
        gw = run(["ip", "route", "show", "default"])
        if gw:
            results.append({"default_route": gw})

        # DNS
        resolv = Path("/etc/resolv.conf")
        if resolv.exists():
            dns = [l.split()[1] for l in resolv.read_text().splitlines()
                   if l.startswith("nameserver")]
            results.append({"dns_servers": dns})

        return results

    def open_ports(self) -> list:
        """Listening ports via ss or netstat."""
        log("Open / listening ports")
        if shutil.which("ss"):
            raw = run(["ss", "-tlnup"])
        elif shutil.which("netstat"):
            raw = run(["netstat", "-tlnup"])
        else:
            return []
        return parse_lines(raw)

    def firewall(self) -> dict:
        """ufw / iptables / firewalld status."""
        log("Firewall status")
        result = {}

        if shutil.which("ufw"):
            result["ufw"] = run(["ufw", "status", "verbose"])
        if shutil.which("iptables"):
            result["iptables_rules"] = parse_lines(run(["iptables", "-L", "-n", "--line-numbers"]))
        if shutil.which("firewall-cmd"):
            result["firewalld_zones"] = run(["firewall-cmd", "--list-all"])

        return result

    def disk_health(self) -> list:
        """Disk partitions and SMART summary."""
        log("Disk health")
        results = []

        # lsblk
        raw = run(["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL", "--json"])
        if raw:
            parsed = safe_json(raw)
            if parsed:
                results.append({"lsblk": parsed})

        # df -h
        df = run(["df", "-h", "--output=source,fstype,size,used,avail,pcent,target"])
        if df:
            results.append({"df": parse_lines(df)})

        # smartctl if available (requires root)
        if shutil.which("smartctl") and is_root():
            smart = run(["smartctl", "-a", "/dev/sda"], timeout=15)
            if smart:
                results.append({"smartctl_sda": smart[:2000]})

        return results

    def users(self) -> list:
        """Local user accounts from /etc/passwd + last login."""
        log("Local users")
        users = []
        try:
            for line in Path("/etc/passwd").read_text().splitlines():
                parts = line.split(":")
                if len(parts) >= 7:
                    uid = int(parts[2])
                    if uid >= 1000 or parts[0] == "root":
                        users.append({
                            "username": parts[0], "uid": uid, "gid": int(parts[3]),
                            "home": parts[5], "shell": parts[6]
                        })
        except (PermissionError, OSError):
            pass

        last_raw = run(["last", "-n", "20"])
        if last_raw:
            users.append({"recent_logins": parse_lines(last_raw)})

        return users

    def cron_jobs(self) -> list:
        """System and user cron jobs."""
        log("Cron jobs")
        jobs = []

        # system crontabs
        for path in [Path("/etc/crontab")] + list(Path("/etc/cron.d").glob("*")):
            try:
                jobs.append({"file": str(path),
                             "content": path.read_text(errors="replace")})
            except (PermissionError, OSError):
                pass

        # current user crontab
        raw = run(["crontab", "-l"])
        if raw:
            jobs.append({"user_crontab": raw})

        return jobs

    def security_config(self) -> dict:
        """SELinux / AppArmor / auditd status."""
        log("Security config (SELinux/AppArmor)")
        result = {}

        if shutil.which("getenforce"):
            result["selinux"] = run(["getenforce"])
        if shutil.which("apparmor_status") or Path("/sys/kernel/security/apparmor").exists():
            result["apparmor"] = run(["aa-status", "--json"]) or run(["apparmor_status"])
        if shutil.which("auditctl"):
            result["auditd"] = run(["auditctl", "-s"])
        if shutil.which("lynis"):
            result["lynis_available"] = True

        # /etc/sysctl — key security settings
        sysctl_keys = ["kernel.randomize_va_space", "kernel.dmesg_restrict",
                       "net.ipv4.ip_forward", "net.ipv4.conf.all.accept_redirects"]
        sysctl_vals = {}
        for key in sysctl_keys:
            val = run(["sysctl", "-n", key])
            if val:
                sysctl_vals[key] = val
        result["sysctl_security"] = sysctl_vals

        return result

    def installed_snaps(self) -> list:
        """Snap packages (Ubuntu)."""
        log("Snap packages")
        if not shutil.which("snap"):
            return []
        raw = run(["snap", "list"])
        if not raw:
            return []
        snaps = []
        for line in raw.splitlines()[1:]:
            parts = line.split(None, 5)
            if len(parts) >= 4:
                snaps.append({"name": parts[0], "version": parts[1],
                               "rev": parts[2], "tracking": parts[3],
                               "publisher": parts[4] if len(parts) > 4 else ""})
        return snaps

    def flatpaks(self) -> list:
        """Flatpak applications."""
        log("Flatpak apps")
        if not shutil.which("flatpak"):
            return []
        raw = run(["flatpak", "list", "--columns=name,version,origin,installation"])
        if not raw:
            return []
        apps = []
        for line in raw.splitlines():
            parts = line.split("\t")
            if parts:
                apps.append({"name": parts[0],
                             "version": parts[1] if len(parts) > 1 else "",
                             "origin": parts[2] if len(parts) > 2 else "",
                             "install": parts[3] if len(parts) > 3 else ""})
        return apps

    def recent_log_errors(self) -> list:
        """Recent kernel + auth errors from journalctl."""
        log("Recent system log errors")
        if shutil.which("journalctl"):
            raw = run(["journalctl", "-p", "err", "-n", "50",
                       "--no-pager", "--output=short-iso"], timeout=30)
            return parse_lines(raw)

        # fallback: syslog
        syslog = Path("/var/log/syslog")
        if syslog.exists():
            try:
                lines = syslog.read_text(errors="replace").splitlines()
                return [l for l in lines[-200:] if "error" in l.lower() or "fail" in l.lower()][-50:]
            except (PermissionError, OSError):
                pass
        return []

    def collect(self) -> dict:
        return {
            "system_info":        self.system_info(),
            "installed_packages": self.installed_packages(),
            "kernel_patches":     self.kernel_patches(),
            "security_updates":   self.security_updates(),
            "patch_history":      self.patch_history(),
            "services":           self.services(),
            "running_processes":  self.running_processes(),
            "network_info":       self.network_info(),
            "open_ports":         self.open_ports(),
            "firewall":           self.firewall(),
            "disk_health":        self.disk_health(),
            "users":              self.users(),
            "cron_jobs":          self.cron_jobs(),
            "security_config":    self.security_config(),
            "snap_packages":      self.installed_snaps(),
            "flatpak_apps":       self.flatpaks(),
            "recent_errors":      self.recent_log_errors(),
        }


# ═══════════════════════════════════════════════════════════════
# ██████████████  macOS COLLECTORS  ██████████████
# ═══════════════════════════════════════════════════════════════

class MacOSCollector:

    def system_info(self) -> dict:
        log("System info")
        info = {}

        sw = run(["sw_vers"])
        if sw:
            for line in sw.splitlines():
                k, _, v = line.partition(":")
                info[k.strip()] = v.strip()

        info["hostname"]  = run(["hostname"]) or "unknown"
        info["arch"]      = run(["uname", "-m"]) or "unknown"
        info["kernel"]    = run(["uname", "-r"]) or "unknown"
        info["uptime"]    = run(["uptime"]) or "unknown"

        # CPU / RAM via sysctl
        cpu_brand = run(["sysctl", "-n", "machdep.cpu.brand_string"])
        info["cpu"] = cpu_brand or run(["sysctl", "-n", "hw.model"]) or "unknown"
        cpu_cores = run(["sysctl", "-n", "hw.logicalcpu"])
        info["cpu_cores"] = int(cpu_cores) if cpu_cores and cpu_cores.isdigit() else None

        mem_bytes = run(["sysctl", "-n", "hw.memsize"])
        if mem_bytes and mem_bytes.isdigit():
            info["ram_gb"] = round(int(mem_bytes) / 1024**3, 2)

        # Disk
        df = run(["df", "-h", "/"])
        if df:
            lines = df.splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                info["disk"] = {"size": parts[1], "used": parts[2],
                                "free": parts[3], "use_pct": parts[4]}

        info["current_user"] = run(["whoami"]) or os.environ.get("USER", "unknown")
        info["timezone"]     = run(["date", "+%Z"]) or "unknown"
        info["serial_number"] = run(["system_profiler", "SPHardwareDataType"]) or ""

        return info

    def software_updates(self) -> list:
        """Pending macOS software updates."""
        log("Available software updates")
        raw = run(["softwareupdate", "-l"], timeout=90)
        if not raw:
            return []
        updates = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("*") or line.startswith("-"):
                updates.append({"update": line.lstrip("*- ").strip()})
        return updates

    def update_history(self) -> list:
        """macOS software update install history."""
        log("Software update history")
        hist_path = Path("/Library/Receipts/InstallHistory.plist")
        if not hist_path.exists():
            return []
        raw = run(["plutil", "-p", str(hist_path)])
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
        """Homebrew formulae and casks."""
        log("Homebrew packages")
        if not shutil.which("brew"):
            return []
        packages = []

        raw = run(["brew", "list", "--versions"], timeout=60)
        if raw:
            for line in raw.splitlines():
                parts = line.split()
                packages.append({"name": parts[0], "versions": parts[1:],
                                 "type": "formula"})

        raw_casks = run(["brew", "list", "--cask", "--versions"], timeout=60)
        if raw_casks:
            for line in raw_casks.splitlines():
                parts = line.split()
                packages.append({"name": parts[0], "versions": parts[1:],
                                 "type": "cask"})

        return packages

    def homebrew_outdated(self) -> list:
        """Outdated Homebrew packages."""
        log("Homebrew outdated")
        if not shutil.which("brew"):
            return []
        raw = run(["brew", "outdated", "--verbose"], timeout=60)
        if not raw:
            return []
        outdated = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                outdated.append({"name": parts[0], "current": parts[1],
                                 "latest": parts[-1]})
        return outdated

    def app_store_apps(self) -> list:
        """Mac App Store installed apps (via mas if available)."""
        log("App Store apps")
        if shutil.which("mas"):
            raw = run(["mas", "list"], timeout=30)
            if raw:
                apps = []
                for line in raw.splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        apps.append({"id": parts[0], "name": parts[1]})
                return apps

        # fallback: scan /Applications
        apps = []
        for path in Path("/Applications").glob("*.app"):
            info_plist = path / "Contents" / "Info.plist"
            version = ""
            if info_plist.exists():
                v = run(["defaults", "read", str(info_plist), "CFBundleShortVersionString"])
                version = v or ""
            apps.append({"name": path.stem, "version": version,
                         "path": str(path)})
        return apps

    def system_integrity_protection(self) -> dict:
        """SIP status and Gatekeeper."""
        log("SIP + Gatekeeper status")
        result = {}
        sip = run(["csrutil", "status"])
        result["sip"] = sip or "unknown"
        gk = run(["spctl", "--status"])
        result["gatekeeper"] = gk or "unknown"
        xp = run(["xprotect", "--list-profiles"]) if shutil.which("xprotect") else None
        result["xprotect"] = xp or "see /System/Library/CoreServices/XProtect.bundle"
        return result

    def services(self) -> list:
        """launchd services (loaded)."""
        log("launchd services")
        raw = run(["launchctl", "list"])
        if not raw:
            return []
        services = []
        for line in raw.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                services.append({"pid": parts[0], "status": parts[1], "label": parts[2]})
        return services

    def running_processes(self) -> list:
        """Top 50 processes by memory."""
        log("Running processes")
        raw = run(["ps", "aux", "-r"])   # -r sorts by CPU on macOS
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
        """Network interfaces and routing."""
        log("Network info")
        results = []

        raw = run(["ifconfig"])
        if raw:
            results.append({"ifconfig": raw[:3000]})

        gw = run(["netstat", "-nr"])
        if gw:
            results.append({"routing_table": parse_lines(gw)})

        # DNS
        dns = run(["scutil", "--dns"])
        if dns:
            resolvers = []
            for line in dns.splitlines():
                if "nameserver" in line.lower():
                    resolvers.append(line.strip())
            results.append({"dns": resolvers})

        return results

    def open_ports(self) -> list:
        """Listening ports via lsof."""
        log("Open / listening ports")
        raw = run(["lsof", "-i", "-n", "-P", "-sTCP:LISTEN"], timeout=30)
        return parse_lines(raw)

    def firewall(self) -> dict:
        """macOS Application Firewall status."""
        log("Firewall status")
        result = {}
        fw = run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
        result["application_firewall"] = fw or "unknown"
        fw_block = run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getblockall"])
        result["block_all"] = fw_block or "unknown"
        pf = run(["pfctl", "-s", "info"])
        result["pf"] = pf or "unknown (may need sudo)"
        return result

    def disk_health(self) -> list:
        """Disk info via diskutil."""
        log("Disk health")
        results = []
        raw = run(["diskutil", "list"])
        if raw:
            results.append({"diskutil_list": parse_lines(raw)})

        # SMART for first disk
        smart = run(["diskutil", "info", "/dev/disk0"])
        if smart:
            results.append({"disk0_info": parse_lines(smart)})

        return results

    def users(self) -> list:
        """Local user accounts."""
        log("Local users")
        raw = run(["dscl", ".", "-list", "/Users"])
        users = []
        if raw:
            for user in raw.splitlines():
                if not user.startswith("_"):
                    info = run(["dscl", ".", "-read", f"/Users/{user}",
                                "RealName", "UniqueID", "NFSHomeDirectory", "UserShell"])
                    users.append({"username": user, "info": info or ""})

        last = run(["last", "-n", "20"])
        if last:
            users.append({"recent_logins": parse_lines(last)})

        return users

    def security_config(self) -> dict:
        """FileVault, certificate trust, privacy settings."""
        log("Security config (FileVault / certs)")
        result = {}
        fv = run(["fdesetup", "status"])
        result["filevault"] = fv or "unknown"
        fw_mode = run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getloggingmode"])
        result["firewall_logging"] = fw_mode or "unknown"
        # MRT (Malware Removal Tool) version
        mrt = Path("/Library/Apple/System/Library/CoreServices/MRT.app/Contents/version.plist")
        result["mrt_exists"] = mrt.exists()
        return result

    def login_items(self) -> list:
        """Login items (background items) via osascript."""
        log("Login items")
        script = 'tell application "System Events" to get the name of every login item'
        raw = run(["osascript", "-e", script], timeout=15)
        if raw:
            return [item.strip() for item in raw.split(",") if item.strip()]
        return []

    def recent_log_errors(self) -> list:
        """Recent errors from unified log (log show)."""
        log("Recent system log errors")
        raw = run(["log", "show", "--last", "1h",
                   "--predicate", "messageType == 16 OR messageType == 17",
                   "--style", "compact", "--info"], timeout=30)
        if raw:
            return parse_lines(raw)[-50:]
        return []

    def collect(self) -> dict:
        return {
            "system_info":              self.system_info(),
            "software_updates":         self.software_updates(),
            "update_history":           self.update_history(),
            "homebrew_packages":        self.homebrew_packages(),
            "homebrew_outdated":        self.homebrew_outdated(),
            "app_store_apps":           self.app_store_apps(),
            "system_integrity":         self.system_integrity_protection(),
            "services":                 self.services(),
            "running_processes":        self.running_processes(),
            "network_info":             self.network_info(),
            "open_ports":               self.open_ports(),
            "firewall":                 self.firewall(),
            "disk_health":              self.disk_health(),
            "users":                    self.users(),
            "security_config":          self.security_config(),
            "login_items":              self.login_items(),
            "recent_errors":            self.recent_log_errors(),
        }


# ═══════════════════════════════════════════════════════════════
# SUMMARY BUILDER  (cross-platform)
# ═══════════════════════════════════════════════════════════════

def build_summary(os_name: str, data: dict) -> dict:
    summary = {
        "scan_time":      now_str(),
        "platform":       os_name,
        "admin":          is_root(),
        "python_version": platform.python_version(),
    }

    si = data.get("system_info", {})
    summary["hostname"] = si.get("hostname") or si.get("ComputerName", "unknown")

    if os_name == "Windows":
        summary["os"]              = si.get("OSCaption", "unknown")
        summary["os_build"]        = si.get("OSBuild", "unknown")
        summary["patches"]         = len(data.get("installed_patches", []))
        summary["missing_updates"] = len(data.get("missing_updates", []))
        missing = data.get("missing_updates", [])
        summary["critical_missing"] = sum(
            1 for u in missing if isinstance(u, dict) and
            str(u.get("Severity", "")).lower() == "critical")
        summary["registry_apps"]   = len(data.get("registry_apps", []))
        summary["store_apps"]      = len(data.get("store_apps", []))
        summary["drivers"]         = len(data.get("drivers", []))
        d = data.get("defender_status", {})
        summary["defender"]        = d.get("AntivirusEnabled", "unknown")
        summary["realtime_prot"]   = d.get("RealTimeProtection", "unknown")

    elif os_name == "Linux":
        os_rel = si.get("os_release", {})
        summary["os"]              = os_rel.get("PRETTY_NAME", "Linux")
        summary["kernel"]          = si.get("kernel", "unknown")
        summary["packages"]        = len(data.get("installed_packages", []))
        summary["pending_updates"] = len(data.get("security_updates", []))
        summary["snaps"]           = len(data.get("snap_packages", []))
        summary["flatpaks"]        = len(data.get("flatpak_apps", []))
        summary["services"]        = len(data.get("services", []))

    elif os_name == "Darwin":
        summary["os"]              = si.get("ProductName", "macOS") + " " + si.get("ProductVersion", "")
        summary["pending_updates"] = len(data.get("software_updates", []))
        summary["homebrew_pkgs"]   = len(data.get("homebrew_packages", []))
        summary["homebrew_outdated"] = len(data.get("homebrew_outdated", []))
        summary["app_store_apps"]  = len(data.get("app_store_apps", []))
        summary["sip"]             = data.get("system_integrity", {}).get("sip", "unknown")
        summary["filevault"]       = data.get("security_config", {}).get("filevault", "unknown")

    return summary


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 66)
    print("  🛡️   CROSS-PLATFORM MASSIVE PATCH INFO SCANNER")
    print(f"  🖥️   Platform detected: {OS}")
    print("=" * 66)

    if not is_root():
        print("\n  ⚠️   WARNING: Not running as root/Administrator.")
        print("       Some collectors may return partial data.\n")
    else:
        print("\n  ✅  Running with elevated privileges — full scan.\n")

    print("📡 Collecting data...\n")

    # ── pick collector ───────────────────────────────────────
    if OS == "Windows":
        collector = WindowsCollector()
    elif OS == "Linux":
        collector = LinuxCollector()
    elif OS == "Darwin":
        collector = MacOSCollector()
    else:
        print(f"❌  Unsupported OS: {OS}")
        sys.exit(1)

    data = collector.collect()
    data["_summary"] = build_summary(OS, data)

    # ── determine output path ────────────────────────────────
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"patch_info_{OS.lower()}_{ts}.json"
    out_path = Path(default_name)
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--out" and i + 2 < len(sys.argv):
            out_path = Path(sys.argv[i + 2])

    # ── serialize & save ─────────────────────────────────────
    json_str = json.dumps(data, indent=2, default=str)
    out_path.write_text(json_str, encoding="utf-8")

    # ── print summary ────────────────────────────────────────
    s = data["_summary"]
    print(f"\n{'=' * 66}")
    print(f"  ✅  SCAN COMPLETE")
    print(f"{'=' * 66}")
    print(f"  📄  Saved to : {out_path.resolve()}")
    print(f"  🕐  Scan time: {s['scan_time']}")
    print(f"  🖥️   OS       : {s.get('os', OS)}")
    print(f"  🔑  Admin    : {s['admin']}")
    print()

    if OS == "Windows":
        print(f"  📦  Installed patches  : {s.get('patches', 0)}")
        print(f"  🔴  Missing updates    : {s.get('missing_updates', 0)}  "
              f"(Critical: {s.get('critical_missing', 0)})")
        print(f"  🏪  Registry apps      : {s.get('registry_apps', 0)}")
        print(f"  🏬  Store apps         : {s.get('store_apps', 0)}")
        print(f"  🔧  Drivers            : {s.get('drivers', 0)}")
        print(f"  🛡️   Defender enabled   : {s.get('defender', '?')}")
    elif OS == "Linux":
        print(f"  🐧  Kernel             : {s.get('kernel', '?')}")
        print(f"  📦  Installed packages : {s.get('packages', 0)}")
        print(f"  🔴  Pending updates    : {s.get('pending_updates', 0)}")
        print(f"  📦  Snap packages      : {s.get('snaps', 0)}")
        print(f"  📦  Flatpak apps       : {s.get('flatpaks', 0)}")
        print(f"  ⚙️   Services           : {s.get('services', 0)}")
    elif OS == "Darwin":
        print(f"  🍎  OS version         : {s.get('os', '?')}")
        print(f"  🔴  Pending updates    : {s.get('pending_updates', 0)}")
        print(f"  🍺  Homebrew packages  : {s.get('homebrew_pkgs', 0)}")
        print(f"  ⬆️   Homebrew outdated  : {s.get('homebrew_outdated', 0)}")
        print(f"  🏪  App Store apps     : {s.get('app_store_apps', 0)}")
        print(f"  🔒  SIP               : {s.get('sip', '?')}")
        print(f"  🔐  FileVault          : {s.get('filevault', '?')}")

    print()

    if "--stdout" in sys.argv:
        print(json_str)

    return data


if __name__ == "__main__":
    main()