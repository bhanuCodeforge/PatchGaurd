
# Task 11.3 — Redis Streams Migration for WebSocket Fan-out

**Time**: 5–10 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: `realtime/ws_manager`, migration doc, integration tests

---

## Scope

Replace Redis pub/sub based fan-out with Redis Streams + consumer groups and implement connection groups in `ws_manager`.

---

## Checklist

- [ ] Implement Streams producer for events
- [ ] Add FastAPI consumer group reader for local connections
- [ ] Handle backpressure and consumer acknowledgements
- [ ] Write migration plan and compatibility shim
- [ ] Document runbook for migration
- [ ] Add integration tests for no-duplicate delivery

---

## Acceptance Criteria

- [ ] No duplicate broadcasts across FastAPI instances
- [ ] Messages are persisted and delivered at-least-once
- [ ] Migration can be performed with zero downtime

---

## Completion Log

**Completed**:  
**Notes**: 