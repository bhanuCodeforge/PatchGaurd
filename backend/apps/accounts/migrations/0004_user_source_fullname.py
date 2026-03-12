"""
Migration 0004 — Extend User model with:
  - source       (LOCAL / LDAP / SAML)
  - full_name
  - last_failed_login
  - notify_critical / notify_deploy / notify_digest
  - source index
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_systemsetting"),
    ]

    operations = [
        # ── Auth source ────────────────────────────────────────────────────────
        migrations.AddField(
            model_name="user",
            name="source",
            field=models.CharField(
                choices=[("local", "Local"), ("ldap", "LDAP"), ("saml", "SAML")],
                default="local",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["source"], name="accounts_user_source_idx"),
        ),

        # ── Identity ───────────────────────────────────────────────────────────
        migrations.AddField(
            model_name="user",
            name="full_name",
            field=models.CharField(blank=True, max_length=200),
        ),

        # ── Security ───────────────────────────────────────────────────────────
        migrations.AddField(
            model_name="user",
            name="last_failed_login",
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── Notification preferences ───────────────────────────────────────────
        migrations.AddField(
            model_name="user",
            name="notify_critical",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="notify_deploy",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="notify_digest",
            field=models.BooleanField(default=False),
        ),
    ]
