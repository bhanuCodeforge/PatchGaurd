"""
Redis Streams consumer-group reader for the realtime FastAPI service.

Each FastAPI instance is a consumer in a shared consumer group.  The
Stream guarantees that each event is delivered to exactly ONE consumer
in the group, preventing duplicate broadcasts across instances.

Design:
  * Consumer group name:  "realtime-workers"
  * Consumer name:        unique per FastAPI instance (hostname + PID)
  * ACK policy:          Explicit ACK after successful fan-out to WebSockets
  * Backpressure:        If message queue grows > PEL_WARN_THRESHOLD, warn
  * Pending re-delivery: Stale claimed entries re-processed after CLAIM_IDLE_MS

Usage:
  from realtime.streams_consumer import StreamsConsumer
  consumer = StreamsConsumer(redis_url=REDIS_URL, manager=manager)
  await consumer.run()   # blocking — run as asyncio task
"""
import asyncio
import json
import logging
import os
import socket
import time
import redis.asyncio as aioredis
from ws_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Consumer group shared across all FastAPI instances
CONSUMER_GROUP = "realtime-workers"

# Unique consumer name per process
_INSTANCE_NAME = f"{socket.gethostname()}-{os.getpid()}"

# Stream names (must match streams_producer.py)
STREAM_DEPLOYMENT   = "patchguard:deployment:progress"
STREAM_SYSTEM       = "patchguard:system:notifications"
STREAM_COMPLIANCE   = "patchguard:system:compliance"
STREAM_AGENT_PREFIX = "patchguard:agent:commands:"

# XREADGROUP batch size
READ_BATCH = 20

# Block timeout for XREADGROUP (ms) — 0 = block indefinitely
BLOCK_MS = 2_000

# After this many messages in the Pending Entry List (PEL) emit a warning
PEL_WARN_THRESHOLD = 500

# Claim idle entries older than this (ms) — handles crashed consumers
CLAIM_IDLE_MS = 30_000

# Retry backoff on Redis errors
_MAX_BACKOFF = 60


class StreamsConsumer:
    """
    Async Redis Streams consumer-group reader.

    Call `run()` inside asyncio.create_task() — it loops forever,
    reading from all relevant streams and broadcasting to WebSocket clients.
    """

    def __init__(self, redis_url: str, manager: ConnectionManager):
        self._url = redis_url
        self._manager = manager
        self._redis: aioredis.Redis | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Redis connection
    # ------------------------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._url,
                decode_responses=True,
                health_check_interval=30,
            )
        return self._redis

    async def close(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    # ------------------------------------------------------------------
    # Consumer-group bootstrap
    # ------------------------------------------------------------------

    async def _ensure_groups(self) -> None:
        """
        Create consumer groups and streams if they don't exist yet.
        MKSTREAM creates the stream on first call if it's absent.
        """
        r = await self._get_redis()
        for stream in (STREAM_DEPLOYMENT, STREAM_SYSTEM, STREAM_COMPLIANCE):
            try:
                await r.xgroup_create(stream, CONSUMER_GROUP, id="$", mkstream=True)
                logger.info("Created consumer group '%s' on stream '%s'", CONSUMER_GROUP, stream)
            except aioredis.ResponseError as exc:
                if "BUSYGROUP" in str(exc):
                    pass  # Group already exists — normal on restart
                else:
                    raise

    # ------------------------------------------------------------------
    # Main read loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Main loop — reads from all streams in the consumer group,
        dispatches to WebSocket clients, and ACKs after dispatch.
        Reconnects with exponential backoff on failure.
        """
        self._running = True
        backoff = 2

        while self._running:
            try:
                await self._ensure_groups()
                await self._reclaim_pending()   # re-process crashed consumers on startup
                backoff = 2  # reset after successful connect

                while self._running:
                    await self._read_and_dispatch()

            except asyncio.CancelledError:
                logger.info("StreamsConsumer cancelled.")
                return
            except Exception as exc:
                logger.warning(
                    "StreamsConsumer error (%s: %s). Reconnecting in %ds…",
                    type(exc).__name__, exc, backoff,
                )
                if self._redis:
                    try:
                        await self._redis.aclose()
                    except Exception:
                        pass
                    self._redis = None

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    # ------------------------------------------------------------------
    # Read & dispatch
    # ------------------------------------------------------------------

    async def _read_and_dispatch(self) -> None:
        """
        Issue a single XREADGROUP call across all known streams, then
        dispatch each message and ACK the stream.
        """
        r = await self._get_redis()

        streams_spec: dict = {
            STREAM_DEPLOYMENT: ">",
            STREAM_SYSTEM: ">",
            STREAM_COMPLIANCE: ">",
        }

        results = await r.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername=_INSTANCE_NAME,
            streams=streams_spec,
            count=READ_BATCH,
            block=BLOCK_MS,
        )

        if not results:
            return   # block timeout — loop again

        for stream_name, entries in results:
            for entry_id, fields in entries:
                dispatched = await self._dispatch(stream_name, fields)
                if dispatched:
                    # ACK only after successful dispatch
                    await r.xack(stream_name, CONSUMER_GROUP, entry_id)
                else:
                    # Leave in PEL for reclaim on restart
                    logger.warning("Failed to dispatch entry %s from %s — left in PEL", entry_id, stream_name)

    async def _dispatch(self, stream: str, fields: dict) -> bool:
        """Route a stream entry to the appropriate WebSocket fan-out method."""
        try:
            raw_payload = fields.get("payload", "{}")
            channel = fields.get("channel", "")
            data = json.dumps({"channel": channel, "payload": json.loads(raw_payload)})

            if stream == STREAM_DEPLOYMENT:
                dep_id = fields.get("deployment_id")
                if dep_id:
                    await self._manager.broadcast_to_deployment(dep_id, data)
                return True

            elif stream in (STREAM_SYSTEM, STREAM_COMPLIANCE):
                await self._manager.broadcast_to_dashboard(data)
                return True

            elif stream.startswith(STREAM_AGENT_PREFIX):
                agent_id = fields.get("agent_id")
                if agent_id:
                    delivered = await self._manager.send_to_agent(agent_id, data)
                    if not delivered:
                        logger.warning("Agent %s offline — command not delivered", agent_id)
                return True

        except Exception as exc:
            logger.error("Dispatch error on stream %s: %s", stream, exc)
        return False

    # ------------------------------------------------------------------
    # Backpressure & reclaim
    # ------------------------------------------------------------------

    async def _reclaim_pending(self) -> None:
        """
        Claim and re-process entries stuck in the PEL from crashed consumers.
        Called once at startup.
        """
        r = await self._get_redis()

        for stream in (STREAM_DEPLOYMENT, STREAM_SYSTEM, STREAM_COMPLIANCE):
            try:
                # AUTOPENDINGCOUNT: iterate through pending entries
                start = "-"
                while True:
                    # Claim up to READ_BATCH entries idle > CLAIM_IDLE_MS
                    claimed = await r.xautoclaim(
                        stream,
                        CONSUMER_GROUP,
                        _INSTANCE_NAME,
                        min_idle_time=CLAIM_IDLE_MS,
                        start_id=start,
                        count=READ_BATCH,
                    )
                    # xautoclaim returns (next_id, entries, deleted)
                    next_id, entries, _ = claimed
                    if entries:
                        logger.info(
                            "Reclaimed %d pending entries from %s", len(entries), stream
                        )
                        for entry_id, fields in entries:
                            await self._dispatch(stream, fields)
                            await r.xack(stream, CONSUMER_GROUP, entry_id)

                    if next_id == "0-0":
                        break  # No more pending entries
                    start = next_id

            except aioredis.ResponseError as exc:
                # XAUTOCLAIM requires Redis 7+; gracefully skip on older Redis
                if "unknown command" in str(exc).lower():
                    logger.warning("XAUTOCLAIM not supported — skipping reclaim (requires Redis 7+)")
                    break
                logger.warning("Reclaim error on %s: %s", stream, exc)
            except Exception as exc:
                logger.warning("Reclaim error on %s: %s", stream, exc)

    async def check_backpressure(self) -> dict:
        """
        Return current stream depths and PEL sizes for monitoring.
        Emit a warning if PEL grows beyond threshold.
        """
        r = await self._get_redis()
        stats = {}
        for stream in (STREAM_DEPLOYMENT, STREAM_SYSTEM, STREAM_COMPLIANCE):
            try:
                info = await r.xinfo_groups(stream)
                for group in info:
                    if group["name"] == CONSUMER_GROUP:
                        pel = group.get("pel-count", 0)
                        if pel > PEL_WARN_THRESHOLD:
                            logger.warning(
                                "Backpressure warning: PEL on %s = %d (threshold %d)",
                                stream, pel, PEL_WARN_THRESHOLD,
                            )
                        stats[stream] = {"pel": pel, "consumers": group.get("consumers", 0)}
            except Exception as exc:
                stats[stream] = {"error": str(exc)}
        return stats
