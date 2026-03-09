import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("patchguard")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule Configuration
app.conf.beat_schedule = {
    # Task 5.1: Sync patch definitions from WSUS/Ubuntu Security
    "sync-patch-catalog": {
        "task": "apps.patches.tasks.sync_vendor_patches",
        "schedule": crontab(minute="0", hour="*/6"), # every 6 hours
        "options": {"queue": "default"},
    },
    # Task 4.1: Check for devices that haven't heartbeated
    "device-stale-check": {
        "task": "apps.inventory.tasks.mark_stale_devices",
        "schedule": crontab(minute="*/5"), # every 5 minutes
        "options": {"queue": "default"},
    },
    # Task 5: Execute pending scheduled patch deployments
    "run-scheduled-deployments": {
        "task": "apps.deployments.tasks.process_scheduled_deployments",
        "schedule": crontab(minute="*/1"), # every minute
        "options": {"queue": "critical"},
    },
    # Task 2.5: Snapshot compliance for historical reporting
    "compliance-snapshot": {
        "task": "apps.patches.tasks.generate_compliance_snapshot",
        "schedule": crontab(minute="0", hour="1"), # daily at 01:00 UTC
        "options": {"queue": "reporting"},
    },
    # PostgreSQL partition maintenance
    "cleanup-old-partitions": {
        "task": "apps.accounts.tasks.cleanup_audit_partitions",
        "schedule": crontab(minute="0", hour="3", day_of_month="1"), # monthly 1st at 03:00
        "options": {"queue": "reporting"},
    },
    # Scheduled weekly compliance PDF report
    "weekly-compliance-report": {
        "task": "apps.patches.tasks.generate_scheduled_report",
        "schedule": crontab(minute="0", hour="7", day_of_week="1"),  # Monday 07:00 UTC
        "options": {"queue": "reporting"},
    },
    # Daily SLA breach check
    "daily-sla-breach-check": {
        "task": "apps.patches.tasks.check_sla_breaches",
        "schedule": crontab(minute="0", hour="6"),  # daily 06:00 UTC
        "options": {"queue": "reporting"},
    },
}
