from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from common.redis_pubsub import RedisPublisher
import logging

logger = logging.getLogger(__name__)


@shared_task
def mark_stale_devices():
    """Mark online devices offline when they haven't sent a heartbeat in 5 minutes."""
    from .models import Device

    threshold = timezone.now() - timedelta(minutes=5)
    stale = Device.objects.filter(status=Device.Status.ONLINE, last_seen__lt=threshold)

    count = stale.count()
    if count > 0:
        for dev in stale:
            dev.status = Device.Status.OFFLINE
            dev.save(update_fields=["status"])
            RedisPublisher.publish_device_status(str(dev.id), dev.hostname, "offline")
        logger.info(f"Marked {count} device(s) offline (stale heartbeat).")


@shared_task
def flush_heartbeat_batch():
    """Placeholder: bulk-flush heartbeat cache to DB in high-volume deployments."""
    logger.info("Heartbeat batch flush (no-op in dev mode).")


@shared_task
def scan_device_patches(device_id: str):
    """
    Command the agent to run a full patch scan.

    Publishes START_SCAN on the agent:command:{device_id} Redis channel.
    The realtime service routes this to the agent via WebSocket.
    Scan results come back via ingest_scan REST endpoint.

    BUG FIX: was using device.agent_api_key as the channel key.
    The realtime ws_manager stores agents by device_id (UUID), so the Redis
    channel must be agent:command:{device.id}.
    """
    from .models import Device
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        logger.error(f"scan_device_patches: device {device_id} not found")
        return

    RedisPublisher.publish_agent_command(
        str(device.id),          # FIX: was device.agent_api_key
        "START_SCAN",
        {"device_id": str(device.id), "hostname": device.hostname},
    )
    logger.info(f"START_SCAN published for '{device.hostname}' ({device.id})")


@shared_task
def process_scan_results(device_id: str, patches: list):
    """
    Persist agent scan results into DevicePatchStatus.

    Called after the realtime service POSTs to /devices/{id}/ingest_scan/.
    Each item in `patches` should contain:
      - vendor_id  (str)   unique identifier e.g. "KB5034441" or "CVE-2025-1234"
      - title      (str)   human-readable name
      - installed  (bool)  True = already installed, False = missing
    Optional:
      - severity, version, vendor, package_name
    """
    from .models import Device
    from apps.patches.models import Patch, DevicePatchStatus

    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        logger.error(f"process_scan_results: device {device_id} not found")
        return

    installed_count = 0
    missing_count = 0
    skipped = 0

    for patch_data in patches:
        vendor_id = (
            patch_data.get("vendor_id")
            or patch_data.get("id")
            or patch_data.get("kb_id")
        )
        if not vendor_id:
            skipped += 1
            continue

        patch, _ = Patch.objects.get_or_create(
            vendor_id=str(vendor_id),
            defaults={
                "title": patch_data.get("title") or str(vendor_id),
                "severity": patch_data.get("severity", Patch.Severity.MEDIUM),
                "vendor": patch_data.get("vendor", device.os_family),
                "status": Patch.Status.IMPORTED,
                "applicable_os": [device.os_family],
                "package_name": patch_data.get("package_name", ""),
                "package_version": patch_data.get("version", ""),
            },
        )

        installed = bool(patch_data.get("installed", False))
        state = (
            DevicePatchStatus.State.INSTALLED
            if installed
            else DevicePatchStatus.State.MISSING
        )

        DevicePatchStatus.objects.update_or_create(
            device=device,
            patch=patch,
            defaults={"state": state},
        )

        if installed:
            installed_count += 1
        else:
            missing_count += 1

    logger.info(
        f"Scan results for '{device.hostname}': "
        f"{installed_count} installed, {missing_count} missing, {skipped} skipped"
    )

    # Notify dashboards of updated compliance
    RedisPublisher.publish_notification(
        "info",
        f"Scan complete for {device.hostname}: "
        f"{installed_count} installed, {missing_count} missing.",
    )
