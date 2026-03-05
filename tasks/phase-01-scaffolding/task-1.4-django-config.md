# Task 1.4 — Django Project Configuration

**Time**: 3 hours  
**Dependencies**: 1.1  
**Status**: ✅ Done  
**Files**: All files under `backend/config/`

---

## AI Prompt

```
Implement the complete Django 6.0 project configuration for PatchGuard.

config/settings/base.py should include:

INSTALLED_APPS:
- All default Django apps
- rest_framework, rest_framework_simplejwt, rest_framework_simplejwt.token_blacklist
- django_filters, corsheaders, django_celery_beat, django_celery_results
- drf_spectacular (for Swagger/OpenAPI 3.1)
- health_check, health_check.db, health_check.cache, health_check.contrib.celery, health_check.contrib.redis
- All 4 local apps: apps.accounts, apps.inventory, apps.patches, apps.deployments

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE: security, whitenoise, cors, session, common, csrf, auth, messages, clickjacking, custom AuditLogMiddleware, custom RequestTimingMiddleware

DATABASE config:
- Default pointing to pgbouncer (port 6432 in prod, 5432 in dev)
- CONN_MAX_AGE=0 (pgbouncer handles pooling)
- Optional "readonly" database if POSTGRES_READ_HOST env var set
- DATABASE_ROUTERS pointing to common.db_router.ReadReplicaRouter

CACHE config using django-redis:
- Default cache on REDIS_CACHE_URL (db 1)
- Connection pool max 50, socket timeout 5s, retry on timeout
- KEY_PREFIX "pm", TIMEOUT 300

REST_FRAMEWORK config:
- JWT authentication only
- IsAuthenticated default permission
- CursorPagination (from common.pagination) with page_size 50
- django_filters, SearchFilter, OrderingFilter backends
- Throttle rates: anon 20/min, user 200/min
- drf_spectacular AutoSchema
- Custom exception handler from common.exceptions
- JSONRenderer only

SIMPLE_JWT config:
- Access token lifetime from env (default 30 min)
- Refresh token lifetime from env (default 7 days)
- Rotate and blacklist refresh tokens
- Signing key from JWT_SECRET_KEY env var
- Custom TokenObtainSerializer from accounts app
- user_id field is "id", claim is "user_id"

SPECTACULAR_SETTINGS:
- Title: "Patch Management API"
- Version: "1.0.0"
- Tags for: Auth, Users, Devices, Patches, Deployments, Reports, Health
- Bearer JWT security scheme
- COMPONENT_SPLIT_REQUEST: True

CELERY config:
- Broker from CELERY_BROKER_URL env (redis db 0)
- Result backend: django-db
- JSON serialization only
- UTC timezone
- Task tracking, 1h hard limit, 55min soft limit
- acks_late, reject_on_worker_lost
- Prefetch multiplier 1
- Three queues: critical, default, reporting

Structured logging with structlog:
- JSON format in production, console in dev
- RotatingFileHandler to /var/log/patchmgr/django.log (50MB, 10 backups)
- Suppress django.db.backends below WARNING

config/settings/dev.py:
- DEBUG = True
- ALLOWED_HOSTS = ["*"]
- CORS_ALLOW_ALL_ORIGINS = True
- Console-only logging

config/settings/prod.py:
- DEBUG = False
- ALLOWED_HOSTS and CORS from env vars
- SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, etc.
- Session cookie secure, httponly, samesite=Lax

config/celery_app.py:
- Celery app with autodiscover
- Beat schedule:
  - sync-patch-catalog: every 6 hours (default queue)
  - device-stale-check: every 5 minutes (default queue)
  - compliance-snapshot: daily at 01:00 UTC (reporting queue)
  - run-scheduled-deployments: every 1 minute (critical queue)
  - cleanup-old-partitions: monthly 1st at 03:00 (reporting queue)

config/urls.py:
- admin/ → Django admin
- api/v1/auth/ → accounts.urls
- api/v1/users/ → accounts.urls_users
- api/v1/devices/ → inventory.urls
- api/v1/patches/ → patches.urls
- api/v1/deployments/ → deployments.urls
- api/v1/reports/ → reporting URLs
- api/schema/ → SpectacularAPIView
- api/docs/ → SpectacularSwaggerView
- api/redoc/ → SpectacularRedocView
- api/health/ → health_check.urls

config/wsgi.py: Standard WSGI config

requirements/base.txt: All packages with pinned versions (Django==6.0.3, djangorestframework==3.15.2, djangorestframework-simplejwt==5.3.1, django-filter==24.3, django-cors-headers==4.4.0, django-celery-beat==2.7.0, django-celery-results==2.5.1, drf-spectacular==0.27.2, psycopg[binary]==3.2.3, redis==5.1.1, celery==5.4.0, gunicorn==23.0.0, django-redis==5.4.0, django-health-check==3.18.3, python-ldap==3.4.4, whitenoise==6.7.0, sentry-sdk==2.16.0, structlog==24.4.0)

requirements/dev.txt: -r base.txt + pytest, pytest-django, pytest-cov, factory-boy, faker, watchfiles, django-debug-toolbar, ipdb

requirements/prod.txt: -r base.txt + uvloop, httptools
```

---

## Acceptance Criteria

- [x] `python manage.py check` passes
- [x] `python manage.py migrate` runs (after models are created)
- [x] Swagger UI loads at /api/docs/
- [x] Health check endpoint responds
- [x] Celery worker connects to Redis broker
- [x] Settings correctly switch between dev and prod

## Files Created/Modified

- [ ] `backend/config/settings/base.py`
- [ ] `backend/config/settings/dev.py`
- [ ] `backend/config/settings/prod.py`
- [ ] `backend/config/celery_app.py`
- [ ] `backend/config/urls.py`
- [ ] `backend/config/wsgi.py`
- [ ] `backend/requirements/base.txt`
- [ ] `backend/requirements/dev.txt`
- [ ] `backend/requirements/prod.txt`

## Completion Log

## Completion Log

2026-04-04: Completed full Django configuration. Integrated JWT, Celery, Redis, and Health Checks. Verified with `manage.py check`. Switched ArrayField to JSONField for cross-DB compatibility.
