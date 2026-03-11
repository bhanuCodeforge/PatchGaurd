"""
Redis Streams producer for PatchGuard realtime events.

Replaces the Redis Pub/Sub PUBLISH calls from Django/Celery with XADD to a
named Stream.  Consumer groups (in ws_manager.py) then read from these
Streams, providing:

  * At-least-once delivery  (messages are persisted until ACK'd)
  * No duplicate broadcasts across FastAPI instances  (each instance is one
    consumer in a group; the Stream ensures each message is processed once)
  * Zero-downtime migration via a compatibility shim (see streams_compat.py)

Stream names:
  patchguard:deployment:progress    — deployment progress events
  patchguard:system:notifications   — system-wide notifications
  patchguard:system:compliance      — compliance alert events
  patchguard:agent:commands         — targeted agent command events

Usage (from Django/Celery — drop-in replacement for redis.publish):

    from realtime.streams_producer import EventProducer

    producer = EventProducer(redis_url=settings.REDIS_URL)
    await producer.publish_deployment_event(deployment_id, payload_dict)
"""
import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Stream names
STREAM_DEPLOYMENT   = "patchguard:deployment:progress"
STREAM_SYSTEM       = "patchguard:system:notifications"
STREAM_COMPLIANCE   = "patchguard:system:compliance"
STREAM_AGENT_PREFIX = "patchguard:agent:commands:"

# Keep the stream trimmed to avoid unbounded growth.
# At-least-once semantics are maintained within this window.
MAX_STREAM_LEN = 5_000
MAXLEN_APPROX = True   # use ~ trimming for performance


class EventProducer:
    """
    Async Redis Streams producer.

    One instance is typically shared per Django worker / Celery task.
    Connection is lazily established and re-used.
    """

    def __init__(self, redis_url: str):
        self._url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._url,
                decode_responses=True,
                health_check_interval=30,
            )
        return self._redis

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    # ------------------------------------------------------------------
    # Core XADD helper
    # ------------------------------------------------------------------

    async def _xadd(self, stream: str, fields: dict) -> str | None:
        """
        Add an entry to a Redis Stream.

        Returns the generated entry ID (e.g. '1712345678901-0'), or None
        on error.  Never raises — callers should treat None as a warning.
        """
        try:
            r = await self._get_redis()
            entry_id = await r.xadd(
                stream,
                fields,
                maxlen=MAX_STREAM_LEN,
                approximate=MAXLEN_APPROX,
            )
            logger.debug("XADD %s → %s", stream, entry_id)
            return entry_id
        except Exception as exc:
            logger.error("EventProducer.xadd(%s) failed: %s", stream, exc)
            return None

    # ------------------------------------------------------------------
    # Domain-specific publish methods
    # ------------------------------------------------------------------

    async def publish_deployment_event(
        self, deployment_id: str, payload: dict
    ) -> str | None:
        """Publish a deployment progress event to the deployment stream."""
        fields = {
            "deployment_id": deployment_id,
            "payload": json.dumps(payload),
            "channel": "deployment:progress",
        }
        return await self._xadd(STREAM_DEPLOYMENT, fields)

    async def publish_system_notification(self, payload: dict) -> str | None:
        """Publish a system-wide notification (compliance alert, etc.)."""
        fields = {
            "payload": json.dumps(payload),
            "channel": "system:notification",
        }
        return await self._xadd(STREAM_SYSTEM, fields)

    async def publish_compliance_alert(self, payload: dict) -> str | None:
        """Publish a compliance alert event."""
        fields = {
            "payload": json.dumps(payload),
            "channel": "system:compliance_alert",
        }
        return await self._xadd(STREAM_COMPLIANCE, fields)

    async def publish_agent_command(
        self, agent_id: str, payload: dict
    ) -> str | None:
        """Publish a targeted command for a specific agent."""
        stream = f"{STREAM_AGENT_PREFIX}{agent_id}"
        fields = {
            "agent_id": agent_id,
            "payload": json.dumps(payload),
            "channel": f"agent:command:{agent_id}",
        }
        # Agent command streams are short-lived; keep them small
        try:
            r = await self._get_redis()
            entry_id = await r.xadd(stream, fields, maxlen=100, approximate=True)
            logger.debug("XADD agent command %s → %s", stream, entry_id)
            return entry_id
        except Exception as exc:
            logger.error("EventProducer.publish_agent_command(%s) failed: %s", agent_id, exc)
            return None
