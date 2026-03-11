
# Task 11.3 — Redis Streams Migration for WebSocket Fan-out

**Time**: 5–10 days  
**Depends on**: 11.1
**Status**: ✅ Complete  
**Files**: `realtime/streams_producer.py`, `realtime/streams_consumer.py`, `realtime/streams_compat.py`, `realtime/migration_runbook.md`, `realtime/tests/test_streams.py`

---

## Scope

Replace Redis pub/sub fan-out with Redis Streams + consumer groups in ws_manager.

---

## Checklist

- [x] Implement Streams producer for events
- [x] Add FastAPI consumer group reader for local connections
- [x] Handle backpressure and consumer acknowledgements
- [x] Write migration plan and compatibility shim
- [x] Document runbook for migration
- [x] Integration tests for no-duplicate delivery

---

## Acceptance Criteria

- [x] No duplicate broadcasts across FastAPI instances
- [x] Messages persisted and delivered at-least-once
- [x] Migration performable with zero downtime

---

## Implementation

### Files Created / Modified

| File | Change | Purpose |
|---|---|---|
| `realtime/streams_producer.py` | **New** | Async XADD producer for 4 stream topics |
| `realtime/streams_consumer.py` | **New** | Consumer group reader with XREADGROUP loop + XAUTOCLAIM reclaim |
| `realtime/streams_compat.py` | **New** | Dual-write shim (Pub/Sub + Streams) — Phase 1 migration |
| `realtime/main.py` | **Modified** | Starts both Pub/Sub subscriber and Streams consumer via env flags |
| `realtime/migration_runbook.md` | **New** | 3-phase zero-downtime migration runbook |
| `realtime/tests/test_streams.py` | **New** | Integration tests for producer, consumer dispatch, no-duplicate delivery |

### Key Design Decisions

- **Consumer group**: `realtime-workers` — shared across all FastAPI instances, ensuring each message processed by exactly one instance.
- **ACK policy**: Explicit ACK after successful WebSocket broadcast. Failed dispatches left in PEL for reclaim.
- **Reclaim**: `XAUTOCLAIM` (Redis 7+) claims entries idle >30s from crashed consumers on startup. Graceful fallback for Redis <7.
- **Backpressure**: PEL monitored; warning logged when >500 unacknowledged entries.
- **Migration flags**: `ENABLE_PUBSUB_SUBSCRIBER` and `ENABLE_STREAMS_CONSUMER` env vars allow gradual cutover without code changes.

### Streams

| Stream Name | Purpose |
|---|---|
| `patchguard:deployment:progress` | Per-deployment progress events |
| `patchguard:system:notifications` | System-wide broadcast |
| `patchguard:system:compliance` | Compliance alerts |
| `patchguard:agent:commands:<id>` | Targeted agent commands |

---

## Completion Log

**Completed**: 2026-04-11  
**Notes**: Zero-downtime migration via dual-write compat shim. See `realtime/migration_runbook.md` for Phase 2 & 3 cutover instructions. Requires Redis ≥ 5.0 (7.0 for XAUTOCLAIM reclaim).