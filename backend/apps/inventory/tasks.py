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
    
    # Update device last scan time
    device.last_scan = timezone.now()
    device.save(update_fields=["last_scan"])

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


@shared_task(queue="default", name="apps.inventory.tasks.rotate_stale_api_keys")
def rotate_stale_api_keys(rotation_days: int = 90) -> dict:
    """
    Task 11.7 — Automated 90-day API key rotation.

    Finds every Device whose key_created_at (or key_last_rotated_at) is older
    than `rotation_days` days, generates a new key, persists it, and notifies
    the agent via Redis so it can refresh its config without manual intervention.

    The key is NEVER sent over WebSocket query-strings — the new key is pushed
    to the agent via the X-Agent-Key command channel so the agent can write it
    to its local config.yaml before the next reconnect.

    Register in Celery Beat (celery_app.py) to run daily.
    """
    import secrets
    from .models import Device

    cutoff = timezone.now() - timedelta(days=rotation_days)

    # Devices whose key is stale (use key_last_rotated_at if set, else key_created_at)
    stale_devices = Device.objects.filter(
        status__in=[Device.Status.ONLINE, Device.Status.OFFLINE],  # exclude decommissioned
    ).exclude(status=Device.Status.DECOMMISSIONED)

    # Filter to only stale keys in Python so we handle NULL timestamps gracefully
    to_rotate = []
    for dev in stale_devices.iterator():
        last_action = dev.key_last_rotated_at or dev.key_created_at
        if last_action is None or last_action < cutoff:
            to_rotate.append(dev)

    rotated = 0
    failed = 0
    for dev in to_rotate:
        new_key = secrets.token_urlsafe(32)
        try:
            dev.agent_api_key = new_key
            dev.key_last_rotated_at = timezone.now()
            dev.save(update_fields=["agent_api_key", "key_last_rotated_at"])

            # Notify agent via Redis — agent must handle KEY_ROTATED command
            # and write new key to its config.yaml before the next heartbeat cycle
            RedisPublisher.publish_agent_command(
                str(dev.id),
                "KEY_ROTATED",
                {
                    "new_api_key": new_key,
                    "effective_at": timezone.now().isoformat(),
                    "message": "API key rotated automatically. Update config.yaml before next reconnect.",
                },
            )
            rotated += 1
            logger.info("Key rotated for device %s (%s)", dev.hostname, dev.id)
        except Exception as exc:
            failed += 1
            logger.error("Key rotation failed for device %s: %s", dev.hostname, exc)

    logger.info("rotate_stale_api_keys: rotated=%d failed=%d (threshold=%d days)",
                rotated, failed, rotation_days)
    return {"rotated": rotated, "failed": failed, "threshold_days": rotation_days}
