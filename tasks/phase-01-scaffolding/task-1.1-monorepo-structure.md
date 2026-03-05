# Task 1.1 — Initialize Monorepo Structure

**Time**: 1 hour  
**Dependencies**: None  
**Status**: ✅ Completed  
**Files**: Project root, all directory scaffolding

---

## AI Prompt

```
Create a monorepo project structure for a patch management tool called "PatchGuard" with the following layout:

Root:
- docker-compose.yml (development)
- docker-compose.prod.yml (production)
- .env.example with all required environment variables
- .gitignore for Python, Node, Docker, IDE files
- README.md with project overview and quick start

Directories:
1. backend/ — Django 6.0 project named "config" with apps directory at backend/apps/
   - Apps: accounts, inventory, patches, deployments
   - Each app has: models.py, serializers.py, views.py, urls.py, admin.py, tests/ directory
   - Common utilities at backend/common/ (middleware.py, pagination.py, exceptions.py, utils.py, db_router.py)
   - Requirements split: requirements/base.txt, requirements/dev.txt, requirements/prod.txt
   - Settings split: config/settings/base.py, config/settings/dev.py, config/settings/prod.py
   - Celery config at config/celery_app.py

2. realtime/ — FastAPI project
   - main.py, auth.py, ws_manager.py, agent_protocol.py
   - routes/ directory with agents.py, events.py, health.py
   - requirements.txt, Dockerfile, tests/ directory

3. frontend/ — Angular 20+ project (standalone components, signals)
   - Core module: auth/, interceptors/, guards/, services/, models/
   - Feature modules: dashboard/, devices/, patches/, deployments/, settings/
   - Shared module: components/, pipes/, directives/

4. agent/ — Python agent with agent.py, config.yaml, plugins/ (linux.py, windows.py, macos.py)

5. nginx/ — nginx.conf for production, ssl/ directory

6. scripts/ — init-db.sh, seed-data.py, generate-certs.sh

Generate only the directory structure and placeholder files with TODO comments. Do NOT implement any logic yet. Include proper __init__.py files for all Python packages.
```

---

## Acceptance Criteria

- [x] All directories and placeholder files exist (84/84 verified)
- [x] `python manage.py check` runs without import errors (after Django install)
- [x] `.gitignore` covers all relevant patterns (Python, Node, Docker, IDE, OS)
- [x] `.env.example` contains all variables from our architecture doc

## Files Created/Modified

- [x] `docker-compose.yml`
- [x] `docker-compose.prod.yml`
- [x] `.env.example`
- [x] `.gitignore`
- [x] `README.md`
- [x] `backend/` — full directory tree
- [x] `realtime/` — full directory tree
- [x] `frontend/` — full directory tree
- [x] `agent/` — full directory tree
- [x] `nginx/` — full directory tree
- [x] `scripts/` — full directory tree

## Completion Log

**Completed**: 2026-04-04

**Notes**:
- 84 files created, 14 directories verified — all present
- All placeholder files contain TODO comments referencing their implementation task
- Django apps: accounts, inventory, patches, deployments (each with models, serializers, views, urls, admin, tests/)
- Extra app-specific files: permissions.py, ldap_backend.py, filters.py, state_machine.py, tasks.py
- Frontend Angular structure: core (auth, interceptors, guards, services, models), features (dashboard, devices, patches, deployments, settings), shared (components, pipes, directives)
- Agent: agent.py, config.yaml, plugins (linux, windows, macos)
- No logic implemented — all files are placeholders per task requirement
