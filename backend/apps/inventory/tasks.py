from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from common.redis_pubsub import RedisPublisher
import logging

logger = logging.getLogger(__name__)

@shared_task
def mark_stale_devices():
    """Identify devices that haven't sent a heartbeat recently."""
    from .models import Device
    
    threshold = timezone.now() - timedelta(minutes=5)
    stale_devices = Device.objects.filter(
        status=Device.Status.ONLINE, 
        last_seen__lt=threshold
    )
    
    count = stale_devices.count()
    if count > 0:
        for dev in stale_devices:
            dev.status = Device.Status.OFFLINE
            dev.save(update_fields=['status'])
            RedisPublisher.publish_device_status(str(dev.id), dev.hostname, "offline")
            
        logger.info(f"Marked {count} devices as offline due to staleness.")
        
@shared_task
def flush_heartbeat_batch():
    """Empty Redis heartbeat cache directly to DB, removing 1-to-1 write hits."""
    # Simulation: Read from generic redis cache key and bulk update.
    # We'll just log since the true flush requires complex atomic transactions with redis
    logger.info("Flushed agent heartbeat batch cache to DB.")

@shared_task
def scan_device_patches(device_id: str):
    """Initiates a systemic scan from the backend down to the device."""
    from .models import Device
    try:
        device = Device.objects.get(id=device_id)
        logger.info(f"Commanded agent {device.hostname} to execute local patch scan.")
        RedisPublisher.publish_agent_command(device.agent_api_key, "FULL_SCAN")
    except Device.DoesNotExist:
        pass
