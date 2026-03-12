from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re
import uuid
from django.utils import timezone
from .settings_models import SystemSetting


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN    = "admin",    "Admin"
        OPERATOR = "operator", "Operator"
        VIEWER   = "viewer",   "Viewer"
        AGENT    = "agent",    "Agent"

    class UserSource(models.TextChoices):
        LOCAL = "local", "Local"
        LDAP  = "ldap",  "LDAP"
        SAML  = "saml",  "SAML"

    # ── Core identity ─────────────────────────────────────────────────────────
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name  = models.CharField(max_length=200, blank=True)
    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER, db_index=True)
    department = models.CharField(max_length=100, blank=True)

    # ── Auth source ───────────────────────────────────────────────────────────
    source      = models.CharField(max_length=10, choices=UserSource.choices,
                                   default=UserSource.LOCAL, db_index=True)
    # Kept for backward compatibility – derived from source on save()
    is_ldap_user = models.BooleanField(default=False)
    ldap_dn      = models.CharField(max_length=500, blank=True, db_index=True)

    # ── Password policy ───────────────────────────────────────────────────────
    must_change_password  = models.BooleanField(default=True)
    last_password_change  = models.DateTimeField(null=True, blank=True)

    # ── Security / lockout ────────────────────────────────────────────────────
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login     = models.DateTimeField(null=True, blank=True)
    locked_until          = models.DateTimeField(null=True, blank=True)

    # ── Notification preferences ──────────────────────────────────────────────
    notify_critical = models.BooleanField(default=True)
    notify_deploy   = models.BooleanField(default=True)
    notify_digest   = models.BooleanField(default=False)

    # ── Computed properties ───────────────────────────────────────────────────
    @property
    def is_locked(self) -> bool:
        """True when the account is currently locked."""
        return bool(self.locked_until and self.locked_until > timezone.now())

    @property
    def is_service_account(self) -> bool:
        return self.role == self.Role.AGENT

    @property
    def is_password_expired(self) -> bool:
        if self.source != self.UserSource.LOCAL:
            return False
        if not self.last_password_change:
            return True
        expiry_days = 90
        return (timezone.now() - self.last_password_change).days >= expiry_days

    # ── Validation ────────────────────────────────────────────────────────────
    def clean(self):
        super().clean()
        if self.source != self.UserSource.LOCAL:
            return
        if hasattr(self, '_password') and self._password:
            self.validate_password_complexity(self._password)

    @staticmethod
    def validate_password_complexity(password: str) -> None:
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

    # ── Save hook ─────────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        # Keep is_ldap_user in sync with source for backward compat
        if self.source == self.UserSource.LDAP:
            self.is_ldap_user = True
        elif self.source in (self.UserSource.LOCAL, self.UserSource.SAML):
            self.is_ldap_user = False

        # Track password changes
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
                if old.password != self.password:
                    self.last_password_change = timezone.now()
                    self.must_change_password  = False
            except User.DoesNotExist:
                pass
        elif not self.last_password_change:
            self.last_password_change = timezone.now()

        super().save(*args, **kwargs)

    class Meta:
        db_table = "accounts_user"
        indexes  = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active", "role"]),
            models.Index(fields=["source"]),
        ]


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action        = models.CharField(max_length=200, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id   = models.UUIDField(null=True, blank=True)
    details       = models.JSONField(default=dict, blank=True)
    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    timestamp     = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        indexes  = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "-timestamp"]),
        ]
        # NOTE: This table is partitioned by month in PostgreSQL.
        # See migrations/0002_partition_audit_log.py for the raw SQL migration.
