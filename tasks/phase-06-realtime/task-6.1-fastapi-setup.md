# Task 6.1 — FastAPI Application Setup

**Time**: 3 hours  
**Dependencies**: 1.4, 3.1  
**Status**: ✅ Done  
**Files**: `realtime/main.py`, `realtime/auth.py`, `realtime/routes/health.py`

---

## AI Prompt

```
Implement the FastAPI real-time service foundation for PatchGuard.

1. realtime/main.py:
   - Lifespan context manager (startup/shutdown)
   - aioredis connection, asyncpg connection pool
   - Background tasks: redis_subscriber(), heartbeat_monitor()
   - Include routers: agents, events, health

2. realtime/auth.py:
   - verify_jwt(authorization) → dict (from Authorization header)
   - verify_ws_token(websocket, token) → dict (from query param)
   - verify_agent_key(websocket, api_key) → str (device_id)

3. realtime/routes/health.py:
   - GET /health → basic health check
   - GET /health/detailed → detailed health (admin only)

4. realtime/requirements.txt:
   - fastapi, uvicorn, websockets, redis, asyncpg, PyJWT, pydantic

Write basic tests for auth functions and health endpoint.
```

---

## Acceptance Criteria

- [x] FastAPI starts and serves /rt/docs
- [x] Health endpoint reports correct service status
- [x] JWT verification works with tokens from Django
- [x] Agent API key verification works
- [x] Redis subscriber starts and listens
- [x] Tests pass

## Files Created/Modified

- [x] `realtime/main.py`
- [x] `realtime/auth.py`
- [x] `realtime/routes/health.py`
- [x] `realtime/requirements.txt`
- [x] `realtime/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
