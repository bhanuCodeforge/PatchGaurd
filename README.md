# PatchGuard — Enterprise Patch Management Platform

> Automated, policy-driven patch deployment across Windows, Linux, and macOS fleets with real-time monitoring, compliance dashboards, and event-sourced audit trails.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Explanations](#module-explanations)
3. [Setup Instructions](#setup-instructions)
4. [Environment Configuration](#environment-configuration)
5. [Running the Stack](#running-the-stack)
6. [VS Code Debug Configurations](#vs-code-debug-configurations)
7. [API Reference](#api-reference)
8. [Known Issues & Assumptions](#known-issues--assumptions)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Angular Frontend                             │
│                      http://localhost:4200                           │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│             BFF — Backend-for-Frontend (FastAPI)                     │
│                      http://localhost:8080                           │
│  • Single entry point for Angular                                    │
│  • Proxies REST → Django, WS → Realtime Service                      │
│  • Caches compliance stats from Redis materialized view              │
└────────────┬─────────────────────────────────────┬───────────────────┘
             │ REST                                 │ WS proxy
             ▼                                     ▼
┌────────────────────────┐           ┌─────────────────────────────────┐
│   Django REST API      │           │  Realtime Service (FastAPI WS)  │
│   http://localhost:8000│           │  ws://localhost:8001             │
│                        │           │                                 │
│  • Auth & JWT          │◄──Redis──►│  • /ws/dashboard (JWT)          │
│  • Devices / Inventory │  Pub/Sub  │  • /ws/agent (API key)          │
│  • Patches & Scans     │  Streams  │  • Bridges Redis messages →WS   │
│  • Deployments         │           │  • Persists agent data → Django  │
│  • Compliance          │           └─────────────┬───────────────────┘
│  • Audit Log           │                         │ WebSocket
└────────────┬───────────┘                         │
             │                                     │
             ▼                                     ▼
┌────────────────────────┐           ┌─────────────────────────────────┐
│  Celery Workers        │           │   PatchGuard Agent              │
│  (Redis broker)        │           │   (Python daemon on endpoints)   │
│                        │           │                                 │
│  • Deployment          │           │  • Collects system inventory    │
│    orchestration       │           │  • Sends heartbeats             │
│  • Wave execution      │           │  • Runs patch scans             │
│  • Result recording    │           │  • Installs patches             │
│  • Compliance refresh  │           │  • Reports results via WS       │
│  • Agent key rotation  │           └─────────────────────────────────┘
└────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                            │
│  PostgreSQL (primary DB)  +  Redis (broker, cache, pub/sub/streams)│
└────────────────────────────────────────────────────────────────────┘
```

### Data Flows

| Flow | Path |
|------|------|
| Agent heartbeat | Agent → WS → Realtime → Django REST `POST /devices/{id}/heartbeat/` |
| Patch scan | Django Celery → Redis `agent:command:{id}` → Realtime → Agent WS `START_SCAN` → Agent → Realtime → Django REST `POST /devices/{id}/ingest_scan/` |
| Deployment | Django (`orchestrate_deployment` task) → Redis → Agent → WS `patch_result` → Realtime → Django REST `POST /deployments/{id}/ingest_patch_result/` → `report_device_result` Celery task |
| Live progress | `report_device_result` Celery → `RedisPublisher.publish_deployment_progress` → Realtime subscriber → WS broadcast → Angular dashboard |

---

## Module Explanations

### `backend/` — Django REST API

| App | Purpose |
|-----|---------|
| `apps/accounts` | User management, JWT auth, RBAC roles (admin/operator/viewer), LDAP sync, audit log |
| `apps/inventory` | Device registry, device groups (static + dynamic), heartbeat ingestion, compliance rate |
| `apps/patches` | Patch catalog, scan results, compliance snapshots, SLA breach checks |
| `apps/deployments` | Deployment lifecycle, wave orchestration (Task 11.4), event sourcing (Task 11.5) |
| `common/` | Shared utilities: RedisPublisher, agent auth, pagination, middleware, logging |
| `bff/` | Backend-for-Frontend FastAPI gateway that aggregates and caches API responses |
| `config/` | Django settings, Celery configuration, URL routing |

#### Celery Task Hierarchy (Phase 11.4)

```
orchestrate_deployment  [critical queue]
  └─► execute_wave      [deployment-waves queue, 15min soft limit]
        └─► report_device_result  [deployment-results queue, acks_late=True]
```

Beat schedule (key tasks):

| Task | Schedule |
|------|----------|
| `mark_stale_devices` | Every 5 min |
| `process_scheduled_deployments` | Every 1 min |
| `monitor_stuck_waves` | Every 10 min |
| `refresh_compliance_materialized_view` | Every hour |
| `rotate_stale_api_keys` | Daily 02:30 UTC |

### `realtime/` — FastAPI WebSocket Service

| File | Purpose |
|------|---------|
| `main.py` | App entrypoint, Redis Pub/Sub subscriber, Streams consumer, asyncpg pool |
| `ws_manager.py` | `ConnectionManager`: dashboard WS map, agent WS map, deployment subscriptions |
| `routes/agents.py` | `/ws/agent` (API key auth), `/ws/dashboard` (JWT auth), event routing |
| `routes/events.py` | REST endpoints: `/rt/agents/online`, `/rt/stats`, `/rt/agents/{id}/command` |
| `auth.py` | `verify_jwt`, `verify_ws_token`, `verify_agent_key` (asyncpg direct query) |
| `streams_consumer.py` | New: Redis Streams consumer group (replaces Pub/Sub) |
| `streams_producer.py` | New: Redis Streams XADD producer |
| `streams_compat.py` | Migration shim: publishes to BOTH Pub/Sub and Streams during transition |

#### WebSocket Message Envelope

All WS messages follow this envelope:
```json
{ "event": "string", "payload": { ... } }
```

### `agent/` — Endpoint Agent

| File | Purpose |
|------|---------|
| `agent.py` | `PatchAgent` class: WS connection loop, heartbeat, command handler, deployment runner |
| `config.yaml` | Device-specific runtime config (api_key, server_url — gitignored) |
| `config.yaml.example` | Safe template to copy |
| `plugins/` | OS-specific patch management (Linux apt/yum, Windows WUA, macOS brew) |
| `collectors/` | `LaneScheduler`: fast-lane metrics (5s) and slow-lane inventory (15min) |

#### Agent Command Protocol

| Command | Direction | Handler |
|---------|-----------|---------|
| `START_SCAN` | Server → Agent | `run_scan()` |
| `START_DEPLOYMENT` | Server → Agent | `run_deployment()` |
| `CANCEL_DEPLOYMENT` | Server → Agent | Logs cancellation |
| `HEALTH_CHECK` | Server → Agent | `run_health_check()` |
| `KEY_ROTATED` | Server → Agent | Updates `config.yaml`, reconnects |
| `CONFIG_UPDATE` | Server → Agent | Updates live config |
| `REBOOT` | Server → Agent | `plugin.reboot()` |
| `PING` | Server → Agent | Sends `pong` |

### `frontend/` — Angular 21 SPA

| Module | Path | Purpose |
|--------|------|---------|
| Dashboard | `features/dashboard` | Fleet overview, compliance KPIs |
| Devices | `features/devices` | Inventory list, device detail, groups |
| Patches | `features/patches` | Patch catalog, approval workflow |
| Deployments | `features/deployments` | Wizard, list, live monitor |
| Compliance | `features/compliance` | Compliance reports, trend charts |
| Audit | `features/audit` | Audit log viewer |
| Settings | `features/settings` | System settings |

Key services: `DeviceService`, `DeploymentService`, `WebsocketService`, `NotificationService`

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 20+ / npm 10+
- PostgreSQL 15+ (or SQLite for dev)
- Redis 7+

### 1. Clone & Environment

```bash
git clone https://github.com/your-org/patchguard.git
cd patchguard
cp .env.example .env
# Edit .env with your Postgres, Redis, and JWT settings
```

### 2. Backend Setup

```bash
# Create Python virtualenv
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r backend/requirements/dev.txt

# Run migrations
cd backend
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# (Optional) Load seed data
python manage.py loaddata fixtures/demo.json
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Agent Setup

```bash
cd agent
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml: set api_key and optionally device_id_override
# OR set auto_register: true to auto-register on first run
```

### 5. Docker (full stack)

```bash
docker compose up --build
```

---

## Environment Configuration

Copy `.env.example` → `.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL DSN | SQLite for dev |
| `CELERY_BROKER_URL` | Redis DSN for Celery | `redis://localhost:6379/0` |
| `REDIS_CACHE_URL` | Redis DSN for cache | `redis://localhost:6379/1` |
| `DJANGO_SECRET_KEY` | Django secret key | dev insecure key |
| `JWT_SECRET_KEY` | JWT signing key | `dev_secret_key_change_in_prod` |
| `REALTIME_LOG_LEVEL` | Realtime service log level | `INFO` |
| `BACKEND_URL` | URL realtime uses to POST to Django | `http://localhost:8000/api/v1` |
| `ENABLE_PUBSUB_SUBSCRIBER` | Legacy Redis Pub/Sub (migration flag) | `true` |
| `ENABLE_STREAMS_CONSUMER` | New Redis Streams consumer (migration flag) | `true` |

---

## Running the Stack

### Native (development)

```bash
# Terminal 1 — Django
cd backend && python manage.py runserver 8000

# Terminal 2 — Celery Worker
cd backend && celery -A config.celery_app worker -l info -Q critical,default,deployment-waves,deployment-results,reporting

# Terminal 3 — Celery Beat
cd backend && celery -A config.celery_app beat -l info

# Terminal 4 — Realtime WebSocket Service
cd realtime && uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 5 — BFF (optional)
cd backend && uvicorn bff.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 6 — Frontend
cd frontend && npx ng serve --proxy-config proxy.conf.json --host 127.0.0.1 --port 4200

# Terminal 7 — Agent (on endpoint machine)
cd agent && python agent.py
```

---

## VS Code Debug Configurations

Open the Run & Debug panel (Ctrl+Shift+D) and choose:

| Configuration | Description |
|---------------|-------------|
| `Django: Debug Server` | Django on port 8000 with debugpy |
| `Realtime (WS): Debug Server` | FastAPI realtime on port 8001 |
| `BFF: Debug Server` | FastAPI BFF on port 8080 |
| `Celery: Debug Worker` | Celery worker (all queues) |
| `Celery: Debug Beat` | Celery Beat scheduler |
| `Angular: Serve` | Frontend dev server on port 4200 |
| `Agent: Debug Run` | Agent process |
| **`Debug: Full Platform`** | Django + Realtime + Worker + Angular |
| **`Debug: Everything`** | Full stack + Beat + Agent |
| **`Debug: Full Stack + BFF`** | Everything + BFF (Phase 11) |

---

## API Reference

### Django REST API — `http://localhost:8000/api/v1/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login/` | Obtain JWT tokens |
| GET | `/devices/` | List devices |
| POST | `/devices/{id}/heartbeat/` | Agent heartbeat |
| GET | `/deployments/` | List deployments |
| POST | `/deployments/{id}/execute/` | Start deployment |
| GET | `/deployments/{id}/events/` | Deployment event audit log |
| POST | `/deployments/{id}/ingest_patch_result/` | Agent patch result |
| GET | `/patches/` | Patch catalog |
| GET | `/dashboard/stats/` | Dashboard aggregate stats |

Full OpenAPI docs: `http://localhost:8000/api/schema/swagger-ui/`

### Realtime WebSocket — `ws://localhost:8001`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `/ws/dashboard?token=JWT` | JWT | Dashboard real-time feed |
| `/ws/agent?api_key=KEY` | Agent API Key | Agent command & reporting channel |

### BFF — `http://localhost:8080`

| Path | Description |
|------|-------------|
| `/bff/health` | Health check |
| `/bff/docs` | OpenAPI docs |
| `/bff/api/v1/*` | Proxy → Django |
| `/bff/ws/*` | Proxy → Realtime |

---

## Known Issues & Assumptions

### Platform Assumptions

- **PostgreSQL required** for production. The compliance materialized view (`mv_compliance_stats`) and audit log partitioning are PostgreSQL-specific. The materialized view refresh task gracefully skips on SQLite.
- **Redis required** for deployment orchestration. Without Redis, Celery tasks queue in memory only and are lost on restart.
- **aiohttp required** on the agent for REST heartbeat and auto-registration. If absent, these features silently disable themselves.

### Architecture Decisions

- **Dual-path Redis (Pub/Sub + Streams)**: The realtime service currently runs both the legacy Pub/Sub subscriber and the new Streams consumer simultaneously. This ensures zero-downtime migration. Disable Pub/Sub via `ENABLE_PUBSUB_SUBSCRIBER=false` once all workers are confirmed on Streams.
- **Synchronous wave loop**: The orchestrator calls `execute_wave()` directly (blocking) rather than via `.delay()`. This is intentional — the orchestrator owns the wave loop and enforces inter-wave delays. The `deployment-waves` queue isolation provides timeout protection at the Celery level.
- **Idempotent orchestrator**: `orchestrate_deployment` is safe to retry/re-run. Already-completed waves are skipped. This handles Celery worker restarts gracefully.

### Security Notes

- `agent/config.yaml` is now in `.gitignore` — real API keys must not be committed. Use `config.yaml.example` as the template.
- Agent API key rotation runs daily at 02:30 UTC with a 90-day rotation threshold. Agents receive the new key via the `KEY_ROTATED` WebSocket command before the server invalidates the old one.
- The realtime service authenticates agents directly via asyncpg (bypassing Django ORM) to avoid blocking the event loop.

### Windows Dev Notes

- The `.venv` Scripts path uses backslash on Windows: `.venv\Scripts\activate`
- Celery on Windows requires `--pool=solo` or `--pool=gevent` — see Makefile.
- The agent `_disk_usage()` uses `C:\` on Windows, `/` on Linux/macOS.

### Phase 11 Migration Status

| Task | Status |
|------|--------|
| 11.4 Celery task hierarchy | ✅ Complete |
| 11.5 DeploymentEvent sourcing | ✅ Complete |
| 11.6 Compliance materialized view | ✅ Complete |
| 11.7 Agent API key rotation | ✅ Complete |
| 11.8 Frontend UX (virtual scroll) | ✅ Complete |
| Redis Streams migration | 🔄 In progress (dual-path active) |