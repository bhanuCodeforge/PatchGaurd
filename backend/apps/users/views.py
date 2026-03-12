"""
apps.users.views
────────────────
All DRF views for user management, SAML SSO, and CSV import/export.

URL map (mounted at /api/v1/users/):
  GET    /                      → UserViewSet.list
  POST   /                      → UserViewSet.create
  GET    /{id}/                 → UserViewSet.retrieve
  PUT    /{id}/                 → UserViewSet.update
  PATCH  /{id}/                 → UserViewSet.partial_update
  DELETE /{id}/                 → UserViewSet.destroy
  GET    /me/                   → UserViewSet.me
  POST   /{id}/lock/            → UserViewSet.lock
  POST   /{id}/unlock/          → UserViewSet.unlock
  POST   /{id}/change_role/     → UserViewSet.change_role
  POST   /{id}/reset_password/  → UserViewSet.reset_password
  GET    /export-csv/           → UserViewSet.export_csv
  POST   /import-csv/           → UserViewSet.import_csv
  GET    /audit-logs/           → AuditLogViewSet.list
  GET    /audit-logs/{id}/      → AuditLogViewSet.retrieve

SAML URLs (mounted at /api/v1/saml/):
  GET    /{config_id}/metadata/ → SAMLMetadataView
  GET    /{config_id}/login/    → SAMLInitLoginView   (SP-initiated)
  POST   /{config_id}/acs/      → SAMLACSView         (Assertion Consumer Service)
  GET    /configs/              → SAMLConfigViewSet.list
  POST   /configs/              → SAMLConfigViewSet.create
  GET    /configs/{id}/         → SAMLConfigViewSet.retrieve
  PUT    /configs/{id}/         → SAMLConfigViewSet.update
  DELETE /configs/{id}/         → SAMLConfigViewSet.destroy
"""

import csv
import io
import logging
import secrets
import string

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AuditLog
from apps.accounts.permissions import IsAdmin, IsOperatorOrAbove
from apps.users.filters import UserFilter
from apps.users.models import SAMLConfiguration
from apps.users.serializers import (
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    AuditLogSerializer,
    SAMLConfigSerializer,
    UserCSVRowSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from common.pagination import StandardPageNumberPagination

User = get_user_model()
logger = logging.getLogger("patchguard.users")

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()"


def _generate_temp_password(length: int = 16) -> str:
    import re
    while True:
        pwd = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if (re.search(r"[A-Z]", pwd) and re.search(r"[a-z]", pwd)
                and re.search(r"\d", pwd) and re.search(r"[^A-Za-z0-9]", pwd)):
            return pwd


def _record(request, action_str: str, user_obj: User) -> None:
    """Write a single AuditLog entry, resolving the actor safely."""
    actor = request.user if isinstance(request.user, User) else None
    AuditLog.objects.create(
        user=actor,
        action=action_str,
        resource_type="user",
        resource_id=user_obj.id,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


# ── User ViewSet ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    """
    Full CRUD user management. Admin-only for mutations; operators can list.
    """
    queryset         = User.objects.all().order_by("-date_joined")
    filterset_class  = UserFilter
    search_fields    = ["username", "email", "full_name", "department"]
    ordering_fields  = ["username", "email", "date_joined", "last_login", "role"]
    pagination_class = StandardPageNumberPagination

    # ── Permission routing ────────────────────────────────────────────────────
    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        if self.action in ("list", "retrieve"):
            return [IsOperatorOrAbove()]
        return [IsAdmin()]

    # ── Serializer routing ────────────────────────────────────────────────────
    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        if self.action in ("update", "partial_update"):
            return AdminUserUpdateSerializer
        if self.action in ("list", "me"):
            return UserListSerializer
        return UserDetailSerializer

    # ── CRUD hooks ────────────────────────────────────────────────────────────
    def perform_create(self, serializer):
        user = serializer.save()
        _record(self.request, f"Created user {user.username}", user)
        logger.info("User created: %s by %s", user.username, self.request.user)

    def perform_update(self, serializer):
        user = serializer.save()
        _record(self.request, f"Updated user {user.username}", user)

    def perform_destroy(self, instance):
        _record(self.request, f"Deleted user {instance.username}", instance)
        logger.warning("User deleted: %s by %s", instance.username, self.request.user)
        instance.delete()

    # ── Custom actions ────────────────────────────────────────────────────────

    @extend_schema(summary="Current user profile")
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserListSerializer(request.user).data)

    @extend_schema(summary="Lock a user account permanently")
    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        user = self.get_object()
        user.locked_until = timezone.now() + timezone.timedelta(days=36_500)
        user.save(update_fields=["locked_until"])
        _record(request, f"Locked user {user.username}", user)
        return Response({"status": "locked", "username": user.username})

    @extend_schema(summary="Unlock a user account")
    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.locked_until          = None
        user.failed_login_attempts = 0
        user.save(update_fields=["locked_until", "failed_login_attempts"])
        _record(request, f"Unlocked user {user.username}", user)
        return Response({"status": "unlocked", "username": user.username})

    @extend_schema(
        summary="Change user role",
        request={"application/json": {"type": "object", "properties": {"role": {"type": "string"}}}},
    )
    @action(detail=True, methods=["post"])
    def change_role(self, request, pk=None):
        user     = self.get_object()
        new_role = request.data.get("role", "").lower()
        valid    = [r[0] for r in User.Role.choices]
        if new_role not in valid:
            return Response(
                {"error": f"Invalid role. Valid choices: {valid}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old_role = user.role
        user.role = new_role
        user.save(update_fields=["role"])
        _record(request, f"Role changed {user.username}: {old_role} → {new_role}", user)
        return Response({"status": "role_changed", "role": new_role})

    @extend_schema(summary="Force-reset a user's password and return a temporary one")
    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        user     = self.get_object()
        temp_pwd = _generate_temp_password()
        user.set_password(temp_pwd)
        user.must_change_password = True
        user.save()
        _record(request, f"Password reset for {user.username}", user)
        return Response({
            "status": "password_reset",
            "temporary_password": temp_pwd,
            "must_change_password": True,
        })

    # ── CSV Export ────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Export all users as CSV",
        responses={200: None},
        parameters=[
            OpenApiParameter("role",   str, description="Filter by role"),
            OpenApiParameter("source", str, description="Filter by source"),
        ],
    )
    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "username", "email", "full_name", "role",
            "department", "source", "is_active", "is_locked",
            "last_login", "date_joined",
        ])
        for u in qs.iterator(chunk_size=500):
            writer.writerow([
                u.username, u.email, u.full_name, u.role,
                u.department, u.source,
                "true" if u.is_active else "false",
                "true" if u.is_locked else "false",
                u.last_login.isoformat() if u.last_login else "",
                u.date_joined.isoformat(),
            ])
        _record(request, "Exported user CSV", request.user)
        return response

    # ── CSV Import ────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Bulk-import users from CSV",
        request={"multipart/form-data": {"type": "object",
                                          "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={200: None},
    )
    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        if not csv_file.name.endswith(".csv"):
            return Response({"error": "File must be a .csv."}, status=status.HTTP_400_BAD_REQUEST)

        decoded = csv_file.read().decode("utf-8-sig")  # handle BOM
        reader  = csv.DictReader(io.StringIO(decoded))

        created = []
        skipped = []
        errors  = []

        for line_num, row in enumerate(reader, start=2):
            row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
            serializer = UserCSVRowSerializer(data=row)

            if not serializer.is_valid():
                errors.append({"row": line_num, "errors": serializer.errors})
                continue

            data = serializer.validated_data
            if User.objects.filter(username__iexact=data["username"]).exists():
                skipped.append({"row": line_num, "username": data["username"],
                                "reason": "Username already exists."})
                continue
            if User.objects.filter(email__iexact=data["email"]).exists():
                skipped.append({"row": line_num, "username": data["username"],
                                "reason": "Email already exists."})
                continue

            user = User(
                username   = data["username"].lower(),
                email      = data["email"].lower(),
                full_name  = data.get("full_name", ""),
                role       = data["role"],
                department = data.get("department", ""),
                source     = data.get("source", "local"),
                must_change_password=True,
            )
            if data.get("password"):
                user.set_password(data["password"])
            else:
                user.set_unusable_password()
            user.save()

            AuditLog.objects.create(
                user=request.user if isinstance(request.user, User) else None,
                action=f"CSV import: created user {user.username}",
                resource_type="user",
                resource_id=user.id,
            )
            created.append(user.username)

        summary = {
            "created": len(created),
            "skipped": len(skipped),
            "errors":  len(errors),
            "created_users": created,
            "skipped_rows":  skipped,
            "error_rows":    errors,
        }
        logger.info("CSV import by %s: %s", request.user, summary)
        return Response(summary, status=status.HTTP_200_OK)


# ── Audit Log ViewSet ─────────────────────────────────────────────────────────

@extend_schema(tags=["Users"])
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to the global audit log.
    Operators can view; admins can view all.
    """
    queryset         = AuditLog.objects.all().select_related("user").order_by("-timestamp")
    serializer_class = AuditLogSerializer
    permission_classes = [IsOperatorOrAbove]
    pagination_class = StandardPageNumberPagination
    filterset_fields = ["resource_type", "user"]
    search_fields    = ["action", "user__username"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Non-admins can only see their own actions
        if self.request.user.role != "admin":
            qs = qs.filter(user=self.request.user)
        return qs


# ── SAML ViewSet ──────────────────────────────────────────────────────────────

@extend_schema(tags=["SAML"])
class SAMLConfigViewSet(viewsets.ModelViewSet):
    """CRUD for SAML IdP configurations. Admin-only."""
    queryset           = SAMLConfiguration.objects.all().order_by("name")
    serializer_class   = SAMLConfigSerializer
    permission_classes = [IsAdmin]


@extend_schema(tags=["SAML"])
class SAMLPublicProvidersView(APIView):
    """
    Public endpoint — returns active IdP names for the login page.

    GET /api/v1/saml/providers/
    Returns: [{ "id": "...", "name": "..." }, ...]
    """
    permission_classes = []  # unauthenticated – needed on the login page

    def get(self, request):
        configs = (
            SAMLConfiguration.objects
            .filter(is_active=True)
            .values("id", "name")
            .order_by("name")
        )
        return Response(list(configs))


# ── SAML Flow Views ───────────────────────────────────────────────────────────

@extend_schema(tags=["SAML"])
class SAMLMetadataView(APIView):
    """
    Returns the SP metadata XML for the given SAMLConfiguration.
    The IdP administrator uses this to register your SP.

    GET /api/v1/saml/{config_id}/metadata/
    """
    permission_classes = []  # publicly accessible – IdPs need to fetch this

    def get(self, request, config_id):
        try:
            config = SAMLConfiguration.objects.get(pk=config_id, is_active=True)
        except SAMLConfiguration.DoesNotExist:
            return Response({"error": "SAML configuration not found."}, status=404)

        try:
            from apps.users.saml_backend import build_saml_settings, generate_metadata
        except ImportError:
            return Response({"error": "python3-saml is not installed."}, status=501)

        base_url   = request.build_absolute_uri("/").rstrip("/")
        saml_settings = build_saml_settings(config, base_url)
        metadata, errors = generate_metadata(saml_settings)
        if errors:
            return Response({"error": "Metadata generation failed.", "details": errors}, status=500)

        return HttpResponse(metadata, content_type="application/xml")


@extend_schema(tags=["SAML"])
class SAMLInitLoginView(APIView):
    """
    Initiates SP-side SAML login. Returns the IdP redirect URL.
    The Angular SPA opens this URL (or navigates to it) to kick off SSO.

    GET /api/v1/saml/{config_id}/login/
    Returns: { "redirect_url": "https://idp.example.com/sso?SAMLRequest=..." }
    """
    permission_classes = []

    def get(self, request, config_id):
        try:
            config = SAMLConfiguration.objects.get(pk=config_id, is_active=True)
        except SAMLConfiguration.DoesNotExist:
            return Response({"error": "SAML configuration not found."}, status=404)

        try:
            from apps.users.saml_backend import build_saml_settings, init_auth
        except ImportError:
            return Response({"error": "python3-saml is not installed."}, status=501)

        base_url      = request.build_absolute_uri("/").rstrip("/")
        saml_settings = build_saml_settings(config, base_url)
        auth          = init_auth(saml_settings, request)
        redirect_url  = auth.login()
        return Response({"redirect_url": redirect_url})


@extend_schema(tags=["SAML"])
class SAMLACSView(APIView):
    """
    Assertion Consumer Service — receives the SAML response from the IdP,
    validates it, provisions / updates the user, and returns JWT tokens.

    POST /api/v1/saml/{config_id}/acs/
    Body: application/x-www-form-urlencoded  (SAMLResponse=<base64>)
    Returns: { "access": "...", "refresh": "...", "user": {...} }
    """
    permission_classes = []

    def post(self, request, config_id):
        try:
            config = SAMLConfiguration.objects.get(pk=config_id, is_active=True)
        except SAMLConfiguration.DoesNotExist:
            return Response({"error": "SAML configuration not found."}, status=404)

        try:
            from apps.users.saml_backend import (
                build_saml_settings, init_auth, process_response,
            )
        except ImportError:
            return Response({"error": "python3-saml is not installed."}, status=501)

        base_url      = request.build_absolute_uri("/").rstrip("/")
        saml_settings = build_saml_settings(config, base_url)
        auth          = init_auth(saml_settings, request)

        try:
            attrs, name_id = process_response(auth)
        except Exception as exc:
            logger.warning("SAML ACS error for config %s: %s", config_id, exc)
            return Response(
                {"error": "SAML validation failed.", "detail": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Provision / retrieve user
        from apps.users.saml_backend import provision_saml_user
        try:
            user = provision_saml_user(config, attrs, name_id)
        except Exception as exc:
            logger.error("SAML user provisioning failed: %s", exc)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({"error": "Account is inactive."}, status=status.HTTP_403_FORBIDDEN)
        if user.is_locked:
            return Response({"error": "Account is locked."}, status=status.HTTP_403_FORBIDDEN)

        # Issue JWT
        refresh = RefreshToken.for_user(user)
        refresh["role"]     = user.role
        refresh["username"] = user.username
        refresh["email"]    = user.email

        # Update last_login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        AuditLog.objects.create(
            user=user,
            action=f"SAML login via {config.name}",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        logger.info("SAML login: %s via config '%s'", user.username, config.name)

        access_token  = str(refresh.access_token)
        refresh_token = str(refresh)

        # For browser-initiated SAML flows, return an HTML page that stores the
        # JWT tokens in localStorage and redirects to the dashboard.
        # API clients that send Accept: application/json still get JSON.
        import json as _json
        if "application/json" in request.META.get("HTTP_ACCEPT", ""):
            return Response({
                "access":  access_token,
                "refresh": refresh_token,
                "user":    UserListSerializer(user).data,
            })

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>SSO Login</title></head>
<body>
<script>
(function () {{
  try {{
    localStorage.setItem('access_token',  {_json.dumps(access_token)});
    localStorage.setItem('refresh_token', {_json.dumps(refresh_token)});
  }} catch (e) {{ console.error('SSO storage error', e); }}
  window.location.replace('/dashboard');
}})();
</script>
<p style="font-family:sans-serif;padding:40px;text-align:center;color:#6b7280">
  Authentication successful &#8212; redirecting&hellip;</p>
</body>
</html>"""
        return HttpResponse(html, content_type="text/html")


@extend_schema(tags=["SAML"])
class SAMLLogoutView(APIView):
    """
    Initiates SAML Single Log-Out (SLO) — returns the IdP redirect URL.
    The frontend navigates to this URL to complete federated logout.

    GET /api/v1/saml/{config_id}/logout/
    Returns: { "redirect_url": "..." }  or  { "status": "logged_out" } if SLO not configured.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, config_id):
        try:
            config = SAMLConfiguration.objects.get(pk=config_id, is_active=True)
        except SAMLConfiguration.DoesNotExist:
            return Response({"error": "SAML configuration not found."}, status=404)

        if not config.idp_slo_url:
            return Response({"status": "logged_out", "detail": "IdP does not support SLO."})

        try:
            from apps.users.saml_backend import build_saml_settings, init_auth
        except ImportError:
            return Response({"error": "python3-saml is not installed."}, status=501)

        base_url      = request.build_absolute_uri("/").rstrip("/")
        saml_settings = build_saml_settings(config, base_url)
        auth          = init_auth(saml_settings, request)
        redirect_url  = auth.logout(name_id=request.user.email)
        return Response({"redirect_url": redirect_url})
