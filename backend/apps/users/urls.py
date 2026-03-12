"""
apps.users.urls
───────────────
URL configuration for the users app.

Mounted by config/urls.py as:
  /api/v1/users/   → include('apps.users.urls')
  /api/v1/saml/    → include('apps.users.saml_urls')
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views import AuditLogViewSet, UserViewSet

router = DefaultRouter()
router.register(r"", UserViewSet, basename="user")

# /api/v1/users/audit-logs/
audit_router = DefaultRouter()
audit_router.register(r"", AuditLogViewSet, basename="user-audit-log")

urlpatterns = [
    # ── User CRUD + actions ───────────────────────────────────────────────────
    # Registered routes (via router):
    #   GET    /                       list
    #   POST   /                       create
    #   GET    /{id}/                  retrieve
    #   PUT    /{id}/                  update
    #   PATCH  /{id}/                  partial_update
    #   DELETE /{id}/                  destroy
    #   GET    /me/                    me
    #   POST   /{id}/lock/             lock
    #   POST   /{id}/unlock/           unlock
    #   POST   /{id}/change_role/      change_role
    #   POST   /{id}/reset_password/   reset_password
    #   GET    /export-csv/            export_csv
    #   POST   /import-csv/            import_csv
    path("", include(router.urls)),

    # ── Audit log sub-resource ────────────────────────────────────────────────
    #   GET    /audit-logs/            list
    #   GET    /audit-logs/{id}/       retrieve
    path("audit-logs/", include(audit_router.urls)),
]
