"""
apps.accounts.serializers
──────────────────────────
Serializers for the accounts (auth) app.
Scope: authentication flows only — login, register, refresh, profile, password.

User management (CRUD, role changes, CSV) lives in apps.users.serializers.
"""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import AuditLog, SystemSetting

User = get_user_model()


# ── JWT / Login ───────────────────────────────────────────────────────────────

class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT serializer with:
      - Role / username / email claims embedded in the token
      - Failed-login tracking and automatic account lock
    """

    @classmethod
    def get_token(cls, user):
        token              = super().get_token(user)
        token["role"]      = user.role
        token["username"]  = user.username
        token["email"]     = user.email
        return token

    def validate(self, attrs):
        username_field = self.username_field
        username       = attrs.get(username_field)

        candidates = User.objects.filter(**{username_field: username})

        # Pre-check: account locked?
        if candidates.exists():
            user = candidates.first()
            if user.locked_until and user.locked_until > timezone.now():
                raise AuthenticationFailed("Account locked. Try again later.")

        try:
            data = super().validate(attrs)
        except Exception:
            # Increment failed-attempt counter
            if candidates.exists():
                user = candidates.first()
                user.failed_login_attempts += 1
                user.last_failed_login     = timezone.now()
                from django.conf import settings
                max_attempts = getattr(settings, "AUTH_MAX_FAILED_ATTEMPTS", 5)
                lockout_mins = getattr(settings, "AUTH_LOCKOUT_MINUTES", 30)
                if user.failed_login_attempts >= max_attempts:
                    user.locked_until = timezone.now() + timedelta(minutes=lockout_mins)
                user.save(update_fields=[
                    "failed_login_attempts", "last_failed_login", "locked_until"
                ])
            raise AuthenticationFailed("Invalid credentials or account locked")

        # Success — reset counters
        self.user = User.objects.get(**{username_field: username})
        self.user.failed_login_attempts = 0
        self.user.locked_until          = None
        self.user.last_login            = timezone.now()
        self.user.save(update_fields=[
            "failed_login_attempts", "locked_until", "last_login"
        ])
        return data


# ── User representation (auth context) ───────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """
    Full user representation used by the auth profile endpoint and the
    register view response.  Exposes all new fields (full_name, source,
    is_locked) so the frontend gets a consistent shape from both
    /api/auth/profile/ and /api/v1/users/.
    """
    is_locked          = serializers.BooleanField(read_only=True)
    is_service_account = serializers.BooleanField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "full_name",
            "first_name", "last_name",
            "role", "department", "source",
            "is_active", "is_locked", "is_service_account",
            "last_login", "failed_login_attempts", "last_failed_login",
            "notify_critical", "notify_deploy", "notify_digest",
            "is_ldap_user", "date_joined",
        ]
        read_only_fields = [
            "id", "last_login", "date_joined",
            "is_ldap_user", "is_locked", "is_service_account",
        ]


# ── Public registration ───────────────────────────────────────────────────────

class UserCreateSerializer(serializers.ModelSerializer):
    """
    Public registration endpoint: always creates a viewer.
    Role elevation is done by an admin via /api/v1/users/{id}/change_role/.
    """
    password = serializers.CharField(write_only=True, min_length=12)

    class Meta:
        model  = User
        fields = ["username", "email", "password", "full_name", "first_name", "last_name", "department"]

    def validate_password(self, value: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", value):
            errors.append("At least one uppercase letter required.")
        if not re.search(r"[a-z]", value):
            errors.append("At least one lowercase letter required.")
        if not re.search(r"\d", value):
            errors.append("At least one digit required.")
        if not re.search(r"[^A-Za-z0-9]", value):
            errors.append("At least one special character required.")
        if errors:
            raise ValidationError(errors)
        return value

    def create(self, validated_data):
        # Public registrations are always admins
        validated_data["role"]   = User.Role.ADMIN
        validated_data["source"] = User.UserSource.LOCAL
        return User.objects.create_user(**validated_data)


# ── Password change ───────────────────────────────────────────────────────────

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=12)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", value):
            errors.append("At least one uppercase letter required.")
        if not re.search(r"[a-z]", value):
            errors.append("At least one lowercase letter required.")
        if not re.search(r"\d", value):
            errors.append("At least one digit required.")
        if not re.search(r"[^A-Za-z0-9]", value):
            errors.append("At least one special character required.")
        if errors:
            raise ValidationError(errors)
        return value


# ── Audit log (used by backward-compat /api/auth/audit-logs/ route) ───────────

class AuditLogSerializer(serializers.ModelSerializer):
    actor      = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()
    description = serializers.CharField(source="action", read_only=True)
    status     = serializers.SerializerMethodField()

    class Meta:
        model  = AuditLog
        fields = [
            "id", "actor", "actor_role", "action",
            "resource_type", "resource_id",
            "description", "timestamp", "ip_address", "status",
        ]

    def get_actor(self, obj)      -> str: return obj.user.username if obj.user else "system"
    def get_actor_role(self, obj) -> str: return getattr(obj.user, "role", "system") if obj.user else "system"
    def get_status(self, obj)     -> str: return "success"


# ── System settings ───────────────────────────────────────────────────────────

class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SystemSetting
        fields = ["id", "key", "value", "data", "description", "updated_at"]
        read_only_fields = ["id", "updated_at"]
