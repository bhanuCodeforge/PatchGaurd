from django.db import models
import uuid

class DeviceManager(models.Manager):
    def filter_by_rules(self, rules: dict):
        qs = self.get_queryset()
        
        if "os_family" in rules:
            qs = qs.filter(os_family=rules["os_family"])
            
        if "os_version" in rules:
            qs = qs.filter(os_version__startswith=rules["os_version"])
            
        if "tags" in rules and isinstance(rules["tags"], list) and len(rules["tags"]) > 0:
            qs = qs.filter(tags__contains=rules["tags"])
            
        if "environment" in rules:
            qs = qs.filter(environment=rules["environment"])
            
        return qs


class DeviceGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    dynamic_rules = models.JSONField(default=dict, blank=True)
    is_dynamic = models.BooleanField(default=False)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_group"

    def get_devices(self):
        if self.is_dynamic:
            if not self.dynamic_rules:
                return Device.objects.none()
            return Device.objects.filter_by_rules(self.dynamic_rules)
        return self.devices.all()

    def __str__(self):
        return self.name


class Device(models.Model):
    class OSFamily(models.TextChoices):
        LINUX = "linux", "Linux"
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"

    class Environment(models.TextChoices):
        PRODUCTION = "production", "Production"
        STAGING = "staging", "Staging"
        DEVELOPMENT = "development", "Development"
        TEST = "test", "Test"

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        MAINTENANCE = "maintenance", "Maintenance"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostname = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(db_index=True)
    mac_address = models.CharField(max_length=17, blank=True)
    os_family = models.CharField(max_length=20, choices=OSFamily.choices)
    os_version = models.CharField(max_length=100, blank=True, default='')
    os_arch = models.CharField(max_length=20, default="x86_64")
    agent_version = models.CharField(max_length=20, blank=True)
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.PRODUCTION)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFLINE)
    tags = models.JSONField(default=list, blank=True)
    groups = models.ManyToManyField(DeviceGroup, related_name="devices", blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    agent_api_key = models.CharField(max_length=64, unique=True, db_index=True)
    key_created_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when the current agent_api_key was generated."
    )
    key_last_rotated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp of last automated API key rotation."
    )
    compliance_rate = models.FloatField(default=100.0, db_index=True)
    inventory_data = models.JSONField(default=dict, blank=True)
    lane_config = models.JSONField(
        default=dict, blank=True,
        help_text="Lane scheduler config: {fast_lane: {interval, concurrency, ...}, slow_lane: {...}}"
    )
    last_scan = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_checkin_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def os_name(self):
        # Human readable name if family/version combined. 
        # For windows it's usually just "Windows" but we can expand this.
        return self.get_os_family_display()

    objects = DeviceManager()

    class Meta:
        db_table = "device"
        indexes = [
            models.Index(fields=["status", "os_family"]),
            models.Index(fields=["environment", "status"]),
            models.Index(fields=["last_seen"]),
        ]


    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class DeviceEvent(models.Model):
    """
    Structured timeline event for a device — unified audit trail.

    Provides the event backbone for the "Execution & Timeline" tab in device details.
    Append-only — DO NOT UPDATE rows once inserted.
    """

    class EventType(models.TextChoices):
        HEARTBEAT = "heartbeat", "Heartbeat"
        SCAN_START = "scan_start", "Scan Started"
        SCAN_COMPLETE = "scan_complete", "Scan Complete"
        PATCH_INSTALL_START = "patch_install_start", "Patch Install Started"
        PATCH_INSTALL_SUCCESS = "patch_install_success", "Patch Installed"
        PATCH_INSTALL_FAILED = "patch_install_failed", "Patch Install Failed"
        DEPLOYMENT_START = "deployment_start", "Deployment Started"
        DEPLOYMENT_COMPLETE = "deployment_complete", "Deployment Complete"
        DEPLOYMENT_FAILED = "deployment_failed", "Deployment Failed"
        REBOOT_REQUESTED = "reboot_requested", "Reboot Requested"
        REBOOT_COMPLETE = "reboot_complete", "Reboot Complete"
        CONFIG_CHANGE = "config_change", "Config Changed"
        KEY_ROTATED = "key_rotated", "API Key Rotated"
        AGENT_ONLINE = "agent_online", "Agent Online"
        AGENT_OFFLINE = "agent_offline", "Agent Offline"
        SLOW_LANE_COMPLETE = "slow_lane_complete", "Inventory Collected"
        ERROR = "error", "Error"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=100, default="agent")
    deployment_id = models.UUIDField(null=True, blank=True, db_index=True)
    patch_id = models.UUIDField(null=True, blank=True)
    execution_lane = models.CharField(max_length=10, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "device_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "-created_at"]),
            models.Index(fields=["device", "event_type"]),
        ]

    def __str__(self):
        return f"{self.device_id} | {self.event_type} | {self.created_at}"

    @classmethod
    def record(cls, device, event_type: str, message: str, severity: str = "info",
               details: dict = None, source: str = "system", deployment_id=None,
               patch_id=None, execution_lane: str = "") -> "DeviceEvent":
        """Factory helper — create and save an event in one call."""
        return cls.objects.create(
            device=device,
            event_type=event_type,
            severity=severity,
            message=message,
            details=details or {},
            source=source,
            deployment_id=deployment_id,
            patch_id=patch_id,
            execution_lane=execution_lane,
        )
