"""
apps.users.saml_urls
─────────────────────
SAML-specific URLs, mounted at /api/v1/saml/ in config/urls.py.

  GET    /configs/                    → SAMLConfigViewSet.list
  POST   /configs/                    → SAMLConfigViewSet.create
  GET    /configs/{id}/               → SAMLConfigViewSet.retrieve
  PUT    /configs/{id}/               → SAMLConfigViewSet.update
  DELETE /configs/{id}/               → SAMLConfigViewSet.destroy
  GET    /{config_id}/metadata/       → SAMLMetadataView
  GET    /{config_id}/login/          → SAMLInitLoginView
  POST   /{config_id}/acs/            → SAMLACSView
  GET    /{config_id}/logout/         → SAMLLogoutView
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views import (
    SAMLACSView,
    SAMLConfigViewSet,
    SAMLInitLoginView,
    SAMLLogoutView,
    SAMLMetadataView,
    SAMLPublicProvidersView,
)

# SAML config CRUD router
config_router = DefaultRouter()
config_router.register(r"configs", SAMLConfigViewSet, basename="saml-config")

urlpatterns = [
    path("", include(config_router.urls)),

    # Public: active IdP list for the login page
    path("providers/", SAMLPublicProvidersView.as_view(), name="saml-providers"),

    # Per-IdP SAML flow endpoints
    path("<uuid:config_id>/metadata/", SAMLMetadataView.as_view(),   name="saml-metadata"),
    path("<uuid:config_id>/login/",    SAMLInitLoginView.as_view(),   name="saml-login"),
    path("<uuid:config_id>/acs/",      SAMLACSView.as_view(),         name="saml-acs"),
    path("<uuid:config_id>/logout/",   SAMLLogoutView.as_view(),      name="saml-logout"),
]
