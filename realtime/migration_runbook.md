# Redis Streams Migration Runbook
## PatchGuard — Task 11.3

This document describes the zero-downtime migration from Redis Pub/Sub to Redis Streams for WebSocket fan-out.

---

## Background

The current system uses Redis Pub/Sub for broadcasting events from Django/Celery to connected WebSocket clients.  Pub/Sub has two critical limitations at scale:

| Limitation | Impact |
|---|---|
| **No persistence** | Messages lost if no subscriber is connected at publish time |
| **Duplicate delivery** | Every FastAPI instance receives every message → N broadcasts for N instances |

Redis Streams + Consumer Groups solve both problems:
- Events are **persisted** until ACK'd (retention window: 5 000 entries)
- Consumer groups ensure **exactly one** instance processes each message

---

## Components

| File | Purpose |
|---|---|
| `realtime/streams_producer.py` | XADD events to named Streams |
| `realtime/streams_consumer.py` | XREADGROUP loop + ACK in each FastAPI instance |
| `realtime/streams_compat.py` | Dual-write shim (Pub/Sub + Streams) during migration |
| `realtime/main.py` | Now starts both subscribers via env flags |

---

## Migration Phases

### Phase 1 — Dual Write (Current)

Both Pub/Sub and Streams are active simultaneously.

**In `.env`:**
```env
ENABLE_PUBSUB_SUBSCRIBER=true   # legacy
ENABLE_STREAMS_CONSUMER=true    # new
```

**Validation steps:**
1. Deploy updated `realtime/main.py` (rolling restart — zero downtime)
2. Publish a test event from Django:
   ```python
   # In Django shell
   import asyncio, redis.asyncio as aioredis, json, os
   r = aioredis.from_url(os.getenv("CELERY_BROKER_URL"))
   asyncio.run(r.publish("deployment:progress", json.dumps({"test": True})))
   ```
3. Verify in realtime logs: both `Redis Pub/Sub connected` and `Redis Streams consumer started`
4. Run integration tests: `cd realtime && pytest tests/test_streams.py -v`

---

### Phase 2 — Streams Only

Disable Pub/Sub subscriber once all realtime instances have been updated and streams have been validated for ≥ 24h.

**In `.env`:**
```env
ENABLE_PUBSUB_SUBSCRIBER=false  # disabled
ENABLE_STREAMS_CONSUMER=true    # only path
```

**Also update Django/Celery to use `CompatPublisher` or `EventProducer` directly** instead of `redis.publish()`.

**Validation steps:**
1. Disable Pub/Sub via env flag (rolling restart)
2. Verify logs show only `Redis Streams consumer started`
3. Deploy a test deployment; confirm progress events reach the UI
4. Monitor PEL (Pending Entry List) — should stay near zero:
   ```bash
   redis-cli XINFO GROUPS patchguard:deployment:progress
   ```

---

### Phase 3 — Cleanup

Remove `streams_compat.py` and `redis_subscriber()` from `main.py`.  
Django/Celery uses `EventProducer` directly.

---

## Rollback Procedure

If Streams cause issues, revert immediately:

```env
ENABLE_PUBSUB_SUBSCRIBER=true
ENABLE_STREAMS_CONSUMER=false
```

Rolling restart restores Pub/Sub behaviour in < 30 seconds.

---

## Monitoring

**Check PEL depth:**
```bash
redis-cli XINFO GROUPS patchguard:deployment:progress | grep pel-count
```

**Stream length:**
```bash
redis-cli XLEN patchguard:deployment:progress
redis-cli XLEN patchguard:system:notifications
```

**Realtime API stats endpoint** (includes PEL stats):
```
GET /rt/stats
```

**Backpressure warning threshold:** 500 entries in PEL → investigate stuck consumers.

---

## Redis Version Requirements

| Feature | Min Redis Version |
|---|---|
| XREADGROUP | 5.0 |
| XAUTOCLAIM | **7.0** |

The `XAUTOCLAIM`-based reclaim falls back gracefully on Redis < 7 with a warning log.

---

## Appendix — Stream Names

| Stream | Purpose |
|---|---|
| `patchguard:deployment:progress` | Deployment progress events |
| `patchguard:system:notifications` | System-wide notifications |
| `patchguard:system:compliance` | Compliance alerts |
| `patchguard:agent:commands:<agent_id>` | Targeted agent commands |
