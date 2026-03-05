# Task 6.2 — WebSocket Connection Manager

**Time**: 3 hours  
**Dependencies**: 6.1  
**Status**: ✅ Done  
**Files**: `realtime/ws_manager.py`

---

## AI Prompt

```
Implement the WebSocket connection manager for PatchGuard real-time service.

realtime/ws_manager.py — ConnectionManager class:

Methods:
1. connect_dashboard(ws, user_id) — Accept, add to "dashboard" group
2. connect_agent(ws, agent_id) — Accept, add to "agents" group, update Redis heartbeat
3. disconnect(ws, identifier) — Remove from all groups, cleanup
4. broadcast_to_group(group, message) — Send to all in group, remove dead connections
5. send_to_agent(agent_id, message) → bool — Send to specific agent
6. broadcast_to_all_agents(message) — Send to all agents
7. get_online_agents() → list[str]
8. get_agent_count() / get_dashboard_count() → int
9. subscribe_to_deployment(ws, deployment_id) — Targeted deployment updates
10. unsubscribe_from_deployment(ws, deployment_id)

Connection health: ping/pong tracking, 60s timeout for dead connections.

Write comprehensive tests for all methods including concurrent access.
```

---

## Acceptance Criteria

- [x] Dashboard connections are tracked in groups
- [x] Agent connections are tracked individually
- [x] Broadcast sends to all group members
- [x] Dead connections are cleaned up automatically
- [x] Ping/pong health monitoring works
- [x] Thread-safe under concurrent access
- [x] All tests pass

## Files Created/Modified

- [x] `realtime/ws_manager.py`
- [x] `realtime/tests/test_ws_manager.py`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
