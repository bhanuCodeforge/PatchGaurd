"""
╔══════════════════════════════════════════════════════════╗
║         WINDOWS MASSIVE PATCH INFO SCANNER               ║
║         Collects: Patches | Apps | Drivers | Security    ║
║         Output : JSON (file + stdout)                    ║
╚══════════════════════════════════════════════════════════╝
"""

import subprocess
import json
import os
import sys
import platform
import datetime
import ctypes
import tempfile
from pathlib import Path


# ─────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────

def is_admin():
    """Check if script runs with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_powershell(command: str, timeout: int = 60) -> str | None:
    """Execute a PowerShell command and return stdout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = result.stdout.strip()
        return out if out else None
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  PowerShell command timed out after {timeout}s")
        return None
    except FileNotFoundError:
        print("  ❌  PowerShell not found — are you on Windows?")
        return None
    except Exception as e:
        print(f"  ❌  PowerShell error: {e}")
        return None


def safe_json(raw: str | None) -> list | dict | None:
    """Safely parse JSON, handling single-object responses."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        # PowerShell wraps single items as dict, wrap into list for consistency
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
    except json.JSONDecodeError:
        return None


def log(section: str):
    print(f"  ➤  {section}...")


# ─────────────────────────────────────────────
# 1. SYSTEM OVERVIEW
# ─────────────────────────────────────────────

def get_system_info() -> dict:
    """Basic OS + hardware information."""
    log("System Info")
    cmd = """
    $os  = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select -First 1
    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
    $disk = Get-PSDrive C | Select @{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}, @{N='UsedGB';E={[math]::Round($_.Used/1GB,2)}}
    $bios = Get-CimInstance Win32_BIOS

    [PSCustomObject]@{
        ComputerName      = $env:COMPUTERNAME
        UserName          = $env:USERNAME
        OSCaption         = $os.Caption
        OSVersion         = $os.Version
        OSBuild           = $os.BuildNumber
        OSArchitecture    = $os.OSArchitecture
        InstallDate       = $os.InstallDate.ToString("yyyy-MM-dd")
        LastBootTime      = $os.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss")
        CPU               = $cpu.Name
        CPUCores          = $cpu.NumberOfCores
        CPULogical        = $cpu.NumberOfLogicalProcessors
        RAM_GB            = $ram
        DiskFree_GB       = $disk.FreeGB
        DiskUsed_GB       = $disk.UsedGB
        BIOSVersion       = $bios.SMBIOSBIOSVersion
        BIOSDate          = $bios.ReleaseDate.ToString("yyyy-MM-dd")
        Domain            = (Get-WmiObject Win32_ComputerSystem).Domain
        TimeZone          = (Get-TimeZone).Id
    } | ConvertTo-Json
    """
    raw = run_powershell(cmd)
    result = safe_json(raw)
    if result and isinstance(result, list):
        return result[0]
    return {}


# ─────────────────────────────────────────────
# 2. INSTALLED HOTFIXES / PATCHES
# ─────────────────────────────────────────────

def get_installed_patches() -> list:
    """All installed Windows hotfixes from Get-HotFix."""
    log("Installed Patches (HotFixes)")
    cmd = """
    Get-HotFix |
        Select-Object HotFixID, Description, InstalledBy,
            @{N='InstalledOn'; E={
                if ($_.InstalledOn) { $_.InstalledOn.ToString("yyyy-MM-dd") } else { "Unknown" }
            }} |
        Sort-Object InstalledOn -Descending |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 3. WINDOWS UPDATE HISTORY
# ─────────────────────────────────────────────

def get_update_history() -> list:
    """Full Windows Update installation history."""
    log("Windows Update History")
    cmd = """
    $session  = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $count    = $searcher.GetTotalHistoryCount()
    $history  = $searcher.QueryHistory(0, $count)

    $list = @()
    foreach ($h in $history) {
        $list += [PSCustomObject]@{
            Title       = $h.Title
            Date        = $h.Date.ToString("yyyy-MM-dd HH:mm:ss")
            ResultCode  = switch ($h.ResultCode) {
                            0 { "NotStarted" }
                            1 { "InProgress" }
                            2 { "Succeeded" }
                            3 { "SucceededWithErrors" }
                            4 { "Failed" }
                            5 { "Aborted" }
                            default { "Unknown" }
                        }
            KB          = if ($h.Title -match "KB(\d+)") { "KB$($matches[1])" } else { "" }
            Categories  = ($h.Categories | ForEach-Object { $_.Name }) -join ", "
        }
    }
    $list | ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=90)) or []


# ─────────────────────────────────────────────
# 4. MISSING / PENDING UPDATES
# ─────────────────────────────────────────────

def get_missing_updates() -> list:
    """Updates available but not yet installed."""
    log("Missing / Pending Updates")
    cmd = """
    $session  = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()

    try {
        $results = $searcher.Search("IsInstalled=0 and Type='Software'")
        $list = @()
        foreach ($u in $results.Updates) {
            $list += [PSCustomObject]@{
                Title       = $u.Title
                KB          = ($u.KBArticleIDs -join ",")
                Severity    = if ($u.MsrcSeverity) { $u.MsrcSeverity } else { "None" }
                Type        = $u.Type
                Size_MB     = [math]::Round($u.MaxDownloadSize / 1MB, 2)
                IsDriver    = $u.DriverClass -ne $null
                RebootRequired = $u.RebootRequired
                Description = $u.Description
            }
        }
        $list | ConvertTo-Json
    } catch {
        @() | ConvertTo-Json
    }
    """
    return safe_json(run_powershell(cmd, timeout=120)) or []


# ─────────────────────────────────────────────
# 5. WINDOWS DEFENDER / ANTIVIRUS STATUS
# ─────────────────────────────────────────────

def get_defender_status() -> dict:
    """Windows Defender real-time protection + signature info."""
    log("Windows Defender Status")
    cmd = """
    try {
        $s = Get-MpComputerStatus
        [PSCustomObject]@{
            AntivirusEnabled          = $s.AntivirusEnabled
            RealTimeProtectionEnabled = $s.RealTimeProtectionEnabled
            AntivirusSignatureVersion = $s.AntivirusSignatureVersion
            AntivirusSignatureAge     = $s.AntivirusSignatureAge
            LastFullScan              = if ($s.FullScanEndTime) { $s.FullScanEndTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "Never" }
            LastQuickScan             = if ($s.QuickScanEndTime) { $s.QuickScanEndTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "Never" }
            DefenderVersion           = $s.AMProductVersion
            NISEnabled                = $s.NISEnabled
            BehaviorMonitorEnabled    = $s.BehaviorMonitorEnabled
            IoavProtectionEnabled     = $s.IoavProtectionEnabled
            OnAccessProtectionEnabled = $s.OnAccessProtectionEnabled
        } | ConvertTo-Json
    } catch {
        @{} | ConvertTo-Json
    }
    """
    raw = run_powershell(cmd)
    result = safe_json(raw)
    if result and isinstance(result, list):
        return result[0]
    return result or {}


# ─────────────────────────────────────────────
# 6. INSTALLED APPS (REGISTRY — ALL HIVES)
# ─────────────────────────────────────────────

def get_registry_apps() -> list:
    """All installed software from all registry uninstall hives."""
    log("Registry Apps (All Hives)")
    cmd = r"""
    $paths = @(
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $apps = foreach ($path in $paths) {
        Get-ItemProperty $path -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -and $_.DisplayName.Trim() -ne "" } |
        Select-Object DisplayName, DisplayVersion, Publisher,
            InstallDate,
            @{N='EstimatedSize_MB'; E={ [math]::Round($_.EstimatedSize / 1024, 2) }},
            InstallLocation,
            @{N='Hive'; E={ if ($path -match "HKLM") { "HKLM" } else { "HKCU" } }}
    }

    $apps |
        Sort-Object DisplayName -Unique |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 7. MICROSOFT STORE (APPX) APPS
# ─────────────────────────────────────────────

def get_store_apps() -> list:
    """Microsoft Store / AppX packages."""
    log("Microsoft Store Apps")
    cmd = """
    Get-AppxPackage |
        Select-Object Name, Version, Publisher, Architecture,
            @{N='InstallLocation'; E={ $_.InstallLocation }} |
        Sort-Object Name |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 8. INSTALLED DRIVERS
# ─────────────────────────────────────────────

def get_drivers() -> list:
    """All installed device drivers with version and date."""
    log("Installed Drivers")
    cmd = """
    Get-WmiObject Win32_PnPSignedDriver |
        Where-Object { $_.DeviceName } |
        Select-Object DeviceName, DriverVersion,
            @{N='DriverDate'; E={ if ($_.DriverDate) { $_.ConvertToDateTime($_.DriverDate).ToString("yyyy-MM-dd") } else { "Unknown" } }},
            Manufacturer, DeviceClass, InfName, IsSigned |
        Sort-Object DeviceClass, DeviceName |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=90)) or []


# ─────────────────────────────────────────────
# 9. SERVICES STATUS
# ─────────────────────────────────────────────

def get_services() -> list:
    """All Windows services with status and start type."""
    log("Windows Services")
    cmd = """
    Get-Service |
        Select-Object Name, DisplayName, Status, StartType,
            @{N='Description'; E={ (Get-WmiObject Win32_Service -Filter "Name='$($_.Name)'" -ErrorAction SilentlyContinue).Description }} |
        Sort-Object Status, DisplayName |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=60)) or []


# ─────────────────────────────────────────────
# 10. FIREWALL STATUS
# ─────────────────────────────────────────────

def get_firewall_status() -> list:
    """Windows Firewall profile status for all profiles."""
    log("Firewall Status")
    cmd = """
    Get-NetFirewallProfile |
        Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction,
            LogAllowed, LogBlocked, LogFileName |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 11. ENVIRONMENT VARIABLES
# ─────────────────────────────────────────────

def get_env_variables() -> dict:
    """System and user environment variables."""
    log("Environment Variables")
    return {
        "system": dict(os.environ),
    }


# ─────────────────────────────────────────────
# 12. SCHEDULED TASKS (SECURITY RELEVANT)
# ─────────────────────────────────────────────

def get_scheduled_tasks() -> list:
    """Scheduled tasks — useful for detecting persistence mechanisms."""
    log("Scheduled Tasks")
    cmd = """
    Get-ScheduledTask |
        Where-Object { $_.State -ne "Disabled" } |
        Select-Object TaskName, TaskPath, State,
            @{N='RunAs';     E={ $_.Principal.UserId }},
            @{N='LastRun';   E={ (Get-ScheduledTaskInfo $_.TaskName -ErrorAction SilentlyContinue).LastRunTime }},
            @{N='NextRun';   E={ (Get-ScheduledTaskInfo $_.TaskName -ErrorAction SilentlyContinue).NextRunTime }},
            @{N='Actions';   E={ ($_.Actions | ForEach-Object { $_.Execute }) -join "; " }} |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=90)) or []


# ─────────────────────────────────────────────
# 13. RUNNING PROCESSES
# ─────────────────────────────────────────────

def get_running_processes() -> list:
    """All running processes with memory and path info."""
    log("Running Processes")
    cmd = """
    Get-Process |
        Select-Object ProcessName, Id, CPU,
            @{N='Memory_MB'; E={ [math]::Round($_.WorkingSet64 / 1MB, 2) }},
            Path, Company, ProductVersion |
        Sort-Object Memory_MB -Descending |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 14. NETWORK ADAPTERS & IP CONFIG
# ─────────────────────────────────────────────

def get_network_info() -> list:
    """Network adapter details and IP addresses."""
    log("Network Info")
    cmd = """
    Get-NetIPConfiguration |
        Select-Object InterfaceAlias, InterfaceIndex,
            @{N='IPv4'; E={ $_.IPv4Address.IPAddress -join ", " }},
            @{N='IPv6'; E={ $_.IPv6Address.IPAddress -join ", " }},
            @{N='Gateway'; E={ $_.IPv4DefaultGateway.NextHop -join ", " }},
            @{N='DNS'; E={ $_.DNSServer.ServerAddresses -join ", " }} |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 15. STARTUP PROGRAMS
# ─────────────────────────────────────────────

def get_startup_programs() -> list:
    """Programs configured to run at startup."""
    log("Startup Programs")
    cmd = r"""
    $list = @()

    # Registry run keys
    $regPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
    )
    foreach ($p in $regPaths) {
        if (Test-Path $p) {
            $props = Get-ItemProperty $p
            $props.PSObject.Properties |
                Where-Object { $_.Name -notlike "PS*" } |
                ForEach-Object {
                    $list += [PSCustomObject]@{
                        Name     = $_.Name
                        Command  = $_.Value
                        Source   = $p
                    }
                }
        }
    }

    # Startup folder
    $startupFolders = @(
        [Environment]::GetFolderPath("Startup"),
        [Environment]::GetFolderPath("CommonStartup")
    )
    foreach ($folder in $startupFolders) {
        if (Test-Path $folder) {
            Get-ChildItem $folder -ErrorAction SilentlyContinue |
                ForEach-Object {
                    $list += [PSCustomObject]@{
                        Name    = $_.Name
                        Command = $_.FullName
                        Source  = "StartupFolder"
                    }
                }
        }
    }

    $list | ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 16. DISK HEALTH (SMART via WMI)
# ─────────────────────────────────────────────

def get_disk_health() -> list:
    """Physical disk status from WMI."""
    log("Disk Health")
    cmd = """
    Get-PhysicalDisk |
        Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus,
            @{N='Size_GB'; E={ [math]::Round($_.Size / 1GB, 2) }},
            BusType, UniqueId |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 17. PROGRAM FILES EXE DEEP SCAN
# ─────────────────────────────────────────────

def scan_program_files() -> list:
    """Walk Program Files directories and collect all .exe files."""
    log("Program Files EXE Scan")
    paths = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]

    found = []
    for base in paths:
        if not base or not os.path.exists(base):
            continue
        try:
            for root, dirs, files in os.walk(base):
                # Skip deep system paths to keep scan fast
                dirs[:] = [d for d in dirs if d.lower() not in
                           {"windows", "system32", "syswow64", "winsxs"}]
                for file in files:
                    if file.lower().endswith(".exe"):
                        full = os.path.join(root, file)
                        try:
                            stat = os.stat(full)
                            found.append({
                                "name": file,
                                "path": full,
                                "size_kb": round(stat.st_size / 1024, 2),
                                "modified": datetime.datetime.fromtimestamp(
                                    stat.st_mtime).strftime("%Y-%m-%d"),
                            })
                        except (PermissionError, OSError):
                            pass
        except (PermissionError, OSError):
            pass

    return found


# ─────────────────────────────────────────────
# 18. WINDOWS FEATURES
# ─────────────────────────────────────────────

def get_windows_features() -> list:
    """Optional Windows features that are enabled."""
    log("Windows Optional Features")
    cmd = """
    Get-WindowsOptionalFeature -Online |
        Where-Object { $_.State -eq "Enabled" } |
        Select-Object FeatureName, State |
        Sort-Object FeatureName |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=90)) or []


# ─────────────────────────────────────────────
# 19. USER ACCOUNTS
# ─────────────────────────────────────────────

def get_local_users() -> list:
    """Local user accounts and their status."""
    log("Local User Accounts")
    cmd = """
    Get-LocalUser |
        Select-Object Name, Enabled, FullName, Description,
            @{N='LastLogon'; E={ if ($_.LastLogon) { $_.LastLogon.ToString("yyyy-MM-dd HH:mm:ss") } else { "Never" } }},
            PasswordExpires, AccountExpires |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd)) or []


# ─────────────────────────────────────────────
# 20. EVENT LOG — RECENT ERRORS
# ─────────────────────────────────────────────

def get_recent_errors() -> list:
    """Last 50 Error/Critical events from System log."""
    log("Recent System Errors (Event Log)")
    cmd = """
    Get-EventLog -LogName System -EntryType Error,Warning -Newest 50 |
        Select-Object TimeGenerated, Source, EventID, EntryType, Message |
        ForEach-Object {
            [PSCustomObject]@{
                Time      = $_.TimeGenerated.ToString("yyyy-MM-dd HH:mm:ss")
                Source    = $_.Source
                EventID   = $_.EventID
                EntryType = $_.EntryType.ToString()
                Message   = $_.Message -replace "`r`n", " "
            }
        } |
        ConvertTo-Json
    """
    return safe_json(run_powershell(cmd, timeout=60)) or []


# ─────────────────────────────────────────────
# SUMMARY GENERATOR
# ─────────────────────────────────────────────

def build_summary(data: dict) -> dict:
    """Generate a quick-glance summary of the scan."""
    missing = data.get("missing_updates", [])
    critical = [u for u in missing if isinstance(u, dict) and
                str(u.get("Severity", "")).lower() == "critical"]
    important = [u for u in missing if isinstance(u, dict) and
                 str(u.get("Severity", "")).lower() == "important"]

    defender = data.get("defender_status", {})

    return {
        "scan_time": datetime.datetime.now().isoformat(),
        "admin_privileges": is_admin(),
        "os": data.get("system_info", {}).get("OSCaption", "Unknown"),
        "os_build": data.get("system_info", {}).get("OSBuild", "Unknown"),
        "total_patches_installed": len(data.get("installed_patches", [])),
        "total_missing_updates": len(missing),
        "critical_missing": len(critical),
        "important_missing": len(important),
        "total_apps_registry": len(data.get("registry_apps", [])),
        "total_store_apps": len(data.get("store_apps", [])),
        "total_drivers": len(data.get("drivers", [])),
        "total_services": len(data.get("services", [])),
        "total_processes": len(data.get("running_processes", [])),
        "total_exe_found": len(data.get("exe_scan", [])),
        "defender_enabled": defender.get("AntivirusEnabled", "Unknown"),
        "realtime_protection": defender.get("RealTimeProtectionEnabled", "Unknown"),
        "defender_signature_age_days": defender.get("AntivirusSignatureAge", "Unknown"),
        "firewall_profiles": len(data.get("firewall_status", [])),
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  🛡️  WINDOWS MASSIVE PATCH INFO SCANNER")
    print("=" * 60)

    if not is_admin():
        print("\n  ⚠️  WARNING: Not running as Administrator.")
        print("     Some data (drivers, features, firewall) may be incomplete.")
        print("     Re-run as Admin for full results.\n")
    else:
        print("\n  ✅  Running as Administrator — full scan enabled.\n")

    print("📡 Collecting data...\n")

    # ── Run all collectors ──────────────────────
    data = {
        "system_info":       get_system_info(),
        "installed_patches": get_installed_patches(),
        "update_history":    get_update_history(),
        "missing_updates":   get_missing_updates(),
        "defender_status":   get_defender_status(),
        "registry_apps":     get_registry_apps(),
        "store_apps":        get_store_apps(),
        "drivers":           get_drivers(),
        "services":          get_services(),
        "firewall_status":   get_firewall_status(),
        "scheduled_tasks":   get_scheduled_tasks(),
        "running_processes": get_running_processes(),
        "network_info":      get_network_info(),
        "startup_programs":  get_startup_programs(),
        "disk_health":       get_disk_health(),
        "windows_features":  get_windows_features(),
        "local_users":       get_local_users(),
        "recent_errors":     get_recent_errors(),
        "exe_scan":          scan_program_files(),
    }

    # ── Build summary after all data collected ──
    data["_summary"] = build_summary(data)

    # ── Output ──────────────────────────────────
    json_output = json.dumps(data, indent=2, default=str)

    # Save to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = Path(f"patch_info_{timestamp}.json")
    out_file.write_text(json_output, encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"  ✅  SCAN COMPLETE")
    print(f"{'=' * 60}")
    print(f"\n  📄  JSON saved to: {out_file.resolve()}")
    print(f"\n  📊  QUICK SUMMARY:")

    s = data["_summary"]
    print(f"      OS              : {s['os']} (Build {s['os_build']})")
    print(f"      Installed Patches: {s['total_patches_installed']}")
    print(f"      Missing Updates  : {s['total_missing_updates']} "
          f"(🔴 Critical: {s['critical_missing']}, 🟡 Important: {s['important_missing']})")
    print(f"      Registry Apps    : {s['total_apps_registry']}")
    print(f"      Store Apps       : {s['total_store_apps']}")
    print(f"      Drivers          : {s['total_drivers']}")
    print(f"      Running Processes: {s['total_processes']}")
    print(f"      EXE Files Found  : {s['total_exe_found']}")
    print(f"      Defender Enabled : {s['defender_enabled']}")
    print(f"      RealTime Protect : {s['realtime_protection']}")
    print()

    # Also print JSON to stdout for piping
    if "--stdout" in sys.argv:
        print(json_output)

    return data


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if platform.system() != "Windows":
        print("❌  This script must be run on Windows.")
        sys.exit(1)

    main()