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
    last_seen = models.DateTimeField(null=True, blank=True)
    last_checkin_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DeviceManager()

    class Meta:
        db_table = "device"
        indexes = [
            models.Index(fields=["status", "os_family"]),
            models.Index(fields=["environment", "status"]),
            models.Index(fields=["last_seen"]),
        ]

    def __str__(self):
        return self.hostname
