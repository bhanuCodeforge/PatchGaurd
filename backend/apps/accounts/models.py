from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re
import uuid
from django.utils import timezone
from .settings_models import SystemSetting

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

    def clean(self):
        super().clean()
        if self.is_ldap_user:
            return
            
        # These checks are for local password updates via Django admin or views
        # Usually handled by validators, but model-level clean ensures 1.0 parity
        if hasattr(self, '_password') and self._password:
            self.validate_password_complexity(self._password)

    def validate_password_complexity(self, password):
        if len(password) < 12:
            raise ValidationError("Password must be at least 12 characters.")
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError("Password must contain at least one special character.")

    def save(self, *args, **kwargs):
        # Update last_password_change if password was just set
        if self.pk:
            old_user = User.objects.get(pk=self.pk)
            if old_user.password != self.password:
                self.last_password_change = timezone.now()
                self.must_change_password = False
        elif not self.last_password_change:
             self.last_password_change = timezone.now()
             
        super().save(*args, **kwargs)

    @property
    def is_password_expired(self):
        if self.is_ldap_user:
            return False
        if not self.last_password_change:
            return True
        expiry_days = 90
        return (timezone.now() - self.last_password_change).days >= expiry_days

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
