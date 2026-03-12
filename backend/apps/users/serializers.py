"""
apps.users.serializers
──────────────────────
All DRF serializers for the users app.

Hierarchy:
  UserListSerializer        – compact, used for GET /users/ list
  UserDetailSerializer      – full representation, GET /users/{id}/
  AdminUserCreateSerializer – POST /users/ (admin creates any role)
  AdminUserUpdateSerializer – PATCH /users/{id}/ (admin updates)
  SAMLConfigSerializer      – CRUD for SAMLConfiguration
  AuditLogSerializer        – extended audit log output
"""

import re
import secrets
import string

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import AuditLog
from apps.users.models import SAMLConfiguration

User = get_user_model()


# ── Helpers ───────────────────────────────────────────────────────────────────

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()"


def _generate_temp_password(length: int = 16) -> str:
    """Generate a random password guaranteed to meet complexity rules."""
    while True:
        pwd = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if (re.search(r"[A-Z]", pwd) and re.search(r"[a-z]", pwd)
                and re.search(r"\d", pwd) and re.search(r"[^A-Za-z0-9]", pwd)):
            return pwd


def _validate_password_complexity(value: str) -> str:
    errors = []
    if len(value) < 12:
        errors.append("Minimum 12 characters.")
    if not re.search(r"[A-Z]", value):
        errors.append("At least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        errors.append("At least one lowercase letter.")
    if not re.search(r"\d", value):
        errors.append("At least one digit.")
    if not re.search(r"[^A-Za-z0-9]", value):
        errors.append("At least one special character.")
    if errors:
        raise ValidationError(errors)
    return value


# ── User serializers ──────────────────────────────────────────────────────────

class UserListSerializer(serializers.ModelSerializer):
    """Compact serializer for list views and stat cards (frontend user table)."""
    is_locked           = serializers.BooleanField(read_only=True)
    is_service_account  = serializers.BooleanField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "full_name",
            "role", "department", "source",
            "is_active", "is_locked", "is_service_account",
            "last_login", "failed_login_attempts", "last_failed_login",
            "notify_critical", "notify_deploy", "notify_digest",
            "date_joined",
        ]
        read_only_fields = fields  # list serializer is read-only


class UserDetailSerializer(serializers.ModelSerializer):
    """Full user representation including lockout metadata."""
    is_locked           = serializers.BooleanField(read_only=True)
    is_service_account  = serializers.BooleanField(read_only=True)
    is_password_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "full_name",
            "role", "department", "source",
            "is_active", "is_locked", "is_service_account",
            "last_login", "failed_login_attempts", "last_failed_login",
            "locked_until", "must_change_password", "is_password_expired",
            "notify_critical", "notify_deploy", "notify_digest",
            "is_ldap_user", "ldap_dn",
            "date_joined",
        ]
        read_only_fields = [
            "id", "last_login", "date_joined", "is_ldap_user",
            "is_locked", "is_service_account", "is_password_expired",
        ]


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Used by administrators to create any user with any role.
    The public RegisterView (accounts app) still uses UserCreateSerializer
    which enforces role='viewer'.
    """
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text="Required for source=local. Leave blank for LDAP/SAML users.",
    )
    force_password_change = serializers.BooleanField(
        write_only=True, required=False, default=True,
    )

    class Meta:
        model  = User
        fields = [
            "username", "email", "full_name",
            "role", "department", "source",
            "password", "force_password_change",
            "notify_critical", "notify_deploy", "notify_digest",
        ]

    # ── Field-level validation ─────────────────────────────────────────────────
    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise ValidationError("A user with this username already exists.")
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        source   = attrs.get("source", User.UserSource.LOCAL)
        password = attrs.get("password", "")

        if source == User.UserSource.LOCAL and not password:
            raise ValidationError(
                {"password": "A password is required when source is 'local'."}
            )
        if password:
            _validate_password_complexity(password)
        return attrs

    def create(self, validated_data: dict) -> User:
        password             = validated_data.pop("password", None)
        force_change         = validated_data.pop("force_password_change", True)
        source               = validated_data.get("source", User.UserSource.LOCAL)

        user = User(**validated_data)
        user.must_change_password = force_change

        if source == User.UserSource.LOCAL and password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Partial-update serializer for PATCH /users/{id}/.
    Email is deliberately excluded (immutable after creation).
    """

    class Meta:
        model  = User
        fields = [
            "full_name", "role", "department", "source",
            "is_active",
            "notify_critical", "notify_deploy", "notify_digest",
        ]

    def validate_role(self, value: str) -> str:
        valid = [r[0] for r in User.Role.choices]
        if value not in valid:
            raise ValidationError(f"Invalid role. Choices: {valid}")
        return value


# ── SAML Configuration serializer ─────────────────────────────────────────────

class SAMLConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SAMLConfiguration
        fields = [
            "id", "name",
            "sp_entity_id",
            "idp_entity_id", "idp_sso_url", "idp_slo_url", "idp_x509_cert",
            "attribute_mapping",
            "default_role", "auto_create_users", "auto_update_attrs",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_idp_x509_cert(self, value: str) -> str:
        # Strip PEM headers if the user pasted them — python3-saml wants raw base64
        value = value.strip()
        value = value.replace("-----BEGIN CERTIFICATE-----", "")
        value = value.replace("-----END CERTIFICATE-----", "")
        value = "".join(value.split())  # collapse whitespace
        if not value:
            raise ValidationError("Certificate cannot be empty.")
        return value


# ── Audit Log serializer ──────────────────────────────────────────────────────

class AuditLogSerializer(serializers.ModelSerializer):
    actor      = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()
    status     = serializers.SerializerMethodField()

    class Meta:
        model  = AuditLog
        fields = [
            "id", "actor", "actor_role",
            "action", "resource_type", "resource_id",
            "details", "ip_address", "timestamp", "status",
        ]

    def get_actor(self, obj: AuditLog) -> str:
        return obj.user.username if obj.user else "system"

    def get_actor_role(self, obj: AuditLog) -> str:
        return getattr(obj.user, "role", "system") if obj.user else "system"

    def get_status(self, obj: AuditLog) -> str:
        return "success"


# ── CSV row serializer (for import validation) ────────────────────────────────

class UserCSVRowSerializer(serializers.Serializer):
    """Validates a single row from a CSV import file."""
    username   = serializers.CharField(max_length=150)
    email      = serializers.EmailField()
    full_name  = serializers.CharField(max_length=200, required=False, allow_blank=True)
    role       = serializers.ChoiceField(choices=User.Role.choices)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source     = serializers.ChoiceField(
        choices=User.UserSource.choices, required=False, default="local"
    )
    password   = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Required for source=local rows. Leave blank for LDAP/SAML.",
    )

    def validate(self, attrs: dict) -> dict:
        if attrs.get("source", "local") == "local" and not attrs.get("password"):
            raise ValidationError(
                {"password": "Password is required for local users."}
            )
        if attrs.get("password"):
            _validate_password_complexity(attrs["password"])
        return attrs
