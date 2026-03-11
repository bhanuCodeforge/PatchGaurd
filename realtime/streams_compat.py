"""
Compatibility shim — publish to BOTH Redis Pub/Sub AND Redis Streams.

Use this during the migration window so:
  * Old ws_manager.py instances reading Pub/Sub still work
  * New StreamsConsumer instances also receive the events

Once all FastAPI workers have been updated to use StreamsConsumer,
remove this shim and switch Django/Celery to use EventProducer directly.

Transition states:
  Phase 1 (current): Django uses CompatPublisher → both channels receive events
  Phase 2: Pub/Sub subscriber disabled in ws_manager → Streams only
  Phase 3: Remove CompatPublisher, Django uses EventProducer directly

See migration_runbook.md for step-by-step instructions.
"""
import json
import logging
import redis.asyncio as aioredis
from streams_producer import (
    EventProducer,
    STREAM_DEPLOYMENT,
    STREAM_SYSTEM,
    STREAM_COMPLIANCE,
)

logger = logging.getLogger(__name__)


class CompatPublisher:
    """
    Writes each event to both:
      1. Redis Pub/Sub channel (legacy — keeps old ws_manager alive)
      2. Redis Stream entry (new — for StreamsConsumer)

    Failure of either channel is logged but does not block the other.
    """

    def __init__(self, redis_url: str):
        self._url = redis_url
        self._redis: aioredis.Redis | None = None
        self._producer = EventProducer(redis_url)

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._url, decode_responses=True, health_check_interval=30
            )
        return self._redis

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
        await self._producer.close()

    async def publish_deployment_event(
        self, deployment_id: str, payload: dict
    ) -> None:
        envelope = json.dumps({
            "event": "deployment_progress",
            "payload": {**payload, "deployment_id": deployment_id},
        })

        # 1. Legacy Pub/Sub
        try:
            r = await self._get_redis()
            await r.publish("deployment:progress", envelope)
        except Exception as exc:
            logger.warning("CompatPublisher legacy pubsub failed: %s", exc)

        # 2. New Streams
        try:
            await self._producer.publish_deployment_event(deployment_id, payload)
        except Exception as exc:
            logger.warning("CompatPublisher streams failed: %s", exc)

    async def publish_system_notification(self, payload: dict) -> None:
        envelope = json.dumps({"event": "system_notification", "payload": payload})

        try:
            r = await self._get_redis()
            await r.publish("system:notification", envelope)
        except Exception as exc:
            logger.warning("CompatPublisher legacy pubsub failed: %s", exc)

        try:
            await self._producer.publish_system_notification(payload)
        except Exception as exc:
            logger.warning("CompatPublisher streams failed: %s", exc)

    async def publish_compliance_alert(self, payload: dict) -> None:
        envelope = json.dumps({"event": "compliance_alert", "payload": payload})

        try:
            r = await self._get_redis()
            await r.publish("system:compliance_alert", envelope)
        except Exception as exc:
            logger.warning("CompatPublisher legacy pubsub failed: %s", exc)

        try:
            await self._producer.publish_compliance_alert(payload)
        except Exception as exc:
            logger.warning("CompatPublisher streams failed: %s", exc)

    async def publish_agent_command(self, agent_id: str, payload: dict) -> None:
        envelope = json.dumps({"event": "agent_command", "payload": payload})

        try:
            r = await self._get_redis()
            await r.publish(f"agent:command:{agent_id}", envelope)
        except Exception as exc:
            logger.warning("CompatPublisher legacy pubsub failed: %s", exc)

        try:
            await self._producer.publish_agent_command(agent_id, payload)
        except Exception as exc:
            logger.warning("CompatPublisher streams failed: %s", exc)
