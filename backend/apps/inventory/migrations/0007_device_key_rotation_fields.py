"""
Migration: Add key_created_at and key_last_rotated_at to Device model (Task 11.7)
"""
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_device_inventory_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="key_created_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp when the current agent_api_key was generated.",
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="key_last_rotated_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp of last automated API key rotation.",
            ),
        ),
    ]
