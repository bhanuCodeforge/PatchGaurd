from django.db import models
import uuid

class Deployment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        ROLLING_BACK = "rolling_back", "Rolling Back"

    class Strategy(models.TextChoices):
        IMMEDIATE = "immediate", "Immediate"
        CANARY = "canary", "Canary"
        ROLLING = "rolling", "Rolling"
        MAINTENANCE = "maintenance", "Maintenance Window"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    patches = models.ManyToManyField("patches.Patch", related_name="deployments")
    target_groups = models.ManyToManyField("inventory.DeviceGroup", related_name="deployments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    strategy = models.CharField(max_length=20, choices=Strategy.choices, default=Strategy.ROLLING)
    
    canary_percentage = models.IntegerField(default=5)
    wave_size = models.IntegerField(default=50)
    wave_delay_minutes = models.IntegerField(default=15)
    max_failure_percentage = models.FloatField(default=5.0)
    requires_reboot = models.BooleanField(default=False)
    
    maintenance_window_start = models.TimeField(null=True, blank=True)
    maintenance_window_end = models.TimeField(null=True, blank=True)
    
    total_devices = models.IntegerField(default=0)
    completed_devices = models.IntegerField(default=0)
    failed_devices = models.IntegerField(default=0)
    current_wave = models.IntegerField(default=0)
    
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_deployments")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="approved_deployments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deployment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["scheduled_at"]),
        ]

    def __str__(self):
        return self.name

    @property
    def progress_percentage(self):
        if self.total_devices == 0:
            return 0
        return int((self.completed_devices / self.total_devices) * 100)

    @property
    def failure_rate(self):
        if self.total_devices == 0:
            return 0.0
        return (self.failed_devices / self.total_devices) * 100.0

    @property
    def is_active(self):
        return self.status in [self.Status.IN_PROGRESS, self.Status.PAUSED]


class DeploymentTarget(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="targets")
    device = models.ForeignKey("inventory.Device", on_delete=models.CASCADE, related_name="deployment_targets")
    wave_number = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True)

    class Meta:
        db_table = "deployment_target"
        unique_together = [("deployment", "device")]
        indexes = [
            models.Index(fields=["deployment", "wave_number", "status"]),
            models.Index(fields=["device", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.deployment.name} - {self.device.hostname}"


class DeploymentEvent(models.Model):
    """
    Immutable audit-trail event for a DeploymentTarget lifecycle transition.

    Task 11.5 — Event Sourcing.

    Every meaningful state change on a DeploymentTarget appends one row here.
    The counters on Deployment (completed_devices, failed_devices) are the
    primary fast-path for UI; this table provides the audit trail and is the
    source of truth for re-computing counters under load tests.

    DO NOT UPDATE these rows once inserted – treat as append-only.
    """

    class EventType(models.TextChoices):
        QUEUED      = "queued",      "Device Queued"
        STARTED     = "started",     "Patching Started"
        COMPLETED   = "completed",   "Patching Completed"
        FAILED      = "failed",      "Patching Failed"
        SKIPPED     = "skipped",     "Device Skipped (Preflight)"
        CANCELLED   = "cancelled",   "Deployment Cancelled"
        WAVE_START  = "wave_start",  "Wave Started"
        WAVE_DONE   = "wave_done",   "Wave Completed"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deployment  = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="events", db_index=True)
    target      = models.ForeignKey(DeploymentTarget, on_delete=models.CASCADE, related_name="events",
                                    null=True, blank=True, db_index=True)
    device      = models.ForeignKey("inventory.Device", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="deployment_events")
    event_type  = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    wave_number = models.IntegerField(null=True, blank=True)
    detail      = models.JSONField(default=dict, blank=True)   # error message, patch IDs, etc.
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "deployment_event"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["deployment", "event_type", "-occurred_at"]),
            models.Index(fields=["deployment", "device", "-occurred_at"]),
        ]

    def __str__(self):
        return f"{self.deployment_id} | {self.event_type} | {self.occurred_at}"

    @classmethod
    def record(cls, deployment, event_type: str, target=None, device=None,
               wave_number: int = None, detail: dict = None) -> "DeploymentEvent":
        """Factory helper — create and save an event in one call."""
        return cls.objects.create(
            deployment=deployment,
            target=target,
            device=device or (target.device if target else None),
            event_type=event_type,
            wave_number=wave_number,
            detail=detail or {},
        )
