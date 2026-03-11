# PatchGuard BFF — Backend-for-Frontend Gateway

The BFF is a lightweight **FastAPI** service that sits between the Angular frontend and the two backend services (Django + realtime FastAPI).  Angular points a **single base URL** at the BFF, which handles auth passthrough, caching, rate-limiting, and WebSocket relay.

```
Angular (4200) ──► BFF (8080) ──► Django (8000)
                            └──► Realtime (8001)
```

---

## Quick Start

### 1. Install Dependencies

```bash
# From repo root
pip install -r backend/requirements/base.txt
pip install -r backend/requirements/bff.txt
```

### 2. Configure Environment

Copy `.env.bff.example` → `.env` (already handled by the root `.env`).

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Django backend base URL |
| `REALTIME_URL` | `http://localhost:8001` | Realtime FastAPI base URL |
| `REALTIME_WS_URL` | `ws://localhost:8001` | Realtime WebSocket base URL |
| `BFF_REDIS_URL` | `redis://localhost:6379/2` | Redis DB for BFF cache |
| `BFF_CACHE_TTL` | `30` | Device list cache TTL (seconds) |
| `DASHBOARD_CACHE_TTL` | `10` | Dashboard aggregate cache TTL (seconds) |
| `RATE_LIMIT_DEVICES` | `60` | Max device list requests / min / client |
| `RATE_LIMIT_DASHBOARD` | `120` | Max dashboard requests / min / client |

### 3. Run the BFF

```bash
cd backend
uvicorn bff.main:app --host 0.0.0.0 --port 8080 --reload
```

Or using the convenience Makefile target:
```bash
make bff-run
```

### 4. Re-point Angular

In `frontend/src/environments/environment.ts`, change:
```typescript
// Before: two separate base URLs
apiUrl: 'http://localhost:8000',
wsUrl:  'ws://localhost:8001',

// After: single BFF base URL
apiUrl: 'http://localhost:8080',
wsUrl:  'ws://localhost:8080',
```

---

## Endpoints Proxied

| Method | Path | Behaviour |
|---|---|---|
| GET | `/bff/health` | BFF own health check |
| GET | `/api/v1/dashboard` | **Aggregated** — fans out to 3 Django endpoints, cached |
| GET | `/api/v1/devices/` | **Cached** — proxied with Redis caching + rate limit |
| * | `/api/v1/devices/{path}` | Proxied verbatim; writes invalidate device cache |
| * | `/api/**` | Generic pass-through proxy to Django |
| WS | `/ws/**` | WebSocket bidirectional relay to realtime service |

---

## Running Integration Tests

```bash
cd backend
pip install pytest pytest-asyncio respx
pytest bff/tests/ -v
```

---

## Architecture Notes

- **Auth**: JWT Bearer tokens are forwarded unchanged.  Cookie `access_token` is promoted to `Authorization: Bearer` header.
- **Caching**: Redis DB 2 (isolated from Django app cache on DB 1).  Cache keys are namespaced per user to prevent data leakage between accounts.
- **Rate Limiting**: Fixed-window counter using Redis INCR.  Fails open on Redis errors to preserve availability.
- **WS Relay**: Uses `websockets` async client for the upstream leg.  Messages are relayed bidirectionally; closing either end terminates both.
