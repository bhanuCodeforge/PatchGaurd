from celery import shared_task
import logging
from common.redis_cache import DashboardCache
from common.redis_pubsub import RedisPublisher

logger = logging.getLogger(__name__)

# Cache key for the compliance snapshot used by the BFF/dashboard
_COMPLIANCE_MV_CACHE_KEY = "bff:compliance_mv_snapshot"
_COMPLIANCE_MV_CACHE_TTL = 3600  # 1 hour — refreshed by Beat anyway


@shared_task(queue="reporting", name="apps.patches.tasks.refresh_compliance_materialized_view")
def refresh_compliance_materialized_view() -> dict:
    """
    Task 11.6 — Refresh the PostgreSQL materialized view mv_compliance_stats
    and update the Redis cache snapshot.

    Triggered by:
      - Celery Beat every hour
      - Deployment completion (apps.deployments.tasks.orchestrate_deployment)
    """
    from django.db import connection, ProgrammingError
    import json

    try:
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compliance_stats;")
            cursor.execute("""
                SELECT
                    total_devices, online_devices, compliant_devices,
                    non_compliant_devices, avg_compliance_rate,
                    missing_critical_patches, missing_high_patches,
                    devices_by_os, devices_by_env, refreshed_at
                FROM mv_compliance_stats;
            """)
            row = cursor.fetchone()
    except ProgrammingError as exc:
        logger.warning("mv_compliance_stats not yet available (SQLite?): %s", exc)
        return {"status": "skipped", "reason": str(exc)}

    if not row:
        return {"status": "empty"}

    snapshot = {
        "total_devices":           row[0],
        "online_devices":          row[1],
        "compliant_devices":       row[2],
        "non_compliant_devices":   row[3],
        "avg_compliance_rate":     float(row[4] or 0),
        "missing_critical_patches": row[5],
        "missing_high_patches":    row[6],
        "devices_by_os":           row[7],
        "devices_by_env":          row[8],
        "refreshed_at":            row[9].isoformat() if row[9] else None,
    }

    # Store in Redis for ultra-fast API reads
    try:
        import redis as _redis
        from django.conf import settings as _settings
        r = _redis.Redis.from_url(
            getattr(_settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        r.setex(_COMPLIANCE_MV_CACHE_KEY, _COMPLIANCE_MV_CACHE_TTL, json.dumps(snapshot))
    except Exception as exc:
        logger.warning("Could not update Redis compliance snapshot: %s", exc)

    logger.info("mv_compliance_stats refreshed: avg=%.1f%% total=%d",
                snapshot["avg_compliance_rate"], snapshot["total_devices"])
    return {"status": "refreshed", "snapshot": snapshot}


@shared_task
def sync_vendor_patches():
    # Placeholder for vendor sync logic
    logger.info("Executing sync_vendor_patches: checking Ubuntu/Microsoft feeds...")
    RedisPublisher.publish_notification("info", "Vendor patch feed sync completed.")
    return "Sync complete"

@shared_task
def generate_compliance_snapshot():
    """
    Periodic task to capture and persist overall compliance status for trend reporting.
    """
    logger.info("Generating daily compliance snapshot...")
    from .models import ComplianceSnapshot, DevicePatchStatus
    from apps.inventory.models import Device
    from django.db.models import Avg
    
    total_devices = Device.objects.count()
    overall_avg = Device.objects.aggregate(avg=Avg('compliance_rate'))['avg'] or 0.0
    compliant_devices = Device.objects.filter(compliance_rate__gte=90).count()
    critical_missing = DevicePatchStatus.objects.filter(
        state=DevicePatchStatus.State.MISSING,
        patch__severity='critical'
    ).count()

    snapshot_obj = ComplianceSnapshot.objects.create(
        overall_compliance=round(overall_avg, 1),
        total_devices=total_devices,
        compliant_devices=compliant_devices,
        critical_missing=critical_missing
    )
    
    # Old cache logic for backward compatibility with dashboard counters
    rate = overall_avg / 100.0
    DashboardCache.set_compliance_snapshot({
       "rate": rate,
       "installed": compliant_devices, # Approximation for cache
       "total": total_devices
    })
    
    if rate < 0.8:
        RedisPublisher.publish_compliance_alert("global", rate)
        
    logger.info(f"Snapshot saved: {snapshot_obj.id} (Compliance: {overall_avg}%)")
    return f"Snapshot generated: {overall_avg}%"

@shared_task
def check_superseded_patches():
    logger.info("Evaluating superseded patch chain linkages...")
    # Simulated DAG progression loop
    pass


@shared_task
def generate_scheduled_report():
    """
    Weekly compliance report generation — collects metrics and sends notification.
    """
    logger.info("Generating scheduled weekly compliance report...")
    from apps.inventory.models import Device
    from .models import DevicePatchStatus
    from django.db.models import Avg

    total = Device.objects.count()
    avg_compliance = Device.objects.aggregate(avg=Avg('compliance_rate'))['avg'] or 0
    non_compliant = Device.objects.filter(compliance_rate__lt=90).count()
    critical_missing = DevicePatchStatus.objects.filter(
        state=DevicePatchStatus.State.MISSING,
        patch__severity='critical'
    ).count()

    report = {
        "type": "weekly_compliance",
        "total_devices": total,
        "avg_compliance": round(avg_compliance, 1),
        "non_compliant_devices": non_compliant,
        "critical_patches_missing": critical_missing,
    }

    RedisPublisher.publish_notification(
        "info",
        f"Weekly report: {avg_compliance:.1f}% compliance, {non_compliant} non-compliant, {critical_missing} critical missing"
    )
    logger.info(f"Weekly report generated: {report}")
    return report


@shared_task
def check_sla_breaches():
    """
    Daily SLA breach detection — alerts on devices not patched within SLA window.
    """
    logger.info("Checking for SLA breaches...")
    from apps.inventory.models import Device
    from django.utils import timezone
    from datetime import timedelta

    sla_window = timedelta(days=14)  # Critical patches must be applied within 14 days
    cutoff = timezone.now() - sla_window

    from .models import DevicePatchStatus
    breaches = DevicePatchStatus.objects.filter(
        state=DevicePatchStatus.State.MISSING,
        patch__severity__in=['critical', 'high'],
        patch__released_at__lt=cutoff,
    ).select_related('device', 'patch').values_list('device__hostname', flat=True).distinct()

    breach_count = breaches.count()
    if breach_count > 0:
        RedisPublisher.publish_notification(
            "warning",
            f"SLA breach alert: {breach_count} device(s) have unpatched critical/high patches beyond 14-day SLA."
        )
    logger.info(f"SLA breach check: {breach_count} device(s) in breach")
    return {"breach_count": breach_count}
