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
8. [Device Details Module — Enterprise Redesign](#device-details-module--enterprise-redesign)
9. [Known Issues & Assumptions](#known-issues--assumptions)

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
| Per-patch install | Dashboard → Django REST `POST /devices/{id}/install_patch/` → Redis `agent:command:{id}` → Realtime → Agent `EXECUTE_PATCH` → Agent emits `patch_install_start` / `patch_install_result` → Realtime → Dashboard WS + Django persist |
| Lane config push | Dashboard → Django REST `POST /devices/{id}/lane_config/` → Redis `CONFIG_UPDATE` → Agent updates LaneScheduler intervals/concurrency |
| Device timeline | Django REST `GET /devices/{id}/timeline/` → Structured `DeviceEvent` audit trail with type/severity/lane filtering |

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
| `ws_manager.py` | `ConnectionManager`: dashboard WS map, agent WS map, deployment subscriptions, device subscriptions |
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
| `EXECUTE_PATCH` | Server → Agent | `run_patch(patch_id, lane, initiated_by)` — per-patch install via Fast/Slow lane |
| `HEALTH_CHECK` | Server → Agent | `run_health_check()` |
| `KEY_ROTATED` | Server → Agent | Updates `config.yaml`, reconnects |
| `CONFIG_UPDATE` | Server → Agent | Updates live config + lane scheduler intervals/concurrency |
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
| GET | `/devices/{id}/timeline/` | Structured event timeline (filterable by type/severity/since) |
| POST | `/devices/{id}/install_patch/` | Per-patch install via Fast/Slow lane |
| POST | `/devices/{id}/lane_config/` | Push lane configuration to agent |
| GET | `/devices/{id}/alert_summary/` | Alert summary (critical/high missing, failed, pending_reboot) |
| GET | `/devices/{id}/agent_health/` | Agent status, heartbeat stats, version, lane config |
| POST | `/devices/{id}/decommission/` | Soft-decommission device (admin only) |
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

## Device Details Module — Enterprise Redesign

This section defines the production-ready device detail architecture for large fleets (10K–100K devices), aligned with agent lanes, patch lifecycle, and real-time operations.

### Information Architecture (Target)

1. **Overview**
  - Device identity, status, environment, compliance gauge
  - Critical alert banner (failed patches, pending reboot, critical missing)
  - Fast-lane live metrics (CPU/RAM/Disk/Network/processes)
2. **Patch Lifecycle**
  - Subviews: Available, Installed, Failed, Pending Reboot, Recent
  - CVE, severity, CVSS, reboot-required, lane used, duration, retry count
  - Immediate actions: **Run Now (Fast Lane)** and **Schedule (Slow Lane)**
3. **Deployments**
  - Deployment targets, per-device outcomes, wave info, timestamps
4. **Execution Timeline**
  - Structured `DeviceEvent` stream with filters: event type, severity, lane, time range
  - Failure reasons, retry attempts, operator/source attribution
5. **Security & Inventory (Slow Lane)**
  - OS-specific deep inventory and security posture
  - Lazy-loaded sections with truncation for very large datasets
6. **Agent & Settings**
  - Agent health, last heartbeat age, version
  - Lane config (interval, concurrency, rate limit, retry strategy, bandwidth)
  - Key rotation/config changes audit visibility
  - Danger zone: decommission vs hard delete

### Component Layout (Suggested)

- `device-full-detail-shell`
  - `device-hero-card`
  - `device-alert-banner`
  - `device-tabs-nav`
  - Tab components:
   - `device-overview-tab`
   - `device-patch-lifecycle-tab`
   - `device-deployments-tab`
   - `device-timeline-tab`
   - `device-inventory-tab`
   - `device-agent-settings-tab`

> Current implementation keeps a monolithic component for speed of delivery. For long-term maintainability, split into the tab components above and isolate service calls per tab.

### Data Model Alignment

Implemented model enhancements:
- `DeviceEvent` (append-only timeline)
- `DevicePatchStatus.state` includes `pending_reboot`
- `DevicePatchStatus.execution_lane` and `execution_duration_ms`
- `Device.lane_config` JSON for per-device lane behavior

Recommended next fields:
- `DevicePatchStatus.last_error_code`
- `DevicePatchStatus.last_error_category` (network, dependency, permission, timeout)
- `DeviceEvent.correlation_id` (link UI action → backend command → agent result)

### WebSocket Event Design

Dashboard receives:
- `agent_heartbeat`, `agent_metrics`, `agent_slow_lane_data`
- `patch_install_start`, `patch_install_result`, `reboot_complete`
- `scan_results`, `patch_result`, `agent_online`, `agent_offline`

Control messages (dashboard → realtime):
- `subscribe_device` / `unsubscribe_device`
- `subscribe_deployment` / `unsubscribe_deployment`

Design rules:
- Prefer event-driven updates over polling
- Include `device_id`, `event_id`, `occurred_at`, and optional `lane`
- Keep payloads compact for high-fanout scenarios

### Fast Lane / Slow Lane Execution UX

**Fast Lane** (urgent):
- Low latency actions (Run Now)
- Strict operator feedback loop with immediate status transitions

**Slow Lane** (batched):
- Scheduled/batched execution
- Throughput controls and reduced endpoint impact

Both lanes should expose:
- Concurrency
- Rate limits
- Retry strategy
- Bandwidth control
- Queue state (`running`, `queued`, `failed`)

### Performance & Scale Strategy (10K+ Devices)

- Use paginated endpoints by default for patches, events, deployments
- Lazy-load heavy tabs (timeline, inventory, logs)
- Limit initial tab payloads; fetch detail on demand
- Virtualize long lists/tables in frontend
- Use websocket subscriptions scoped by device/deployment
- Avoid global broadcasts for per-device updates where possible

### Current Gaps and Next Hardening Steps

1. **Component decomposition** still pending (single large Angular component)
2. **Queue depth visualization** for fast/slow lanes not yet exposed in UI/API
3. **Timeline streaming mode** (incremental append) should complement paged fetch
4. **Retry analytics** (attempt histograms, MTTR) not yet surfaced
5. **Command correlation IDs** needed for end-to-end traceability

### Security & Audit Expectations

- Keep sensitive actions in dedicated danger zone
- Record who changed lane config or triggered patch runs
- Surface patch approvals and policy context in timeline
- Maintain immutable audit/event records for compliance investigations

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

### Device Details Redesign

The device full-detail view has been redesigned with the following additions:

**Backend (Django)**:
- `DeviceEvent` model — 17 event types, 4 severity levels, append-only audit trail with `record()` factory
- `PENDING_REBOOT` state in `DevicePatchStatus` for tracking post-install reboot requirements
- `ExecutionLane` (fast/slow) and `execution_duration_ms` on `DevicePatchStatus`
- `lane_config` JSONField on `Device` for per-device fast/slow lane configuration
- 6 new API endpoints: `timeline`, `install_patch`, `lane_config`, `alert_summary`, `agent_health`, `decommission`
- DeviceEvent recording in existing endpoints: `scan`, `reboot`, `agent_config`, `rotate_key`

**Agent**:
- Lane-aware `run_patch()`: emits `patch_install_start`/`patch_install_result` events with timing
- `LaneScheduler` accepts `fast_concurrency`/`slow_concurrency` params with per-instance thread pool
- `CONFIG_UPDATE` handler propagates concurrency changes to scheduler

**Realtime (WebSocket)**:
- New event routing: `patch_install_start`, `patch_install_result`, `reboot_complete`
- Device-specific subscriptions (`subscribe_device`/`unsubscribe_device`) for targeted updates
- `broadcast_to_device_subscribers()` for efficient per-device event delivery

**Frontend (Angular)**:
- Alert banner showing critical/high missing, failed, pending_reboot counts
- Per-patch install buttons (Fast ⚡ / Slow 🕐 lane) in available patches table
- Timeline tab replacing Activity Log — structured, filterable event timeline
- Agent Health panel showing status, version, heartbeat age, lane intervals
- Lane Configuration panel for pushing fast/slow lane intervals and concurrency
- Decommission option in danger zone for soft-delete without data loss
- Device-specific WS subscriptions for real-time patch install progress