DEVELOPER GUIDE
===============

Purpose
-------
This document contains concise, actionable instructions for developers who want to run, debug, extend, and contribute to PatchGuard locally (Windows) or using Docker.

Quick reference
---------------
- Repo root: `d:\PatchGaurd`
- Backend (Django): `backend/` — port 8000
- Real-time (FastAPI): `realtime/` — port 8001
- Frontend (Angular): `frontend/` — port 4200
- Agent: `agent/`

Prerequisites
-------------
- Windows 10/11 or Linux/macOS
- Python 3.12+ (prefer a venv)
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Git
- Docker (optional for containerized dev)

Environment (important variables)
---------------------------------
Copy `.env.example` to `.env` and set: `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`, `JWT_SECRET_KEY`. Example minimal vars:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=REPLACE_ME
POSTGRES_DB=vector_db
REDIS_URL=redis://localhost:6379/0
DJANGO_SETTINGS_MODULE=config.settings.dev
BACKEND_URL=http://localhost:8000/api/v1
```

Local dev (native, Windows) — recommended for iterative development
------------------------------------------------------------------
Open PowerShell and run:

```powershell
# clone + venv
git clone <repo> D:\PatchGuard
cd D:\PatchGuard
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install python deps (single venv for backend/realtime/agent)
pip install -r backend/requirements/dev.txt
pip install -r realtime/requirements.txt
pip install -r agent/requirements.txt

# frontend deps
cd frontend
npm install
cd ..
```

Initialize DB and seed data:

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
.\.venv\Scripts\python.exe manage.py migrate

# seed data (runs from repo root, uses backend on PYTHONPATH)
cd ..
$env:PYTHONPATH="$PWD\backend"
.\.venv\Scripts\python.exe scripts/seed-data.py
```

Start services (open separate terminals):

```powershell
# Terminal 1 — Django API
cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

# Terminal 2 — FastAPI (Realtime)
cd realtime
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# Terminal 3 — Celery worker (Windows: use solo pool)
cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
.\.venv\Scripts\python.exe celery_worker.py -A config.celery_app worker --loglevel=info -Q critical,default,reporting --concurrency=4 --pool=solo

# Terminal 4 — Angular frontend (proxy configured)
cd frontend
npx ng serve --proxy-config proxy.conf.json --host 127.0.0.1 --port 4200

# Terminal 5 — Agent (optional)
cd agent
.\.venv\Scripts\python.exe agent.py
```

Notes & gotchas
---------------
- Celery on Windows requires `--pool=solo`.
- `frontend/proxy.conf.json` proxies `/api -> 127.0.0.1:8000` and `/ws -> ws://127.0.0.1:8001`.
- `backend/manage.py` contains a thread-safe signal fix — auto-reload is safe in dev (we removed the previous `--noreload` workaround).
- If the agent can't connect, verify `agent/config.yaml` `server_url` and `api_key` match device records in the DB.

VS Code workflows
-----------------
Open the workspace in VS Code and use `.vscode/launch.json` compounds:
- **Full Stack + Frontend** — starts Django, FastAPI, Celery Worker, and Angular.
- **Everything** — starts Full Stack + Celery Beat + Agent.

Running tests & lint
--------------------
- Backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

- Frontend tests:

```bash
cd frontend
npx ng test --watch=false
```

- Linting:
  - Python: `ruff check backend/ realtime/ agent/` (or `ruff check .`)
  - Frontend: `npm run lint` (uses eslint)

Adding a new backend app (quick checklist)
-----------------------------------------
1. `cd backend`
2. `.\.venv\Scripts\python.exe manage.py startapp myapp`
3. Add `myapp` to `config/settings/base.py` INSTALLED_APPS
4. Create models, register in admin, write serializers and viewsets
5. Add routes in `backend/config/urls.py` (include pattern under `/api/v1/`)
6. Create migrations: `manage.py makemigrations myapp` and `manage.py migrate`
7. Add tests under `backend/apps/myapp/tests/` and run pytest

Adding a new frontend feature
-----------------------------
- Use Angular standalone components and the existing `ApiService` patterns.
- If you need real-time events, subscribe to `WebSocketService` and emit/consume typed events.
- Follow existing code style (Signals, minimal global state). Use `npx ng g component <name>` or create files under `src/app/features/`.

Celery & tasks
---------------
- Celery app is configured at `backend/config/celery_app.py` and imported in `backend/config/__init__.py`.
- Use `@shared_task` or `@app.task` with `config.celery_app` as needed.
- Publish progress via Redis channels: `deployment:progress`, `agent:command:{device_id}`.

Debugging tips
--------------
- Inspect Django logs stdout where `manage.py` runs.
- FastAPI logs are printed by Uvicorn (use `--reload` for code changes).
- Celery worker logs show task failures — check traceback; use `--loglevel=debug` as needed.
- To inspect Redis pub/sub messages quickly, use `redis-cli subscribe <channel>`.

Docker (dev & prod)
-------------------
- Dev: `docker compose up --build -d` from repo root. Use `docker compose exec django python manage.py migrate` to run migrations inside container.
- Prod: `docker compose -f docker-compose.prod.yml up -d` — production files include nginx and pgbouncer and expect environment variables for secrets.

Contributing
------------
- Branch naming: `feature/<short-desc>`, `fix/<short-desc>`, `hotfix/<short-desc>`
- Create PRs against `main` (or workflow branch used by your org).
- Include unit tests and update `TASK_TRACKER.md` for task progress.

Where to look first (important files)
-------------------------------------
- `backend/config/settings/` — Django settings
- `backend/config/urls.py` — API entry points
- `realtime/main.py` and `realtime/routes/` — WebSocket endpoints
- `backend/apps/deployments/` — deployment orchestration and Celery tasks
- `agent/agent.py` and `agent/config.yaml` — agent behavior & configuration
- `frontend/src/app/core/services/websocket.service.ts` — client real-time integration

Next steps (for maintainers)
---------------------------
- Add CI jobs for backend tests and frontend build.
- Add integration tests for WebSocket flows.
- Add a PR template and CODEOWNERS if needed.

---

File created: `DEVELOPER.md` (repo root)
