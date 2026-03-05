# PatchGuard Enterprise

**PatchGuard** is an enterprise-grade, scalable centralized patch management platform. It orchestrates remote fleet patching across Windows, Linux, and macOS endpoints, tracks real-time deployment telemetry, enforces compliance policies, and provides role-based access control with Active Directory/LDAP integration.

This **monorepo** houses all system components as a single deployable unit: the Django REST core, FastAPI WebSocket layer, Angular SPA, Python hardware agents, and all supporting infrastructure configuration.

---

## 📊 Build Status

| Component | Stack | Status |
|-----------|-------|--------|
| Backend API | Django 6.0 + DRF 3.15 | ✅ Complete |
| Auth System | SimpleJWT 5.3 + LDAP | ✅ Complete |
| Task Engine | Celery 5.4 + Redis 7 | ✅ Complete |
| Real-Time Layer | FastAPI 0.110 + WebSockets | ✅ Complete |
| Frontend Core | Angular 21.2 (Signals) | ✅ Core Done |
| Agent | Python 3.12 | ⚙️ In Progress |
| Test Suite | pytest + Angular Karma | ⬜ Not Started |

**Overall Progress: 27/44 tasks (61%)**

---

## 🏛️ System Architecture

PatchGuard implements a **Tri-Layer Microservices Topology** connected via a Redis-backed Event Bus. The three tiers are fully decoupled: REST operations, WebSocket persistence, and async task execution each run in isolated processes.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL CLIENTS                            │
│                                                                     │
│   ╔══════════════╗    ╔══════════════╗    ╔══════════════════════╗ │
│   ║  Admin UI    ║    ║ Windows Agent║    ║    Linux/macOS Agent ║ │
│   ║ (Browser SPA)║    ║  agent.py    ║    ║      agent.py        ║ │
│   ╚══════╤═══════╝    ╚══════╤═══════╝    ╚══════════╤═══════════╝ │
│          │ HTTPS             │ WSS (443)              │ WSS (443)   │
└──────────┼───────────────────┼────────────────────────┼────────────┘
           │                   │                        │
           ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NGINX REVERSE PROXY (:443)                     │
│   /api/*  ──────────────────────────────────────► Django (:8000)    │
│   /ws/*   ──────────────────────────────────────► FastAPI (:8001)   │
│   /*      ──────────────────────────────────────► Angular Static    │
└───────────────┬─────────────────────┬───────────────────────────────┘
                │                     │
                ▼                     ▼
┌───────────────────────┐   ┌─────────────────────────────────────────┐
│   DJANGO (WSGI)       │   │           FASTAPI (ASGI)                │
│   Core REST API       │   │         Real-Time Service               │
│                       │   │                                         │
│  • JWT Auth + LDAP    │   │  • WebSocket pool management            │
│  • RBAC Permissions   │   │  • Agent command dispatch               │
│  • Patch state machine│   │  • Redis Pub/Sub subscriber             │
│  • Deployment wizard  │   │  • Dashboard event fan-out              │
│  • OpenAPI/Swagger    │   │  • JWT verification (shared secret)     │
└──────────┬────────────┘   └──────────────────┬──────────────────────┘
           │                                    │
           │  Write/Read                        │  Subscribe
           ▼                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                         DATA TIER                                 │
│                                                                   │
│  ╔══════════════════╗          ╔═════════════════════════════╗    │
│  ║  PostgreSQL 16   ║          ║       Redis 7               ║    │
│  ║                  ║          ║                             ║    │
│  ║ • accounts       ║          ║ Pub/Sub Channels:           ║    │
│  ║ • inventory      ║          ║  deployment:<id>            ║    │
│  ║ • patches        ║  ◄────   ║  device:status              ║    │
│  ║ • deployments    ║  Write   ║  notifications              ║    │
│  ║ • audit_log      ║          ║  compliance:alert           ║    │
│  ║ (partitioned)    ║          ║                             ║    │
│  ╚══════════════════╝          ║ Task Queues:                ║    │
│                                ║  critical / default /       ║    │
│                                ║  reporting                  ║    │
│                                ╚══════════════╤══════════════╝    │
└───────────────────────────────────────────────┼───────────────────┘
                                                │ Poll
                                                ▼
                               ┌─────────────────────────────┐
                               │     CELERY WORKERS          │
                               │                             │
                               │  Beat Schedule (cron):      │
                               │  • Vendor patch sync (6h)   │
                               │  • Stale device check (5m)  │
                               │  • Compliance snapshot (1d) │
                               │  • Scheduled deployments(1m)│
                               │  • Partition cleanup (1mo)  │
                               │                             │
                               │  Task Queues:               │
                               │  • execute_deployment       │
                               │  • cancel_deployment_task   │
                               │  • process_scheduled_       │
                               │    deployments              │
                               └─────────────────────────────┘
```

### Mermaid Diagram

```mermaid
graph TD
    Admin([Administrator Browser]) -->|HTTPS /api + /ws| Nginx
    AgentW[Windows Agent] -->|WSS /ws/agents| Nginx
    AgentL[Linux / macOS Agent] -->|WSS /ws/agents| Nginx

    subgraph Proxy["Nginx Reverse Proxy :443"]
        Nginx{nginx.conf}
    end

    Nginx -->|/api/*| Django["Django 6 WSGI :8000\nREST API · Auth · RBAC"]
    Nginx -->|/ws/*| FastAPI["FastAPI ASGI :8001\nWebSocket Pool · Pub/Sub"]
    Nginx -->|/* SPA| Angular["Angular 21 SPA\nAdmin Dashboard"]

    subgraph DataTier["Data Tier"]
        Postgres[(PostgreSQL 16\naccounts · inventory\npatches · deployments)]
        Redis[(Redis 7\nPub/Sub + Task Queues)]
    end

    Django -->|ORM writes| Postgres
    Django -->|Enqueue tasks / publish| Redis
    FastAPI -.->|Subscribe channels| Redis
    FastAPI -.->|Agent API key lookup| Postgres

    subgraph Workers["Celery Workers"]
        Beat[Celery Beat\nCron Scheduler]
        Worker[Celery Worker\ncritical · default · reporting]
    end

    Beat -->|Trigger| Worker
    Worker -.->|Poll| Redis
    Worker -->|Bulk writes| Postgres
    Worker -.->|Publish progress| Redis
```

---

## 🔑 Core Design Decisions

### 1. Django WSGI — Source of Truth
The Django monolith owns all persistent state. It handles REST authentication, the patch lifecycle state machine, RBAC enforcement, and deployment orchestration.
- **Patch State Machine** (`patches/state_machine.py`): enforces transitions `imported → approved → superseded`, blocking installation of unapproved patches.
- **Deployment Waves** (`deployments/tasks.py`): Celery chunks device groups into canary/rolling waves, respecting `max_failure_percentage` thresholds before advancing.
- **Audit Log** (`accounts/models.py`): Every API write is logged to a time-partitioned `audit_log` table, maintained by a monthly Celery Beat job.

### 2. FastAPI ASGI — Real-Time Edge Layer
A stateless, ultra-lightweight microservice that never touches the database for hot paths. Its only persistent state lives in an in-memory `ConnectionManager`.
- Validates incoming WebSocket connections using the same JWT secret as Django.
- Subscribes to Redis channels (`deployment:<id>`, `device:status`, `notifications`) and fans out events to connected dashboard clients and field agents.
- Field agents authenticate with a unique `agent_api_key` (looked up once at connect-time from PostgreSQL).

### 3. Angular 21 SPA — Reactive Dashboard
Built with standalone components and Angular Signals for fine-grained reactivity without Zone.js overhead.
- Auth interceptor attaches Bearer tokens to all API requests.
- `WebSocketService` maintains a single socket to `/ws/dashboard` and broadcasts events through an `Observable` stream.
- Role-based route guards (`authGuard`, `roleGuard`) enforce access at the URL level.

---

## ⚙️ Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend | Python | 3.12+ | Runtime |
| Backend | Django | 6.0.3 | ORM, REST, Auth |
| Backend | Django REST Framework | 3.15.2 | API serialization + ViewSets |
| Backend | SimpleJWT | 5.3.1 | JWT access/refresh tokens |
| Backend | drf-spectacular | 0.27.2 | OpenAPI 3.1 schema + Swagger UI |
| Backend | Celery | 5.4.0 | Distributed task queue |
| Backend | django-celery-beat | 2.7.0 | Persistent cron schedules |
| Real-Time | FastAPI | 0.110.0 | ASGI WebSocket server |
| Real-Time | Uvicorn | 0.29.0 | ASGI runner |
| Real-Time | Websockets | 12.0 | WS protocol |
| Real-Time | asyncpg | 0.29.0 | Async PostgreSQL driver |
| Frontend | Angular | 21.2.0 | SPA framework (Signals + Standalone) |
| Frontend | RxJS | 7.8 | Reactive streams |
| Frontend | TypeScript | 5.9 | Typed JavaScript |
| Database | PostgreSQL | 16-alpine | Primary datastore (partitioned audit log) |
| Cache/Queue | Redis | 7-alpine | Pub/Sub + Celery broker/result backend |
| Proxy | Nginx | alpine | TLS termination + routing |
| Container | Docker + Compose | latest | Dev and production orchestration |

---

## 📂 Monorepo Structure

```text
PatchGaurd/
│
├── agent/                          # Python endpoint agent (Windows / Linux / macOS)
│   ├── agent.py                    # Main agent loop: heartbeat, scan, patch execution
│   ├── config.yaml                 # Agent configuration (server URL, API key, interval)
│   ├── requirements.txt            # Agent-specific dependencies
│   └── plugins/
│       ├── windows.py              # Windows Update API integration
│       ├── linux.py                # apt/yum patch execution
│       └── macos.py                # softwareupdate integration
│
├── backend/                        # Core Django WSGI service
│   ├── manage.py
│   ├── Dockerfile
│   ├── apps/
│   │   ├── accounts/               # Users, roles, JWT auth, LDAP backend, audit log
│   │   ├── inventory/              # Devices, DeviceGroups, heartbeat, stale detection
│   │   ├── patches/                # Patch catalog, state machine, DevicePatchStatus
│   │   └── deployments/            # Deployment lifecycle, waves, targets, Celery tasks
│   ├── common/
│   │   ├── middleware.py           # AuditLog + RequestTiming middleware
│   │   ├── exceptions.py           # Custom DRF exception handler
│   │   ├── pagination.py           # Cursor + page-number pagination
│   │   ├── db_router.py            # Primary/replica DB routing
│   │   ├── redis_cache.py          # DashboardCache singleton
│   │   └── redis_pubsub.py         # RedisPublisher (deployment, device, compliance)
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py             # Shared settings (INSTALLED_APPS, JWT, Celery, Spectacular)
│   │   │   ├── dev.py              # Debug=True, CORS all, SQLite fallback
│   │   │   └── prod.py             # HTTPS, HSTS, Sentry, secure cookies
│   │   ├── celery_app.py           # Celery app + Beat schedule (5 recurring tasks)
│   │   ├── urls.py                 # Root URL conf
│   │   └── wsgi.py
│   └── requirements/
│       ├── base.txt                # Production dependencies (pinned)
│       ├── dev.txt                 # + debug toolbar, factory-boy
│       └── prod.txt                # + gunicorn, sentry
│
├── frontend/                       # Angular 21 SPA
│   ├── src/app/
│   │   ├── core/
│   │   │   ├── auth/               # AuthService, AuthGuard, AuthInterceptor
│   │   │   ├── models/             # TypeScript interfaces (Device, Patch, Deployment…)
│   │   │   └── services/           # ApiService, DeviceService, PatchService, DeploymentService,
│   │   │                           # WebSocketService, ReportService, UserService
│   │   └── features/
│   │       └── auth/login/         # Login page component (✅ complete)
│   ├── proxy.conf.json             # Dev proxy: /api → :8000, /ws → :8001
│   ├── Dockerfile
│   └── package.json
│
├── realtime/                       # FastAPI ASGI WebSocket service
│   ├── main.py                     # App factory, lifespan (Redis sub loop)
│   ├── auth.py                     # JWT + agent API key verification
│   ├── ws_manager.py               # ConnectionManager (dashboard + agent pools)
│   ├── agent_protocol.py           # Pydantic message schemas
│   ├── Dockerfile
│   ├── requirements.txt
│   └── routes/
│       ├── agents.py               # WS endpoint for field agents
│       ├── events.py               # WS endpoint for dashboard clients
│       └── health.py               # /health REST endpoint
│
├── nginx/
│   ├── nginx.conf                  # Virtual host: TLS termination, upstream routing
│   └── ssl/                        # TLS certificates (generated by scripts/generate-certs.sh)
│
├── scripts/
│   ├── init-db.sh                  # One-shot DB init (create roles, run migrations)
│   ├── seed-data.py                # Populate dev data (users, devices, patches)
│   └── generate-certs.sh           # Self-signed cert generation for local HTTPS
│
├── tasks/                          # Markdown task specifications (phases 01–10)
│
├── docker-compose.yml              # Dev stack: postgres, redis, backend, realtime, frontend, workers
├── docker-compose.prod.yml         # Prod stack: + nginx, pgbouncer, resource limits, non-root
├── Makefile                        # Convenience commands (see below)
├── TASK_TRACKER.md                 # Progress roadmap (27/44 complete)
└── README.md
```

---

## 🚀 Quick Start (Development)

### Prerequisites
- Docker Desktop 4.x+
- Node.js 20.x (for local Angular dev)
- Python 3.12+ (for local Django dev)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD
```

### 2. Start All Services

```bash
make up
# Equivalent to: docker compose up --build -d
```

Services started:
| Service | URL |
|---------|-----|
| Angular UI | http://localhost:4200 |
| Django API | http://localhost:8000/api/v1/ |
| Swagger UI | http://localhost:8000/api/schema/swagger-ui/ |
| FastAPI Docs | http://localhost:8001/docs |
| Celery Flower | http://localhost:5555 |

### 3. Initialize Database

```bash
make migrate      # Run Django migrations
make seed         # Load development seed data (users, devices, patches)
```

### 4. Create Superuser

```bash
make superuser
```

---

## 🔧 Makefile Commands

```bash
make up           # Start all Docker services
make down         # Stop all Docker services
make build        # Rebuild images
make logs         # Tail all service logs
make migrate      # Run Django migrations
make seed         # Run seed-data.py
make superuser    # Create Django superuser
make test         # Run backend test suite
make lint         # Run ruff + eslint
make shell        # Open Django shell
make psql         # Open PostgreSQL CLI
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | Obtain JWT access + refresh tokens |
| `POST` | `/api/auth/refresh/` | Rotate refresh token |
| `POST` | `/api/auth/logout/` | Blacklist refresh token |
| `GET` | `/api/v1/devices/` | List all devices (filterable) |
| `GET` | `/api/v1/devices/{id}/` | Device detail |
| `POST` | `/api/v1/devices/{id}/scan/` | Trigger remote patch scan |
| `GET` | `/api/v1/patches/` | Patch catalog (filterable by severity, OS) |
| `POST` | `/api/v1/patches/{id}/approve/` | Approve patch for deployment |
| `GET` | `/api/v1/deployments/` | List deployments |
| `POST` | `/api/v1/deployments/` | Create deployment |
| `POST` | `/api/v1/deployments/{id}/approve/` | Approve draft deployment |
| `POST` | `/api/v1/deployments/{id}/execute/` | Execute deployment immediately |
| `POST` | `/api/v1/deployments/{id}/pause/` | Pause in-progress deployment |
| `POST` | `/api/v1/deployments/{id}/resume/` | Resume paused deployment |
| `POST` | `/api/v1/deployments/{id}/cancel/` | Cancel deployment |
| `POST` | `/api/v1/deployments/{id}/rollback/` | Initiate rollback |
| `GET` | `/api/v1/deployments/{id}/targets/` | Per-device deployment status |
| `GET` | `/api/v1/reports/dashboard/` | Dashboard KPI stats |
| `GET` | `/api/v1/reports/compliance/` | Compliance report |
| `GET` | `/api/schema/swagger-ui/` | Interactive Swagger UI |
| `WS` | `/ws/dashboard` | Real-time dashboard events (JWT auth) |
| `WS` | `/ws/agents/{agent_id}` | Agent command channel (API key auth) |

---

## 🔐 Authentication & RBAC

PatchGuard uses short-lived JWT access tokens (30 min default) with rotating refresh tokens (7 days). Tokens include custom claims: `role`, `username`, `email`.

| Role | Permissions |
|------|-------------|
| `admin` | Full access including user management and system settings |
| `operator` | Can create, approve, and execute deployments; manage patches |
| `viewer` | Read-only access to all resources |
| `agent` | Service account for field agents (API key, no human login) |

LDAP/Active Directory authentication is available via `django-python3-ldap`. Configure `LDAP_*` environment variables in `.env`.

---

## 🗄️ Data Model Overview

```
┌──────────┐     ┌─────────────┐     ┌────────────────────┐
│   User   │     │    Device   │     │       Patch        │
│ (accounts│     │ (inventory) │     │    (patches)       │
│  app)    │     │             │     │                    │
│ role     │     │ hostname    │     │ cve_ids            │
│ locked_  │     │ os_family   │     │ severity           │
│ until    │     │ ip_address  │     │ status (state      │
│ last_    │     │ status      │     │  machine)          │
│ login    │     │ agent_api_  │     │                    │
└──────────┘     │ key         │     └────────┬───────────┘
                 └──────┬──────┘              │
                        │                     │
                        ▼                     ▼
               ┌────────────────────────────────────┐
               │         DevicePatchStatus           │
               │           (patches app)             │
               │                                     │
               │  device → Device                    │
               │  patch  → Patch                     │
               │  state  (pending/installed/failed)  │
               └────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     Deployment                          │
│                  (deployments app)                      │
│                                                         │
│  patches      → ManyToMany(Patch)                       │
│  target_groups→ ManyToMany(DeviceGroup)                 │
│  strategy     → immediate / canary / rolling            │
│  status       → draft → scheduled → in_progress →      │
│                 paused → completed / failed             │
│  created_by   → User                                    │
│  approved_by  → User                                    │
└─────────────────────────────────────────────────────────┘
              │
              ▼ (one per device, one per wave)
┌─────────────────────────────────────────────────────────┐
│                  DeploymentTarget                       │
│  deployment   → Deployment                              │
│  device       → Device                                  │
│  wave_number  → int                                     │
│  status       → queued / in_progress / completed /      │
│                 failed / skipped / rolled_back          │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 WebSocket Protocol

### Dashboard Events (client → server)
```json
{ "type": "subscribe", "channel": "deployments" }
```

### Server → Client Messages
```json
{ "type": "deployment_progress", "deployment_id": "...", "status": "in_progress", "progress_percentage": 42 }
{ "type": "device_status", "device_id": "...", "hostname": "web-01", "status": "offline" }
{ "type": "notification", "level": "error", "message": "Deployment halted: failure threshold exceeded" }
{ "type": "compliance_alert", "scope": "global", "rate": 0.73 }
```

### Agent Commands (server → agent)
```json
{ "command": "START_DEPLOYMENT", "deployment_id": "...", "target_id": "..." }
{ "command": "CANCEL_DEPLOYMENT", "deployment_id": "..." }
{ "command": "FULL_SCAN" }
```

---

## 📈 Progress

| Phase | Description | Tasks | Status |
|-------|-------------|-------|--------|
| 1 | Scaffolding & Infrastructure | 6/6 | ✅ Complete |
| 2 | Django Models & Migrations | 5/5 | ✅ Complete |
| 3 | Authentication & Authorization | 3/3 | ✅ Complete |
| 4 | Django REST API | 4/4 | ✅ Complete |
| 5 | Celery Task Engine | 3/3 | ✅ Complete |
| 6 | FastAPI Real-Time Service | 3/3 | ✅ Complete |
| 7 | Angular Frontend | 3/12 | ⚙️ In Progress |
| 8 | Python Agent | 0/1 | ⬜ Not Started |
| 9 | Testing & Quality | 0/3 | ⬜ Not Started |
| 10 | Production Hardening | 0/4 | ⬜ Not Started |
| **Total** | | **27/44** | **61%** |
#   P a t c h G a u r d  
 