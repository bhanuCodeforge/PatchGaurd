from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── Auth (login, register, token refresh, password change, profile) ────────
    path("api/auth/", include("apps.accounts.urls")),

    # ── User management (CRUD, lock/unlock, role, CSV, audit-logs) ─────────────
    # Replaces the old accounts.urls_users + accounts.urls_audit routes.
    path("api/v1/users/", include("apps.users.urls")),

    # ── SAML 2.0 SSO (metadata, login initiation, ACS, logout, config CRUD) ────
    path("api/v1/saml/", include("apps.users.saml_urls")),

    # ── Devices ────────────────────────────────────────────────────────────────
    path("api/v1/devices/", include("apps.inventory.urls")),

    # ── Patches ────────────────────────────────────────────────────────────────
    path("api/v1/patches/", include("apps.patches.urls")),

    # ── Deployments + compliance reports ──────────────────────────────────────
    path("api/v1/", include("apps.deployments.urls")),

    # ── System settings (admin-only key/value store) ───────────────────────────
    path("api/v1/settings/", include("apps.accounts.urls_settings")),

    # ── OpenAPI / Swagger ──────────────────────────────────────────────────────
    path("api/schema/",  SpectacularAPIView.as_view(),    name="schema"),
    path("api/docs/",    SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",   SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
]

# Backward-compatibility aliases: the old /api/v1/audit-logs/ route
# now lives under /api/v1/users/audit-logs/, but we keep the old path
# so any existing clients / monitoring scripts don't break.
urlpatterns += [
    path("api/v1/audit-logs/", include("apps.accounts.urls_audit")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
