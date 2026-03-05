from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"
        AGENT = "agent", "Agent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    department = models.CharField(max_length=100, blank=True)
    must_change_password = models.BooleanField(default=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    ldap_dn = models.CharField(max_length=500, blank=True, db_index=True)
    is_ldap_user = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active", "role"]),
        ]


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=200, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "-timestamp"]),
        ]
        # NOTE: This table will be partitioned by month in PostgreSQL.
        # See migrations/0002_partition_audit_log.py for the raw SQL migration.
