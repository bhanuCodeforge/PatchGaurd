"""
Migration: Add DeploymentEvent model (Task 11.5 — Event Sourcing)
"""
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deployments", "0001_initial"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeploymentEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(
                    max_length=20,
                    choices=[
                        ("queued",     "Device Queued"),
                        ("started",    "Patching Started"),
                        ("completed",  "Patching Completed"),
                        ("failed",     "Patching Failed"),
                        ("skipped",    "Device Skipped (Preflight)"),
                        ("cancelled",  "Deployment Cancelled"),
                        ("wave_start", "Wave Started"),
                        ("wave_done",  "Wave Completed"),
                    ],
                    db_index=True,
                )),
                ("wave_number", models.IntegerField(null=True, blank=True)),
                ("detail", models.JSONField(default=dict, blank=True)),
                ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("deployment", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="deployments.deployment",
                    db_index=True,
                )),
                ("target", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="deployments.deploymenttarget",
                    null=True,
                    blank=True,
                    db_index=True,
                )),
                ("device", models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="deployment_events",
                    to="inventory.device",
                    null=True,
                    blank=True,
                )),
            ],
            options={
                "db_table": "deployment_event",
                "ordering": ["-occurred_at"],
            },
        ),
        migrations.AddIndex(
            model_name="deploymentevent",
            index=models.Index(
                fields=["deployment", "event_type", "-occurred_at"],
                name="dep_event_dep_type_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="deploymentevent",
            index=models.Index(
                fields=["deployment", "device", "-occurred_at"],
                name="dep_event_dep_device_ts_idx",
            ),
        ),
    ]
