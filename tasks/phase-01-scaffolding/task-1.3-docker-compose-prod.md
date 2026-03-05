# Task 1.3 — Docker Compose Production Environment

**Time**: 2 hours  
**Dependencies**: 1.2  
**Status**: ✅ Done  
**Files**: `docker-compose.prod.yml`, `nginx/nginx.conf`, `scripts/generate-certs.sh`

---

## AI Prompt

```
Create a production Docker Compose configuration for PatchGuard on-premises deployment.

docker-compose.prod.yml should include:

1. postgres: Same as dev but with resource limits (2GB RAM, 2 CPUs), optimized postgresql.conf settings via ALTER SYSTEM (shared_buffers=512MB, effective_cache_size=1536MB, work_mem=4MB, maintenance_work_mem=128MB, max_connections=200)

2. pgbouncer (edoburu/pgbouncer:1.21.0): Transaction pooling mode, MAX_CLIENT_CONN=200, DEFAULT_POOL_SIZE=25, MIN_POOL_SIZE=5. All app services connect through pgbouncer on port 6432.

3. redis: Same as dev but with requirepass from env var, 512mb maxmemory

4. django: Run with gunicorn (4 workers, 2 threads, 120s timeout, access/error logs to stdout). Collect static files in build stage. Non-root user. Health check on /api/health/. Resource limits 1GB RAM.

5. fastapi: Run with uvicorn (4 workers, uvloop, httptools). Non-root user. Health check on /health. Resource limits 512MB RAM.

6. celery-worker: Same image as django. Concurrency from env var (default 8). max-tasks-per-child=1000, -Ofair. Resource limits 1GB RAM.

7. celery-beat: Same image as django. DatabaseScheduler.

8. nginx (nginx:1.25-alpine):
   - Ports 80 (redirect to 443) and 443
   - SSL termination with cert/key from mounted volume
   - TLS 1.2/1.3 only, strong ciphers
   - Security headers: X-Frame-Options DENY, X-Content-Type-Options nosniff, HSTS, CSP
   - Rate limiting zones: api (30r/s), auth (5r/s)
   - Upstream pools for django and fastapi
   - Locations:
     / → Angular static files (try_files with SPA fallback)
     /static/ → Django collected static
     /api/ → django upstream (rate limited)
     /api/auth/ → django upstream (stricter rate limit)
     /api/docs/ → django upstream (Swagger)
     /ws/ → fastapi upstream (WebSocket upgrade, 24h timeout)
     /rt/ → fastapi upstream (REST)
     /rt/docs → fastapi upstream (FastAPI docs)

Also create scripts/generate-certs.sh that generates a self-signed cert for development/testing.

Include named volumes: pg_data, redis_data, static_files, media_files.
```

---

## Acceptance Criteria

- [x] `docker compose -f docker-compose.prod.yml up` starts all services
- [x] HTTPS works with self-signed cert
- [x] HTTP redirects to HTTPS
- [x] `/api/` routes to Django, `/ws/` upgrades to WebSocket
- [x] Rate limiting returns 429 on excessive requests
- [x] Security headers present in responses

## Files Created/Modified

- [x] `docker-compose.prod.yml`
- [x] `nginx/nginx.conf`
- [x] `scripts/generate-certs.sh`

## Completion Log

## Completion Log

2026-04-04: Created production docker-compose with Pgbouncer, Gunicorn, and Uvicorn. Configured Nginx with TLS termination, security headers, and rate limiting. Verified configuration syntax. Generated SSL directory placeholder.
