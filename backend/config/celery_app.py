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

# ── Queue definitions (Task 11.4 hierarchy) ──────────────────────────────
from kombu import Queue, Exchange

app.conf.task_queues = (
    Queue("critical",            Exchange("critical"),            routing_key="critical"),
    Queue("default",             Exchange("default"),             routing_key="default"),
    Queue("reporting",           Exchange("reporting"),           routing_key="reporting"),
    Queue("deployment-waves",    Exchange("deployment-waves"),    routing_key="deployment-waves"),
    Queue("deployment-results",  Exchange("deployment-results"),  routing_key="deployment-results"),
)
app.conf.task_default_queue = "default"
app.conf.task_create_missing_queues = True

# Celery Beat Schedule Configuration
app.conf.beat_schedule = {
    # Task 5.1: Sync patch definitions from WSUS/Ubuntu Security
    "sync-patch-catalog": {
        "task": "apps.patches.tasks.sync_vendor_patches",
        "schedule": crontab(minute="0", hour="*/6"),
        "options": {"queue": "default"},
    },
    # Task 4.1: Check for devices that haven't heartbeated
    "device-stale-check": {
        "task": "apps.inventory.tasks.mark_stale_devices",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "default"},
    },
    # Execute pending scheduled patch deployments
    "run-scheduled-deployments": {
        "task": "apps.deployments.tasks.process_scheduled_deployments",
        "schedule": crontab(minute="*/1"),
        "options": {"queue": "critical"},
    },
    # Task 2.5: Snapshot compliance for historical reporting
    "compliance-snapshot": {
        "task": "apps.patches.tasks.generate_compliance_snapshot",
        "schedule": crontab(minute="0", hour="1"),
        "options": {"queue": "reporting"},
    },
    # PostgreSQL partition maintenance
    "cleanup-old-partitions": {
        "task": "apps.accounts.tasks.cleanup_audit_partitions",
        "schedule": crontab(minute="0", hour="3", day_of_month="1"),
        "options": {"queue": "reporting"},
    },
    # Scheduled weekly compliance PDF report
    "weekly-compliance-report": {
        "task": "apps.patches.tasks.generate_scheduled_report",
        "schedule": crontab(minute="0", hour="7", day_of_week="1"),
        "options": {"queue": "reporting"},
    },
    # Daily SLA breach check
    "daily-sla-breach-check": {
        "task": "apps.patches.tasks.check_sla_breaches",
        "schedule": crontab(minute="0", hour="6"),
        "options": {"queue": "reporting"},
    },
    # Task 11.4: Monitor stuck deployment waves every 10 minutes
    "monitor-stuck-waves": {
        "task": "apps.deployments.tasks.monitor_stuck_waves",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "default"},
    },
    # Task 11.6: Refresh compliance materialized view every hour
    "refresh-compliance-materialized-view": {
        "task": "apps.patches.tasks.refresh_compliance_materialized_view",
        "schedule": crontab(minute="0"),  # every hour
        "options": {"queue": "reporting"},
    },
    # Task 11.7: Daily automated API key rotation (90-day stale threshold)
    "rotate-stale-api-keys": {
        "task": "apps.inventory.tasks.rotate_stale_api_keys",
        "schedule": crontab(minute="30", hour="2"),  # 02:30 UTC daily
        "options": {"queue": "default"},
    },
}
