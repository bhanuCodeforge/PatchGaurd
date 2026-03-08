from django.db import models
import uuid

class Patch(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Status(models.TextChoices):
        IMPORTED = "imported", "Imported"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor_id = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IMPORTED)
    vendor = models.CharField(max_length=100)
    kb_article = models.URLField(blank=True)
    cve_ids = models.JSONField(default=list, blank=True)
    cvss_score = models.FloatField(null=True, blank=True)
    applicable_os = models.JSONField(default=list)
    package_name = models.CharField(max_length=200, blank=True)
    package_version = models.CharField(max_length=100, blank=True)
    file_url = models.URLField(blank=True)
    file_hash_sha256 = models.CharField(max_length=64, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    supersedes = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="superseded_by")
    requires_reboot = models.BooleanField(default=False)
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    status_notes = models.TextField(blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patch"
        ordering = ["-released_at"]
        indexes = [
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["-released_at"]),
        ]

    def __str__(self):
        return f"{self.vendor_id} - {self.title}"


class DevicePatchStatus(models.Model):
    class State(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not Applicable"
        MISSING = "missing", "Missing"
        PENDING = "pending", "Pending"
        DOWNLOADING = "downloading", "Downloading"
        INSTALLING = "installing", "Installing"
        INSTALLED = "installed", "Installed"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey("inventory.Device", on_delete=models.CASCADE, related_name="patch_statuses")
    patch = models.ForeignKey(Patch, on_delete=models.CASCADE, related_name="device_statuses")
    state = models.CharField(max_length=20, choices=State.choices, default=State.MISSING)
    installed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "device_patch_status"
        unique_together = [("device", "patch")]
        indexes = [
            models.Index(fields=["device", "state"]),
            models.Index(fields=["patch", "state"]),
            models.Index(fields=["state", "-last_attempt"]),
        ]

    def __str__(self):
        return f"{self.device.hostname} - {self.patch.vendor_id} - {self.state}"
