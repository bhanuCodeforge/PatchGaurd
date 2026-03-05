# Patch Management Tool — Complete Production Implementation Guide

> **Audience**: Single full-stack developer  
> **Deployment**: On-premises  
> **Stack**: Angular 20+ · Django 6.0 · FastAPI · PostgreSQL 16 · Celery · Redis · WebSockets  
> **Timeline estimate**: 10–14 weeks for MVP

## Table of Contents
1. [Project Structure & Monorepo Layout](#1-project-structure)
2. [Environment & Infrastructure Setup](#2-environment-setup)
3. [PostgreSQL Schema & Migrations](#3-database-schema)
4. [Django Backend — Full Implementation](#4-django-backend)
5. [FastAPI Real-Time Service](#5-fastapi-service)
6. [Celery Workers & Task Design](#6-celery-workers)
7. [Authentication & Authorization (JWT + RBAC)](#7-authentication)
8. [Swagger / OpenAPI Documentation](#8-swagger-api-docs)
9. [Angular Frontend & Dashboards](#9-angular-frontend)
10. [WebSocket Protocol & Agent Communication](#10-websocket-protocol)
11. [On-Premises Deployment (Docker Compose + Nginx)](#11-deployment)
12. [Monitoring, Logging & Health Checks](#12-monitoring)
13. [Security Hardening Checklist](#13-security)
14. [Testing Strategy](#14-testing)
15. [Development Workflow & Sprint Plan](#15-sprint-plan)

---

## 1. Project Structure & Monorepo Layout {#1-project-structure}

```
patch-manager/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── nginx/
│   ├── nginx.conf
│   └── ssl/
│       ├── cert.pem
│       └── key.pem
├── backend/                          # Django project
│   ├── manage.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── config/                       # Django project settings
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery_app.py
│   ├── apps/
│   │   ├── accounts/                 # Users, auth, RBAC
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── permissions.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   ├── inventory/                # Devices, groups, tags
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── filters.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   ├── patches/                  # Patch catalog, approval
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── state_machine.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   └── deployments/              # Rollout orchestration
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       ├── tasks.py              # Celery tasks
│   │       ├── urls.py
│   │       ├── admin.py
│   │       └── tests/
│   └── common/
│       ├── middleware.py
│       ├── pagination.py
│       ├── exceptions.py
│       └── utils.py
├── realtime/                         # FastAPI service
│   ├── main.py
│   ├── requirements.txt
│   ├── auth.py
│   ├── ws_manager.py
│   ├── agent_protocol.py
│   ├── routes/
│   │   ├── agents.py
│   │   ├── events.py
│   │   └── health.py
│   └── tests/
├── agent/                            # Lightweight agent binary
│   ├── agent.py
│   ├── config.yaml
│   └── plugins/
│       ├── linux.py
│       ├── windows.py
│       └── macos.py
├── frontend/                         # Angular app
│   ├── angular.json
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── auth/
│   │   │   │   ├── interceptors/
│   │   │   │   ├── guards/
│   │   │   │   ├── services/
│   │   │   │   └── models/
│   │   │   ├── features/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── devices/
│   │   │   │   ├── patches/
│   │   │   │   ├── deployments/
│   │   │   │   └── settings/
│   │   │   ├── shared/
│   │   │   │   ├── components/
│   │   │   │   ├── pipes/
│   │   │   │   └── directives/
│   │   │   └── app.routes.ts
│   │   ├── environments/
│   │   └── assets/
│   └── Dockerfile
└── scripts/
    ├── init-db.sh
    ├── seed-data.py
    └── generate-certs.sh
```

---

## 2. Environment & Infrastructure Setup {#2-environment-setup}

### 2.1 .env.example

```env
# ─── PostgreSQL ───
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=patchmgr
POSTGRES_USER=patchmgr
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_READ_HOST=postgres-replica  # optional read replica

# ─── Redis ───
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_URL=redis://redis:6379/1

# ─── Django ───
DJANGO_SECRET_KEY=<generate-with-openssl-rand-hex-64>
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_ALLOWED_HOSTS=patchmgr.internal.corp
DJANGO_CORS_ORIGINS=https://patchmgr.internal.corp

# ─── JWT ───
JWT_SECRET_KEY=<shared-between-django-and-fastapi>
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# ─── FastAPI ───
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8001
FASTAPI_WORKERS=4

# ─── Celery ───
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKER_CONCURRENCY=8

# ─── Nginx / TLS ───
SERVER_NAME=patchmgr.internal.corp
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

### 2.2 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./scripts/init-db.sh:/docker-entrypoint-initdb.d/init.sh
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"

  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 200
      DEFAULT_POOL_SIZE: 25
      MIN_POOL_SIZE: 5
    ports:
      - "127.0.0.1:6432:6432"
    depends_on:
      postgres:
        condition: service_healthy

  django:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: >
      gunicorn config.wsgi:application
      --bind 0.0.0.0:8000
      --workers 4
      --threads 2
      --timeout 120
      --access-logfile -
      --error-logfile -
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media
    env_file: .env
    depends_on:
      pgbouncer:
        condition: service_started
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s

  fastapi:
    build:
      context: ./realtime
      dockerfile: Dockerfile
    command: >
      uvicorn main:app
      --host 0.0.0.0
      --port 8001
      --workers ${FASTAPI_WORKERS:-4}
      --loop uvloop
      --http httptools
      --ws websockets
    env_file: .env
    depends_on:
      pgbouncer:
        condition: service_started
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: >
      celery -A config.celery_app worker
      --loglevel=info
      --concurrency=${CELERY_WORKER_CONCURRENCY:-8}
      --max-tasks-per-child=1000
      -Q critical,default,reporting
      -Ofair
    env_file: .env
    depends_on:
      pgbouncer:
        condition: service_started
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: >
      celery -A config.celery_app beat
      --loglevel=info
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    depends_on:
      django:
        condition: service_healthy

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_files:/var/www/static:ro
    depends_on:
      - django
      - fastapi

volumes:
  pg_data:
  redis_data:
  static_files:
  media_files:
```

### 2.3 Nginx Configuration

```nginx
# nginx/nginx.conf
worker_processes auto;
events { worker_connections 2048; }

http {
    include       mime.types;
    sendfile      on;
    tcp_nopush    on;
    tcp_nodelay   on;
    keepalive_timeout 65;
    client_max_body_size 50M;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # Upstream pools
    upstream django_backend {
        server django:8000;
    }
    upstream fastapi_backend {
        server fastapi:8001;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name patchmgr.internal.corp;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name patchmgr.internal.corp;

        ssl_certificate     /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;
        ssl_session_cache   shared:SSL:10m;

        # Security headers
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

        # Angular SPA
        location / {
            root /var/www/frontend;
            try_files $uri $uri/ /index.html;
            expires 1h;
            add_header Cache-Control "public, no-transform";
        }

        # Static files (Django collectstatic)
        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Django REST API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 60s;
        }

        # Django Auth endpoints (stricter rate limit)
        location /api/auth/ {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://django_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Swagger UI
        location /api/docs/ {
            proxy_pass http://django_backend;
            proxy_set_header Host $host;
        }

        # FastAPI real-time endpoints
        location /ws/ {
            proxy_pass http://fastapi_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 86400s;  # 24h for WebSocket
            proxy_send_timeout 86400s;
        }

        # FastAPI REST endpoints (agent check-in etc.)
        location /rt/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://fastapi_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # FastAPI docs
        location /rt/docs {
            proxy_pass http://fastapi_backend;
            proxy_set_header Host $host;
        }
    }
}
```

---

## 3. PostgreSQL Schema & Migrations {#3-database-schema}

### 3.1 Database Initialization Script

```sql
-- scripts/init-db.sql (run via init-db.sh)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- fuzzy text search on hostnames
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- composite GIN indexes

-- Connection pool tuning (for PgBouncer transaction mode)
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '1536MB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET max_wal_senders = 3;
```

### 3.2 Django Models — Full Schema

#### accounts/models.py

```python
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"
        AGENT = "agent", "Agent Service Account"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    department = models.CharField(max_length=100, blank=True)
    must_change_password = models.BooleanField(default=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # LDAP / AD integration fields (on-prem)
    ldap_dn = models.CharField(max_length=500, blank=True, db_index=True)
    is_ldap_user = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active", "role"]),
        ]


class AuditLog(models.Model):
    """Immutable audit trail for all user actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(null=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "-timestamp"]),
        ]
```

#### inventory/models.py

```python
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField


class DeviceGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    dynamic_rules = models.JSONField(default=dict, blank=True)
    is_dynamic = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_group"

    def get_devices(self):
        if self.is_dynamic:
            return Device.objects.filter_by_rules(self.dynamic_rules)
        return self.devices.all()


class DeviceManager(models.Manager):
    def filter_by_rules(self, rules):
        qs = self.get_queryset()
        if "os_family" in rules:
            qs = qs.filter(os_family=rules["os_family"])
        if "os_version" in rules:
            qs = qs.filter(os_version__startswith=rules["os_version"])
        if "tags" in rules:
            qs = qs.filter(tags__contains=rules["tags"])
        if "environment" in rules:
            qs = qs.filter(environment=rules["environment"])
        return qs


class Device(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online"
        OFFLINE = "offline"
        MAINTENANCE = "maintenance"
        DECOMMISSIONED = "decommissioned"

    class OSFamily(models.TextChoices):
        LINUX = "linux"
        WINDOWS = "windows"
        MACOS = "macos"

    class Environment(models.TextChoices):
        PRODUCTION = "production"
        STAGING = "staging"
        DEVELOPMENT = "development"
        TEST = "test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostname = models.CharField(max_length=255, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    mac_address = models.CharField(max_length=17, blank=True)
    os_family = models.CharField(max_length=20, choices=OSFamily.choices)
    os_version = models.CharField(max_length=100)
    os_arch = models.CharField(max_length=20, default="x86_64")
    agent_version = models.CharField(max_length=20, blank=True)
    environment = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.PRODUCTION
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OFFLINE
    )
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    groups = models.ManyToManyField(DeviceGroup, related_name="devices", blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    agent_api_key = models.CharField(max_length=64, unique=True, db_index=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_checkin_ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DeviceManager()

    class Meta:
        db_table = "device"
        indexes = [
            models.Index(fields=["status", "os_family"]),
            models.Index(fields=["environment", "status"]),
            models.Index(fields=["last_seen"]),
        ]

    def __str__(self):
        return self.hostname
```

#### patches/models.py

```python
import uuid
from django.db import models


class Patch(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    class Status(models.TextChoices):
        IMPORTED = "imported"
        REVIEWED = "reviewed"
        APPROVED = "approved"
        REJECTED = "rejected"
        SUPERSEDED = "superseded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor_id = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IMPORTED
    )
    vendor = models.CharField(max_length=100)
    kb_article = models.URLField(blank=True)
    cve_ids = ArrayField(models.CharField(max_length=20), default=list, blank=True)
    applicable_os = ArrayField(models.CharField(max_length=50), default=list)
    package_name = models.CharField(max_length=200, blank=True)
    package_version = models.CharField(max_length=100, blank=True)
    file_url = models.URLField(blank=True)
    file_hash_sha256 = models.CharField(max_length=64, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="superseded_by"
    )
    requires_reboot = models.BooleanField(default=False)

    approved_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patch"
        ordering = ["-released_at"]
        indexes = [
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["-released_at"]),
        ]


class DevicePatchStatus(models.Model):
    class PatchState(models.TextChoices):
        NOT_APPLICABLE = "not_applicable"
        MISSING = "missing"
        PENDING = "pending"
        DOWNLOADING = "downloading"
        INSTALLING = "installing"
        INSTALLED = "installed"
        FAILED = "failed"
        ROLLED_BACK = "rolled_back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        "inventory.Device", on_delete=models.CASCADE, related_name="patch_statuses"
    )
    patch = models.ForeignKey(Patch, on_delete=models.CASCADE, related_name="device_statuses")
    state = models.CharField(
        max_length=20, choices=PatchState.choices, default=PatchState.MISSING
    )
    installed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "device_patch_status"
        unique_together = [("device", "patch")]
        indexes = [
            models.Index(fields=["device", "state"]),
            models.Index(fields=["patch", "state"]),
            models.Index(fields=["state", "-last_attempt"]),
        ]
```

#### deployments/models.py

```python
import uuid
from django.db import models


class Deployment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        SCHEDULED = "scheduled"
        IN_PROGRESS = "in_progress"
        PAUSED = "paused"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"
        ROLLING_BACK = "rolling_back"

    class Strategy(models.TextChoices):
        IMMEDIATE = "immediate"
        CANARY = "canary"
        ROLLING = "rolling"
        MAINTENANCE = "maintenance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    patches = models.ManyToManyField("patches.Patch", related_name="deployments")
    target_groups = models.ManyToManyField(
        "inventory.DeviceGroup", related_name="deployments"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    strategy = models.CharField(
        max_length=20, choices=Strategy.choices, default=Strategy.ROLLING
    )

    canary_percentage = models.IntegerField(default=5)
    wave_size = models.IntegerField(default=50)
    wave_delay_minutes = models.IntegerField(default=15)
    max_failure_percentage = models.FloatField(default=5.0)
    requires_reboot = models.BooleanField(default=False)
    maintenance_window_start = models.TimeField(null=True, blank=True)
    maintenance_window_end = models.TimeField(null=True, blank=True)

    total_devices = models.IntegerField(default=0)
    completed_devices = models.IntegerField(default=0)
    failed_devices = models.IntegerField(default=0)
    current_wave = models.IntegerField(default=0)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_deployments"
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_deployments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deployment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["scheduled_at"]),
        ]


class DeploymentTarget(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        SKIPPED = "skipped"
        ROLLED_BACK = "rolled_back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deployment = models.ForeignKey(
        Deployment, on_delete=models.CASCADE, related_name="targets"
    )
    device = models.ForeignKey(
        "inventory.Device", on_delete=models.CASCADE, related_name="deployment_targets"
    )
    wave_number = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True)

    class Meta:
        db_table = "deployment_target"
        unique_together = [("deployment", "device")]
        indexes = [
            models.Index(fields=["deployment", "wave_number", "status"]),
            models.Index(fields=["device", "-started_at"]),
        ]
```

### 3.3 Table Partitioning (Raw SQL Migration)

```python
# In a Django migration file: 0002_partition_tables.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE audit_log RENAME TO audit_log_old;
            CREATE TABLE audit_log (LIKE audit_log_old INCLUDING ALL)
                PARTITION BY RANGE (timestamp);

            CREATE TABLE audit_log_2025_01 PARTITION OF audit_log
                FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
            CREATE TABLE audit_log_2025_02 PARTITION OF audit_log
                FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
            -- ... repeat for each month

            INSERT INTO audit_log SELECT * FROM audit_log_old;
            DROP TABLE audit_log_old;
            """,
            reverse_sql="-- manual reverse required",
        ),
    ]
```

---

## 4. Django Backend — Full Implementation {#4-django-backend}

### 4.1 Requirements (requirements/base.txt)

```
Django==6.0.3
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
django-filter==24.3
django-cors-headers==4.4.0
django-celery-beat==2.7.0
django-celery-results==2.5.1
drf-spectacular==0.27.2
psycopg[binary]==3.2.3
redis==5.1.1
celery==5.4.0
gunicorn==23.0.0
django-redis==5.4.0
django-health-check==3.18.3
django-auditlog==3.0.0
python-ldap==3.4.4
whitenoise==6.7.0
sentry-sdk==2.16.0
structlog==24.4.0
```

### 4.2 Django Settings (config/settings/base.py)

```python
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.contrib.celery",
    "health_check.contrib.redis",
    # Local apps
    "apps.accounts",
    "apps.inventory",
    "apps.patches",
    "apps.deployments",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.AuditLogMiddleware",
    "common.middleware.RequestTimingMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("POSTGRES_HOST", "pgbouncer"),
        "PORT": os.getenv("PGBOUNCER_PORT", "6432"),
        "NAME": os.getenv("POSTGRES_DB", "patchmgr"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
        },
    },
}

if os.getenv("POSTGRES_READ_HOST"):
    DATABASES["readonly"] = {
        **DATABASES["default"],
        "HOST": os.getenv("POSTGRES_READ_HOST"),
    }

DATABASE_ROUTERS = ["common.db_router.ReadReplicaRouter"]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_CACHE_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "pm",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardCursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "200/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 30))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY"),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainSerializer",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Patch Management API",
    "DESCRIPTION": "On-premises patch management and deployment orchestration.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "Auth", "description": "Authentication & token management"},
        {"name": "Users", "description": "User management (admin only)"},
        {"name": "Devices", "description": "Device inventory & groups"},
        {"name": "Patches", "description": "Patch catalog & approval"},
        {"name": "Deployments", "description": "Deployment orchestration"},
        {"name": "Reports", "description": "Compliance & analytics"},
        {"name": "Health", "description": "System health checks"},
    ],
    "SECURITY": [{"Bearer": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600
CELERY_TASK_SOFT_TIME_LIMIT = 3300
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = {
    "critical": {"exchange": "critical", "routing_key": "critical"},
    "default": {"exchange": "default", "routing_key": "default"},
    "reporting": {"exchange": "reporting", "routing_key": "reporting"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.dev.ConsoleRenderer"
            if os.getenv("DEBUG")
            else "structlog.processors.JSONRenderer",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/patchmgr/django.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
        "celery": {"level": "INFO"},
    },
}
```

*(Sections 4.3–15 contain the full implementation guide for Celery, URLs, serializers, views, FastAPI, WebSocket, Angular frontend, agent, deployment, monitoring, security, and testing — see the complete document for details.)*

---

> **Note**: This document has been updated to use **Angular 20+** and **Django 6.0.3** (latest stable versions as of April 2026).
