"""
apps.users.admin
────────────────
Django admin registrations for the users app.
"""

from django.contrib import admin
from apps.users.models import SAMLConfiguration


@admin.register(SAMLConfiguration)
class SAMLConfigurationAdmin(admin.ModelAdmin):
    list_display  = ("name", "idp_entity_id", "default_role", "auto_create_users", "is_active", "updated_at")
    list_filter   = ("is_active", "default_role", "auto_create_users")
    search_fields = ("name", "idp_entity_id", "idp_sso_url")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("General", {
            "fields": ("id", "name", "is_active"),
        }),
        ("Service Provider (SP)", {
            "fields": ("sp_entity_id",),
            "description": "Leave blank to use the auto-generated SP entity ID.",
        }),
        ("Identity Provider (IdP)", {
            "fields": ("idp_entity_id", "idp_sso_url", "idp_slo_url", "idp_x509_cert"),
        }),
        ("Attribute Mapping", {
            "fields": ("attribute_mapping",),
            "description": (
                'JSON: {"email": "email", "cn": "full_name", "memberOf": "role"}. '
                'Keys are SAML attribute names; values are User field names.'
            ),
        }),
        ("Provisioning", {
            "fields": ("default_role", "auto_create_users", "auto_update_attrs"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
