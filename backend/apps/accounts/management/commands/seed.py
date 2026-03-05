import random
import uuid
import secrets
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User, AuditLog
from apps.inventory.models import Device, DeviceGroup
from apps.patches.models import Patch, DevicePatchStatus
from apps.deployments.models import Deployment, DeploymentTarget

class Command(BaseCommand):
    help = "Seed database with sample device, patch, and deployment data."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
        parser.add_argument("--minimal", action="store_true", help="Create a minimal data set (20 devices)")

    @transaction.atomic
    def handle(self, *args, **options):
        clear = options["clear"]
        minimal = options["minimal"]

        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            DeploymentTarget.objects.all().delete()
            Deployment.objects.all().delete()
            DevicePatchStatus.objects.all().delete()
            Patch.objects.all().delete()
            Device.objects.all().delete()
            DeviceGroup.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            AuditLog.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Starting database seed..."))
        
        # 1. Create Users
        self.stdout.write("Creating standard users...")
        admin_user, _ = User.objects.get_or_create(
            username="jdoe",
            email="jdoe@internal.corp",
            defaults={"role": "admin", "department": "IT Operations", "is_staff": True}
        )
        admin_user.set_password("admin")
        admin_user.save()

        operator_user, _ = User.objects.get_or_create(
            username="mrodriguez",
            email="mrodriguez@internal.corp",
            defaults={"role": "operator", "department": "Security Team"}
        )
        operator_user.set_password("operator")
        operator_user.save()

        viewer_user, _ = User.objects.get_or_create(
            username="lpark",
            email="lpark@internal.corp",
            defaults={"role": "viewer", "department": "Compliance"}
        )
        viewer_user.set_password("viewer")
        viewer_user.save()

        # 2. Create Device Groups
        group_names = [
            "Production Linux servers", "Production Windows servers",
            "Staging environment", "Development machines",
            "macOS workstations", "Database servers"
        ]
        groups = {}
        for name in group_names:
            group, _ = DeviceGroup.objects.get_or_create(name=name)
            groups[name] = group

        # 3. Create Devices
        num_devices = 20 if minimal else 200
        self.stdout.write(f"Creating {num_devices} devices...")
        
        os_options = [
            ("linux", ["Ubuntu 22.04", "Ubuntu 24.04", "RHEL 9.3"]),
            ("windows", ["Server 2019", "Server 2022"]),
            ("macos", ["14.4", "14.5"])
        ]
        
        envs = ["production", "staging", "development", "test"]
        statuses = ["online", "online", "online", "online", "online", "online", "online", "online", "online", "offline", "maintenance"]
        all_tags = ["web", "api", "database", "monitoring", "CI", "cache", "AD", "file-server"]

        devices = []
        for i in range(num_devices):
            os_family, versions = random.choice(os_options)
            os_version = random.choice(versions)
            env = random.choice(envs)
            
            # Weighted distribution for hostnames
            prefix = "web" if "web" in os_version.lower() else ("db" if i % 5 == 0 else "srv")
            hostname = f"{prefix}-{env}-{i:02d}"
            
            device = Device.objects.create(
                hostname=hostname,
                ip_address=f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}",
                os_family=os_family,
                os_version=os_version,
                environment=env,
                status=random.choice(statuses),
                tags=random.sample(all_tags, random.randint(1, 3)),
                agent_api_key=secrets.token_hex(32),
                last_seen=timezone.now() - timedelta(minutes=random.randint(0, 10000)) if random.random() > 0.1 else None,
                metadata={
                    "cpu_cores": random.choice([2, 4, 8, 16]),
                    "ram_gb": random.choice([4, 8, 16, 32, 64]),
                    "disk_gb": random.choice([50, 100, 500, 1000])
                }
            )
            # Assign to groups
            if os_family == "linux" and "prod" in env:
                device.groups.add(groups["Production Linux servers"])
            elif os_family == "windows" and "prod" in env:
                device.groups.add(groups["Production Windows servers"])
            
            if "staging" in env:
                device.groups.add(groups["Staging environment"])
            elif "dev" in env:
                device.groups.add(groups["Development machines"])
            
            if "db" in hostname:
                device.groups.add(groups["Database servers"])
                
            devices.append(device)

        # 4. Create Patches
        num_patches = 10 if minimal else 30
        self.stdout.write(f"Creating {num_patches} patches...")
        
        patch_vendors = ["Canonical", "Microsoft", "Red Hat"]
        severities = ["critical", "high", "medium", "low"]
        
        patches = []
        for i in range(num_patches):
            severity = random.choice(severities)
            vendor = random.choice(patch_vendors)
            v_id = f"CVE-2025-{random.randint(1000, 9999)}" if vendor != "Microsoft" else f"KB50{random.randint(10000, 99999)}"
            
            patch = Patch.objects.create(
                vendor_id=v_id,
                title=f"{vendor} Security Update for {severity.capitalize()} Vulnerability",
                severity=severity,
                vendor=vendor,
                status=random.choice(["imported", "reviewed", "approved"]),
                released_at=timezone.now() - timedelta(days=random.randint(1, 60)),
                applicable_os=[versions[0] for _, versions in os_options] # Simple approximation
            )
            patches.append(patch)

        # 5. Create DevicePatchStatus
        self.stdout.write("Generating patch status records...")
        for device in devices:
            # Each device has a subset of patches
            for patch in random.sample(patches, min(len(patches), 15)):
                r = random.random()
                if r < 0.85:
                    state = "installed"
                    installed_at = timezone.now() - timedelta(days=random.randint(1, 30))
                elif r < 0.93:
                    state = "missing"
                    installed_at = None
                elif r < 0.98:
                    state = "pending"
                    installed_at = None
                else:
                    state = "failed"
                    installed_at = None
                
                DevicePatchStatus.objects.create(
                    device=device,
                    patch=patch,
                    state=state,
                    installed_at=installed_at
                )

        # 6. Create Deployments
        self.stdout.write("Creating 5 sample deployments...")
        deployment_statuses = ["completed", "in_progress", "scheduled", "draft", "failed"]
        for s in deployment_statuses:
            d = Deployment.objects.create(
                name=f"{s.capitalize()} Rollout {timezone.now().strftime('%Y-%m-%d')}",
                status=s,
                strategy="rolling",
                created_by=admin_user,
                total_devices=num_devices // 5,
                scheduled_at=timezone.now() + timedelta(hours=12) if s == "scheduled" else None
            )
            # Add some patches to deployment
            d.patches.add(*random.sample(patches, 3))
            
            # Create targets
            target_devices = random.sample(devices, d.total_devices)
            for t_dev in target_devices:
                ts = "completed" if s == "completed" else "queued"
                if s == "failed" and random.random() > 0.5:
                    ts = "failed"
                
                DeploymentTarget.objects.create(
                    deployment=d,
                    device=t_dev,
                    status=ts,
                    wave_number=random.randint(1, 4)
                )

        # 7. Audit Logs
        self.stdout.write("Generating 100 audit log entries...")
        actions = ["POST /api/v1/targets/", "PUT /api/v1/patches/", "DELETE /api/v1/devices/", "POST /api/v1/deployments/"]
        for _ in range(100):
            AuditLog.objects.create(
                user=random.choice([admin_user, operator_user, viewer_user]),
                action=random.choice(actions),
                resource_type=random.choice(["device", "patch", "deployment"]),
                ip_address=f"192.168.1.{random.randint(2, 254)}",
                details={"status_code": 200}
            )

        self.stdout.write(self.style.SUCCESS(
            "\nSeed complete! \n"
            f"- Users: 3\n"
            f"- Device Groups: {len(groups)}\n"
            f"- Devices: {num_devices}\n"
            f"- Patches: {num_patches}\n"
            f"- Deployments: 5\n"
        ))
