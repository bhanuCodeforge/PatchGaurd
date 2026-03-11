"""
Redis-backed caching and rate-limiting for the BFF.

Uses redis.asyncio (same library already in requirements) with a dedicated
Redis DB so BFF state never collides with Django's application cache.
"""
import json
import time
import logging
import redis.asyncio as aioredis
from bff.config import REDIS_URL

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    return _redis


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

async def cache_get(key: str) -> dict | list | None:
    """Return parsed JSON from cache, or None on miss / Redis failure."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("BFF cache_get failed (%s) — bypassing cache", exc)
    return None


async def cache_set(key: str, value: dict | list, ttl: int) -> None:
    """Store JSON-serialised value with TTL.  Silently swallows Redis errors."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.warning("BFF cache_set failed (%s) — result not cached", exc)


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as exc:
        logger.warning("BFF cache_delete failed (%s)", exc)


# ---------------------------------------------------------------------------
# Rate-limiter  (sliding-window counter using INCR + EXPIRE)
# ---------------------------------------------------------------------------

async def is_rate_limited(client_key: str, limit: int, window_seconds: int = 60) -> bool:
    """
    Returns True if the client has exceeded `limit` requests in the last
    `window_seconds`.  Uses a simple fixed-window counter keyed by client IP
    + endpoint identifier.

    Fails open on Redis errors (returns False) to avoid availability impact.
    """
    try:
        r = await get_redis()
        rl_key = f"rl:{client_key}:{int(time.time()) // window_seconds}"
        count = await r.incr(rl_key)
        if count == 1:
            await r.expire(rl_key, window_seconds)
        return count > limit
    except Exception as exc:
        logger.warning("BFF rate_limit check failed (%s) — allowing request", exc)
        return False
