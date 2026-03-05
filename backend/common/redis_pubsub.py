import json
from django.utils import timezone
from django.conf import settings
import redis
import logging

logger = logging.getLogger(__name__)

class RedisPublisher:
    """Centralized Redis pub/sub helper for standardizing websocket payloads."""
    
    # Core system channels
    DEPLOYMENT_PROGRESS = "deployment:progress"
    AGENT_STATUS = "agent:status"
    AGENT_COMMAND_PREFIX = "agent:command:"
    DEVICE_ONLINE = "device:online"
    DEVICE_OFFLINE = "device:offline"
    NEW_PATCHES = "system:new_patches"
    COMPLIANCE_ALERT = "system:compliance_alert"
    SYSTEM_NOTIFICATION = "system:notification"

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            cls._client = redis.Redis.from_url(redis_url, decode_responses=True)
        return cls._client

    @classmethod
    def publish(cls, channel: str, event_type: str, payload: dict):
        """Create and publish enveloped standard message format."""
        message = {
            "event": event_type,
            "payload": payload,
            "timestamp": timezone.now().isoformat()
        }
        try:
            client = cls.get_client()
            client.publish(channel, json.dumps(message))
            logger.debug(f"Published to {channel}: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish to redis channel {channel}: {e}")

    @classmethod
    def publish_deployment_progress(cls, deployment_id: str, progress_data: dict):
        cls.publish(cls.DEPLOYMENT_PROGRESS, "update", {"deployment_id": str(deployment_id), **progress_data})

    @classmethod
    def publish_device_status(cls, device_id: str, hostname: str, status: str):
        channel = cls.DEVICE_ONLINE if status == "online" else cls.DEVICE_OFFLINE
        cls.publish(channel, "status_change", {"device_id": str(device_id), "hostname": hostname, "status": status})

    @classmethod
    def publish_agent_command(cls, agent_id: str, command: str, args: dict = None):
        if args is None:
            args = {}
        cls.publish(f"{cls.AGENT_COMMAND_PREFIX}{agent_id}", command, args)

    @classmethod
    def publish_notification(cls, level: str, message: str):
        cls.publish(cls.SYSTEM_NOTIFICATION, level, {"message": message})

    @classmethod
    def publish_compliance_alert(cls, group_id: str, metric: float):
        cls.publish(cls.COMPLIANCE_ALERT, "threshold_breach", {"group_id": str(group_id), "metric": metric})
