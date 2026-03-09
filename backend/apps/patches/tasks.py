from celery import shared_task
import logging
from common.redis_cache import DashboardCache
from common.redis_pubsub import RedisPublisher

logger = logging.getLogger(__name__)

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
