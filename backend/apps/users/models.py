"""
apps.users.models
─────────────────
Models owned by the users app:
  - SAMLConfiguration  : per-IdP SAML 2.0 settings stored in the database,
                         enabling multi-IdP support without touching settings.py.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


# ── SAML Configuration ────────────────────────────────────────────────────────

class SAMLConfiguration(models.Model):
    """
    Stores the identity-provider (IdP) metadata needed to perform a SAML 2.0
    SSO exchange.  Multiple configurations can coexist (multi-IdP).

    Attribute mapping format (JSON):
      {
        "email":     "email",       # SAML attr  → User field
        "givenName": "full_name",
        "role":      "role"         # optional; falls back to default_role
      }
    """

    class DefaultRole(models.TextChoices):
        ADMIN    = "admin",    "Admin"
        OPERATOR = "operator", "Operator"
        VIEWER   = "viewer",   "Viewer"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100, unique=True,
                                   help_text="Friendly name shown in the login UI")

    # ── Service Provider (SP) settings ────────────────────────────────────────
    sp_entity_id = models.CharField(
        max_length=500, blank=True,
        help_text="SP EntityID. Defaults to <base_url>/api/v1/saml/<id>/metadata/ if blank."
    )

    # ── Identity Provider (IdP) settings ──────────────────────────────────────
    idp_entity_id  = models.CharField(max_length=500)
    idp_sso_url    = models.URLField(max_length=500, verbose_name="IdP SSO URL")
    idp_slo_url    = models.URLField(max_length=500, blank=True, verbose_name="IdP SLO URL")
    idp_x509_cert  = models.TextField(verbose_name="IdP X.509 Certificate (PEM, no headers)")

    # ── Attribute mapping ──────────────────────────────────────────────────────
    attribute_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'JSON mapping of SAML attribute names to User field names. '
            'Example: {"email": "email", "cn": "full_name", "memberOf": "role"}'
        ),
    )

    # ── Provisioning ──────────────────────────────────────────────────────────
    default_role       = models.CharField(
        max_length=20, choices=DefaultRole.choices, default=DefaultRole.VIEWER,
        help_text="Role assigned when the SAML response does not include a role attribute."
    )
    auto_create_users  = models.BooleanField(
        default=True,
        help_text="Automatically provision a new User account on first SAML login."
    )
    auto_update_attrs  = models.BooleanField(
        default=True,
        help_text="Overwrite full_name / department from SAML attrs on every login."
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = "saml_configuration"
        ordering  = ["name"]
        verbose_name        = "SAML Configuration"
        verbose_name_plural = "SAML Configurations"

    def __str__(self) -> str:
        return f"{self.name} ({'active' if self.is_active else 'disabled'})"

    def get_sp_entity_id(self, base_url: str = "") -> str:
        if self.sp_entity_id:
            return self.sp_entity_id
        return f"{base_url.rstrip('/')}/api/v1/saml/{self.id}/metadata/"
