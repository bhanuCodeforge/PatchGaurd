#!/usr/bin/env python3
"""
PatchGuard Seed Data Script
Populates the dev database with realistic test data so the entire UI can be verified locally.
"""
import os
import sys
import django
import uuid
from datetime import datetime, timedelta, timezone

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.contrib.auth import get_user_model
from apps.inventory.models import Device, DeviceGroup  # type: ignore[import]
from apps.patches.models import Patch, DevicePatchStatus  # type: ignore[import]
from apps.deployments.models import Deployment  # type: ignore[import]

User = get_user_model()

NOW = datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# 1. USERS
# ──────────────────────────────────────────────
def seed_users():
    users = [
        dict(username="admin",    email="admin@patchguard.local",    password="Admin@123456",    role="admin",    first_name="Admin",   last_name="User",     is_superuser=True, is_staff=True),
        dict(username="operator", email="operator@patchguard.local", password="Operator@123456", role="operator", first_name="Alice",   last_name="operator"),
        dict(username="viewer",   email="viewer@patchguard.local",   password="Viewer@123456",   role="viewer",   first_name="Bob",     last_name="viewer"),
    ]
    for u in users:
        is_super = u.pop("is_superuser", False)
        is_staff  = u.pop("is_staff", False)
        pw = u.pop("password")
        role = u.pop("role")

        obj, new = User.objects.get_or_create(username=u["username"], defaults=u)
        # Always ensure password, role and flags are correct (idempotent re-seed)
        obj.set_password(pw)
        obj.role = role
        obj.is_superuser = is_super
        obj.is_staff = is_staff
        obj.save(update_fields=["password", "role", "is_superuser", "is_staff"])
        print(f"  {'Created' if new else 'Refreshed'} user: {obj.username}  (password: {pw}  role: {role})")
    return User.objects.filter(username="admin").first()


# ──────────────────────────────────────────────
# 2. DEVICE GROUPS
# ──────────────────────────────────────────────
def seed_groups():
    groups_data = [
        {"name": "All Windows Devices",  "description": "Windows fleet",         "dynamic_rules": {"os_family": "windows"}, "is_dynamic": True},
        {"name": "Linux Servers",         "description": "Linux production hosts", "dynamic_rules": {"os_family": "linux"},   "is_dynamic": True},
        {"name": "Production Fleet",      "description": "All production env",     "dynamic_rules": {"environment": "production"}, "is_dynamic": True},
        {"name": "Staging Environment",   "description": "Staging servers",        "dynamic_rules": {"environment": "staging"},    "is_dynamic": True},
    ]
    groups = []
    for gd in groups_data:
        g, created = DeviceGroup.objects.get_or_create(name=gd["name"], defaults=gd)
        groups.append(g)
        print(f"  {'Created' if created else 'Found'} group: {g.name}")
    return groups


# ──────────────────────────────────────────────
# 3. DEVICES
# ──────────────────────────────────────────────
def seed_devices():
    devices_data = [
        {
            "hostname": "web-prod-01",
            "ip_address": "10.0.1.10",
            "os_family": Device.OSFamily.LINUX,
            "os_version": "Ubuntu 22.04.3 LTS",
            "environment": Device.Environment.PRODUCTION,
            "status": Device.Status.ONLINE,
            "agent_api_key": "AGENT_SECRET_KEY_PLACEHOLDER",
            "agent_version": "1.0.0",
            "tags": ["web", "nginx", "critical"],
            "last_seen": NOW - timedelta(minutes=2),
        },
        {
            "hostname": "web-prod-02",
            "ip_address": "10.0.1.11",
            "os_family": Device.OSFamily.LINUX,
            "os_version": "Ubuntu 22.04.3 LTS",
            "environment": Device.Environment.PRODUCTION,
            "status": Device.Status.ONLINE,
            "agent_api_key": "agentkey_web_prod_02_0000000000",
            "agent_version": "1.0.0",
            "tags": ["web", "nginx"],
            "last_seen": NOW - timedelta(minutes=5),
        },
        {
            "hostname": "db-prod-01",
            "ip_address": "10.0.2.10",
            "os_family": Device.OSFamily.LINUX,
            "os_version": "Rocky Linux 9.2",
            "environment": Device.Environment.PRODUCTION,
            "status": Device.Status.ONLINE,
            "agent_api_key": "agentkey_db_prod_01_000000000000",
            "agent_version": "1.0.0",
            "tags": ["database", "postgres", "critical"],
            "last_seen": NOW - timedelta(minutes=1),
        },
        {
            "hostname": "win-workstation-01",
            "ip_address": "192.168.1.50",
            "os_family": Device.OSFamily.WINDOWS,
            "os_version": "Windows 11 Pro 23H2",
            "environment": Device.Environment.DEVELOPMENT,
            "status": Device.Status.ONLINE,
            "agent_api_key": "agentkey_win_ws01_000000000000000",
            "agent_version": "1.0.0",
            "tags": ["workstation", "dev"],
            "last_seen": NOW - timedelta(minutes=10),
        },
        {
            "hostname": "win-server-prod-01",
            "ip_address": "10.0.3.10",
            "os_family": Device.OSFamily.WINDOWS,
            "os_version": "Windows Server 2022",
            "environment": Device.Environment.PRODUCTION,
            "status": Device.Status.MAINTENANCE,
            "agent_api_key": "agentkey_win_srv01_00000000000000",
            "agent_version": "1.0.0",
            "tags": ["iis", "windows-server"],
            "last_seen": NOW - timedelta(hours=2),
        },
        {
            "hostname": "staging-app-01",
            "ip_address": "172.16.0.10",
            "os_family": Device.OSFamily.LINUX,
            "os_version": "Debian 12 (Bookworm)",
            "environment": Device.Environment.STAGING,
            "status": Device.Status.ONLINE,
            "agent_api_key": "agentkey_staging_app01_0000000000",
            "agent_version": "1.0.0",
            "tags": ["staging", "app"],
            "last_seen": NOW - timedelta(minutes=8),
        },
        {
            "hostname": "mac-dev-01",
            "ip_address": "192.168.1.100",
            "os_family": Device.OSFamily.MACOS,
            "os_version": "macOS Sonoma 14.3",
            "environment": Device.Environment.DEVELOPMENT,
            "status": Device.Status.OFFLINE,
            "agent_api_key": "agentkey_mac_dev01_000000000000000",
            "agent_version": "1.0.0",
            "tags": ["developer", "macos"],
            "last_seen": NOW - timedelta(hours=6),
        },
    ]

    devices = []
    for dd in devices_data:
        dev, created = Device.objects.update_or_create(
            hostname=dd["hostname"],
            defaults=dd,
        )
        devices.append(dev)
        print(f"  {'Created' if created else 'Updated'} device: {dev.hostname}")
    return devices


# ──────────────────────────────────────────────
# 4. PATCHES
# ──────────────────────────────────────────────
def seed_patches():
    patches_data = [
        {
            "vendor_id": "MS24-001-KB5034441",
            "title": "2024-01 Cumulative Update for Windows 11 (KB5034441)",
            "description": "Security and quality update for Windows 11. Fixes critical RCE vulnerability in TCP/IP stack.",
            "severity": Patch.Severity.CRITICAL,
            "status": Patch.Status.APPROVED,
            "vendor": "Microsoft",
            "cve_ids": ["CVE-2024-21307", "CVE-2024-21318"],
            "applicable_os": ["windows"],
            "requires_reboot": True,
            "released_at": NOW - timedelta(days=14),
        },
        {
            "vendor_id": "MS24-002-KB5034123",
            "title": "2024-01 Security Update for .NET Framework (KB5034123)",
            "description": "Addresses elevation of privilege vulnerabilities in .NET Framework 4.8.1.",
            "severity": Patch.Severity.HIGH,
            "status": Patch.Status.APPROVED,
            "vendor": "Microsoft",
            "cve_ids": ["CVE-2024-20656"],
            "applicable_os": ["windows"],
            "requires_reboot": False,
            "released_at": NOW - timedelta(days=14),
        },
        {
            "vendor_id": "MS24-003-KB5034765",
            "title": "Windows Server 2022 Servicing Stack Update (KB5034765)",
            "description": "Servicing stack update required before applying critical security updates.",
            "severity": Patch.Severity.MEDIUM,
            "status": Patch.Status.IMPORTED,
            "vendor": "Microsoft",
            "cve_ids": [],
            "applicable_os": ["windows"],
            "requires_reboot": False,
            "released_at": NOW - timedelta(days=7),
        },
        {
            "vendor_id": "UBUNTU-USN-6609-1",
            "title": "USN-6609-1: Linux kernel vulnerabilities",
            "description": "It was discovered that the Linux kernel did not properly handle page table updates in certain situations — multiple vulnerabilities fixed.",
            "severity": Patch.Severity.CRITICAL,
            "status": Patch.Status.APPROVED,
            "vendor": "Canonical",
            "cve_ids": ["CVE-2024-0193", "CVE-2024-1085"],
            "applicable_os": ["linux"],
            "requires_reboot": True,
            "released_at": NOW - timedelta(days=10),
        },
        {
            "vendor_id": "UBUNTU-USN-6560-1",
            "title": "USN-6560-1: OpenSSH vulnerability",
            "description": "OpenSSH was updated to fix a race condition that could allow unauthorized access.",
            "severity": Patch.Severity.HIGH,
            "status": Patch.Status.APPROVED,
            "vendor": "Canonical",
            "cve_ids": ["CVE-2023-51385"],
            "applicable_os": ["linux"],
            "requires_reboot": False,
            "released_at": NOW - timedelta(days=21),
        },
        {
            "vendor_id": "RHEL-RHSA-2024-0752",
            "title": "RHSA-2024:0752 Important: bind security update",
            "description": "Security update for bind (DNS server) fixing a potential denial of service.",
            "severity": Patch.Severity.HIGH,
            "status": Patch.Status.REVIEWED,
            "vendor": "Red Hat",
            "cve_ids": ["CVE-2023-50387"],
            "applicable_os": ["linux"],
            "requires_reboot": False,
            "released_at": NOW - timedelta(days=5),
        },
        {
            "vendor_id": "APPLE-SECURITY-2024-01-22",
            "title": "macOS Sonoma 14.3 Security Update",
            "description": "Security update addressing vulnerabilities in Kernel, Safari, and WebKit.",
            "severity": Patch.Severity.CRITICAL,
            "status": Patch.Status.IMPORTED,
            "vendor": "Apple",
            "cve_ids": ["CVE-2024-23222", "CVE-2024-23218"],
            "applicable_os": ["macos"],
            "requires_reboot": True,
            "released_at": NOW - timedelta(days=3),
        },
        {
            "vendor_id": "UBUNTU-USN-6640-1",
            "title": "USN-6640-1: curl vulnerabilities",
            "description": "Multiple vulnerabilities in curl were fixed including heap buffer overflow.",
            "severity": Patch.Severity.MEDIUM,
            "status": Patch.Status.IMPORTED,
            "vendor": "Canonical",
            "cve_ids": ["CVE-2024-0853"],
            "applicable_os": ["linux"],
            "requires_reboot": False,
            "released_at": NOW - timedelta(days=1),
        },
    ]

    patches = []
    for pd in patches_data:
        p, created = Patch.objects.update_or_create(
            vendor_id=pd["vendor_id"],
            defaults=pd,
        )
        patches.append(p)
        print(f"  {'Created' if created else 'Updated'} patch: {p.vendor_id}")
    return patches


# ──────────────────────────────────────────────
# 5. DEVICE-PATCH STATUS
# ──────────────────────────────────────────────
def seed_patch_statuses(devices, patches):
    # Map patches roughly by OS relevance
    linux_patches = [p for p in patches if "linux" in p.applicable_os]
    windows_patches = [p for p in patches if "windows" in p.applicable_os]
    mac_patches = [p for p in patches if "macos" in p.applicable_os]

    assignments = []
    for dev in devices:
        if dev.os_family == Device.OSFamily.LINUX:
            relevant = linux_patches
        elif dev.os_family == Device.OSFamily.WINDOWS:
            relevant = windows_patches
        elif dev.os_family == Device.OSFamily.MACOS:
            relevant = mac_patches
        else:
            continue

        states = [
            DevicePatchStatus.State.INSTALLED,
            DevicePatchStatus.State.MISSING,
            DevicePatchStatus.State.PENDING,
            DevicePatchStatus.State.FAILED,
        ]
        for i, patch in enumerate(relevant):
            state = states[i % len(states)]
            dps, _ = DevicePatchStatus.objects.get_or_create(
                device=dev,
                patch=patch,
                defaults={"state": state}
            )
            assignments.append(dps)

    print(f"  Seeded {len(assignments)} device-patch status entries.")
    return assignments


# ──────────────────────────────────────────────
# 6. DEPLOYMENT
# ──────────────────────────────────────────────
def seed_deployment(admin_user, devices, patches):
    approved_patches = [p for p in patches if p.status == Patch.Status.APPROVED]
    if not approved_patches:
        print("  No approved patches available for deployment.")
        return

    dep, created = Deployment.objects.get_or_create(
        name="January 2024 Critical Security Rollout",
        defaults={
            "description": "Rolling deployment of all critical/high severity patches approved in January 2024.",
            "status": Deployment.Status.SCHEDULED,
            "strategy": Deployment.Strategy.ROLLING,
            "wave_size": 2,
            "wave_delay_minutes": 15,
            "max_failure_percentage": 10.0,
            "requires_reboot": True,
            "total_devices": len(devices),
            "scheduled_at": NOW + timedelta(hours=2),
            "created_by": admin_user,
        }
    )
    if created:
        dep.patches.set(approved_patches[:3])
        dep.save()
        print(f"  Created deployment: {dep.name}")
    else:
        print(f"  Deployment already exists: {dep.name}")

    return dep


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def seed_data():
    print("\n========================================")
    print("  PatchGuard - Seeding Database")
    print("========================================\n")

    print("[1/6] Users...")
    admin = seed_users()

    print("\n[2/6] Device Groups...")
    seed_groups()

    print("\n[3/6] Devices...")
    devices = seed_devices()

    print("  Device groups are dynamic — auto-resolved by rules.")

    print("\n[4/6] Patches...")
    patches = seed_patches()

    print("\n[5/6] Device-Patch Status...")
    seed_patch_statuses(devices, patches)

    print("\n[6/6] Deployments...")
    seed_deployment(admin, devices, patches)

    print("\n========================================")
    print("  Seeding complete!")
    print("========================================")
    print("\nLogin credentials:")
    print("  admin    / Admin@123456    (superuser)")
    print("  operator / Operator@123456 (operator)")
    print("  viewer   / Viewer@123456   (viewer)")
    print("\nServices:")
    print("  Backend API:  http://localhost:8000/api/docs/")
    print("  Frontend:     http://localhost:4200/")
    print("  Realtime WS:  http://localhost:8001/docs")


if __name__ == "__main__":
    seed_data()
