
# Task 11.2 — BFF / API Gateway Prototype

**Time**: 3–5 days  
**Depends on**: 11.1
**Status**: ✅ Complete  
**Files**: `backend/bff/`, `backend/bff/README.md`, `backend/bff/tests/test_bff.py`

---

## Scope

Lightweight FastAPI BFF that aggregates critical endpoints and gives Angular a single base URL.

---

## Checklist

- [x] Auth passthrough (cookie/header translation)
- [x] Aggregate /api/v1/dashboard endpoint
- [x] Proxy /api/v1/devices list with caching
- [x] WebSocket pass-through for /ws/
- [x] README with run/re-point instructions
- [x] Integration tests verifying endpoint parity

---

## Acceptance Criteria

- [x] Angular uses single base URL for all API and realtime calls
- [x] Rate-limiting and caching applied at BFF for heavy endpoints
- [x] Integration tests pass for all proxied/aggregated endpoints

---

## Implementation

### Files Created

| File | Purpose |
|---|---|
| `backend/bff/__init__.py` | Package doc |
| `backend/bff/config.py` | Environment-based configuration |
| `backend/bff/auth.py` | Auth passthrough (Bearer + cookie → header) |
| `backend/bff/cache.py` | Redis caching + fixed-window rate limiter |
| `backend/bff/proxy.py` | Shared async httpx client + proxy helpers |
| `backend/bff/main.py` | FastAPI app entry point, CORS, lifespan |
| `backend/bff/routes/dashboard.py` | Aggregated `/api/v1/dashboard` (fan-out + cache) |
| `backend/bff/routes/devices.py` | Cached `/api/v1/devices/` proxy with write invalidation |
| `backend/bff/routes/api_proxy.py` | Generic catch-all pass-through to Django |
| `backend/bff/routes/ws_proxy.py` | Bidirectional WebSocket relay to realtime service |
| `backend/bff/tests/test_bff.py` | Integration tests |
| `backend/bff/README.md` | Setup and re-point instructions |
| `backend/requirements/bff.txt` | Additional dependencies |

### Re-pointing Angular

Set `apiUrl` and `wsUrl` to `http://localhost:8080` (or the BFF host) in `environments/environment.ts`.

---

## Completion Log

**Completed**: 2026-04-11  
**Notes**: BFF runs on port 8080. Uses Redis DB 2 for caching to avoid collision with Django app cache.