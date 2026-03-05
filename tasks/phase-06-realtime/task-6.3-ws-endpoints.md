# Task 6.3 — WebSocket Endpoints (Dashboard + Agent)

**Time**: 4 hours  
**Dependencies**: 6.2  
**Status**: ✅ Done  
**Files**: `realtime/routes/agents.py`, `realtime/routes/events.py`, `realtime/agent_protocol.py`

---

## AI Prompt

```
Implement the WebSocket endpoints and agent protocol handler for PatchGuard.

1. realtime/agent_protocol.py — Protocol definitions:
   - AgentToServer message types: heartbeat, system_info, patch_status, scan_result, reboot_complete
   - ServerToAgent message types: install_patches, scan_patches, reboot, cancel, update_agent
   - ServerToDashboard message types: deployment_progress, patch_status_update, device_online, device_offline, notification
   - Pydantic models for each message type

2. realtime/routes/agents.py:
   - WebSocket /ws/dashboard — JWT auth, subscribe to deployment groups
   - WebSocket /ws/agent — API key auth, handle heartbeat/patch_status/system_info/scan_result

3. realtime/routes/events.py — REST endpoints:
   - POST /rt/agents/{device_id}/command
   - GET /rt/agents/online
   - GET /rt/stats

4. Redis subscriber for agent commands (bridge: Celery → Redis → FastAPI → WebSocket → Agent)

Write integration tests for all WebSocket flows.
```

---

## Acceptance Criteria

- [x] Dashboard WebSocket connects and receives real-time updates
- [x] Agent WebSocket connects, sends heartbeats, receives commands
- [x] Patch status updates flow: Agent → FastAPI → DB + Redis → Dashboard
- [x] Celery commands reach agents via Redis → FastAPI → WebSocket bridge
- [x] Dead agent detection works
- [x] All message types validated via Pydantic
- [x] No unhandled exceptions crash the service
- [x] All tests pass

## Files Created/Modified

- [x] `realtime/agent_protocol.py`
- [x] `realtime/routes/agents.py`
- [x] `realtime/routes/events.py`
- [x] `realtime/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
