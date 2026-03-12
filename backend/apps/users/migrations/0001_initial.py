"""
users app — initial migration
Creates the SAMLConfiguration table.
"""
import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SAMLConfiguration",
            fields=[
                ("id",
                 models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name",
                 models.CharField(
                     help_text="Friendly name shown in the login UI",
                     max_length=100, unique=True,
                 )),
                ("sp_entity_id",
                 models.CharField(
                     blank=True, max_length=500,
                     help_text="SP EntityID. Defaults to auto-generated URL if blank.",
                 )),
                ("idp_entity_id",
                 models.CharField(max_length=500)),
                ("idp_sso_url",
                 models.URLField(max_length=500, verbose_name="IdP SSO URL")),
                ("idp_slo_url",
                 models.URLField(blank=True, max_length=500, verbose_name="IdP SLO URL")),
                ("idp_x509_cert",
                 models.TextField(verbose_name="IdP X.509 Certificate (PEM, no headers)")),
                ("attribute_mapping",
                 models.JSONField(
                     blank=True, default=dict,
                     help_text='JSON mapping of SAML attributes to User fields.',
                 )),
                ("default_role",
                 models.CharField(
                     choices=[("admin", "Admin"), ("operator", "Operator"), ("viewer", "Viewer")],
                     default="viewer", max_length=20,
                     help_text="Role when SAML response has no role attribute.",
                 )),
                ("auto_create_users",
                 models.BooleanField(
                     default=True,
                     help_text="Auto-provision a User on first SAML login.",
                 )),
                ("auto_update_attrs",
                 models.BooleanField(
                     default=True,
                     help_text="Overwrite user attrs from SAML on every login.",
                 )),
                ("is_active",
                 models.BooleanField(default=True)),
                ("created_at",
                 models.DateTimeField(auto_now_add=True)),
                ("updated_at",
                 models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name":        "SAML Configuration",
                "verbose_name_plural": "SAML Configurations",
                "db_table":            "saml_configuration",
                "ordering":            ["name"],
            },
        ),
    ]
