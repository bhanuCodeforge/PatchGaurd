# Task 1.6 — Database Initialization & Seed Script

**Time**: 2 hours  
**Dependencies**: 1.4  
**Status**: ✅ Done  
**Files**: `scripts/init-db.sh`, `scripts/seed-data.py`

---

## AI Prompt

```
Create database initialization and seed data scripts for PatchGuard.

1. scripts/init-db.sh (runs as docker-entrypoint-initdb.d):
   - Create extensions: uuid-ossp, pg_trgm, btree_gin
   - Set PostgreSQL performance params via ALTER SYSTEM:
     * max_connections = 200
     * shared_buffers = 512MB
     * effective_cache_size = 1536MB
     * work_mem = 4MB
     * maintenance_work_mem = 128MB
     * wal_level = replica
     * max_wal_senders = 3
     * log_min_duration_statement = 200 (log slow queries > 200ms)

2. scripts/seed-data.py (Django management command: python manage.py seed):
   - Uses factory_boy and faker to generate realistic demo data
   - Creates:
     * 3 users: 1 admin (jdoe/admin), 1 operator (mrodriguez/operator), 1 viewer (lpark/viewer)
     * 6 device groups: "Production Linux servers", "Production Windows servers", "Staging environment", "Development machines", "macOS workstations", "Database servers"
     * 200 devices distributed across groups:
       - 120 Linux (Ubuntu 22.04, Ubuntu 24.04, RHEL 9.3)
       - 60 Windows (Server 2019, Server 2022)
       - 20 macOS (14.4, 14.5)
       - Mix of production/staging/development
       - Random tags: web, api, database, monitoring, CI, cache, AD, file-server
       - 90% online, 5% offline, 5% maintenance
       - Realistic hostnames (web-prod-01, db-staging-03, etc.)
       - Random IP addresses in 10.0.x.x range
       - Random CPU/RAM/disk metadata
     * 30 patches:
       - 5 critical (with CVE IDs like CVE-2025-XXXX)
       - 8 high
       - 12 medium
       - 5 low
       - Mix of vendors: Canonical, Microsoft, Red Hat
       - Realistic titles and descriptions
       - Various statuses: imported, reviewed, approved
       - Applicable OS arrays matching actual device OS versions
     * DevicePatchStatus records:
       - Each device gets 10-20 patch statuses
       - ~85% installed, ~8% missing, ~5% pending, ~2% failed
     * 5 deployments:
       - 1 completed (all targets done)
       - 1 in_progress (72% complete, wave 3 of 4)
       - 1 scheduled (tonight)
       - 1 draft
       - 1 failed (exceeded threshold)
       - Each with realistic DeploymentTarget records
     * 100 audit log entries with realistic actions
   
   - Add --clear flag to delete all existing data before seeding
   - Add --minimal flag to create only 20 devices and 10 patches
   - Print summary of created objects at the end

Make this a proper Django management command at backend/apps/accounts/management/commands/seed.py.
```

---

## Acceptance Criteria

- [x] `python manage.py seed` creates all demo data
- [x] `python manage.py seed --clear` resets and reseeds
- [x] Dashboard stats show meaningful numbers after seeding
- [x] Device groups correctly contain their assigned devices
- [x] Compliance calculations work with seeded data
- [x] No integrity errors or missing foreign keys

## Files Created/Modified

- [x] `scripts/init-db.sh`
- [x] `backend/apps/accounts/management/commands/seed.py`

## Completion Log

## Completion Log

2026-04-04: Created full seed command in apps/accounts/management/commands/seed.py. Used random data generation for 200 devices and 30 patches. Verified migrate and seed logic.
