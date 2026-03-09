from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from common.redis_pubsub import RedisPublisher
import logging
from common.logging import trace

logger = logging.getLogger(__name__)


@shared_task
@trace
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
@trace
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
@trace
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
        # 1. Identify the core vendor_id
        vendor_id = (
            patch_data.get("vendor_id")
            or patch_data.get("id")
            or patch_data.get("kb_id")
            or patch_data.get("name")
        )
        if not vendor_id:
            skipped += 1
            continue

        # 2. Extract basic metadata
        title = patch_data.get("title") or patch_data.get("name") or str(vendor_id)
        severity = patch_data.get("severity", Patch.Severity.MEDIUM).lower()
        if severity not in [s[0] for s in Patch.Severity.choices]:
            severity = Patch.Severity.MEDIUM

        patch, _ = Patch.objects.get_or_create(
            vendor_id=str(vendor_id),
            defaults={
                "title": title,
                "severity": severity,
                "vendor": patch_data.get("vendor", device.os_family),
                "status": Patch.Status.IMPORTED,
                "applicable_os": [device.os_family],
                "package_name": patch_data.get("package_name", str(vendor_id)),
                "package_version": patch_data.get("version", ""),
            },
        )

        # 3. Determine if installed
        is_installed = False
        if "installed" in patch_data:
            is_installed = bool(patch_data["installed"])
        elif "missing" in patch_data:
            is_installed = not bool(patch_data["missing"])
        elif "status" in patch_data:
            is_installed = str(patch_data["status"]).lower() in ["installed", "completed", "success"]
        
        state = (
            DevicePatchStatus.State.INSTALLED
            if is_installed
            else DevicePatchStatus.State.MISSING
        )

        DevicePatchStatus.objects.update_or_create(
            device=device,
            patch=patch,
            defaults={"state": state},
        )

        if is_installed:
            installed_count += 1
        else:
            missing_count += 1

    logger.info(
        f"Scan results for '{device_id}': "
        f"{installed_count} installed, {missing_count} missing, {skipped} skipped"
    )
    
    # Update device compliance rate
    refresh_device_compliance(device_id)

    # Notify dashboards of updated compliance
    RedisPublisher.publish_notification(
        "info",
        f"Scan complete for {device.hostname}: "
        f"{installed_count} installed, {missing_count} missing.",
    )


@shared_task
@trace
def refresh_device_compliance(device_id: str):
    """Calculate and save the compliance percentage for a single device."""
    from .models import Device
    from apps.patches.models import DevicePatchStatus
    
    try:
        device = Device.objects.get(id=device_id)
        statuses = DevicePatchStatus.objects.filter(device=device)
        total = statuses.count()
        if total == 0:
            device.compliance_rate = 100
        else:
            installed = statuses.filter(state=DevicePatchStatus.State.INSTALLED).count()
            device.compliance_rate = round((installed / total) * 100, 1)
        
        device.save(update_fields=["compliance_rate"])
        logger.info(f"Updated compliance for {device.hostname}: {device.compliance_rate}%")
    except Device.DoesNotExist:
        logger.error(f"refresh_device_compliance: device {device_id} not found")


@shared_task
@trace
def refresh_all_device_compliance():
    """Batch refresh compliance for all devices."""
    from .models import Device
    devices = Device.objects.values_list('id', flat=True)
    for dev_id in devices:
        refresh_device_compliance.delay(str(dev_id))
    logger.info(f"Triggered compliance refresh for {len(devices)} devices.")


@shared_task
@trace
def sync_dynamic_group_memberships():
    """
    Periodic task to synchronize ManyToMany relationships for dynamic groups.
    Iterates through all groups with is_dynamic=True and updates their device associations.
    """
    from .models import DeviceGroup, Device
    
    dynamic_groups = DeviceGroup.objects.filter(is_dynamic=True)
    logger.info(f"Starting dynamic group membership sync for {dynamic_groups.count()} groups.")
    
    for group in dynamic_groups:
        try:
            # 1. Get the current matching devices based on rules
            matching_devices = Device.objects.filter_by_rules(group.dynamic_rules)
            
            # 2. Sync the ManyToMany association
            # .set() is efficient as it handles additions and removals in a single transaction
            group.devices.set(matching_devices)
            
            logger.info(f"Group '{group.name}' synced: {matching_devices.count()} members.")
        except Exception as e:
            logger.error(f"Failed to sync group '{group.name}': {str(e)}")

    logger.info("Dynamic group sync completed.")
