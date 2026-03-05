# Task 10.1 — Production Deployment Pipeline

**Time**: 3 hours  
**Dependencies**: All phases  
**Status**: ⬜ Not Started  
**Files**: Root-level deployment files

---

## AI Prompt

```
Create the complete production deployment pipeline for PatchGuard on-premises.

1. Dockerfile optimization (multi-stage builds):
   - backend/Dockerfile: builder → runtime, non-root, <300MB
   - realtime/Dockerfile: multi-stage, non-root, HEALTHCHECK
   - frontend/Dockerfile: npm ci + ng build → nginx:alpine, <50MB

2. scripts/deploy.sh — Deployment script (validate, pull, migrate, backup, rolling restart, seed)
3. scripts/backup.sh — Database backup (pg_dump, gzip, retention 30 daily + 12 weekly)
4. scripts/restore.sh — Database restore (list, confirm, restore, verify)
5. scripts/health-check.sh — System health check (all services, disk, DB, Redis, Celery)
6. DEPLOYMENT_CHECKLIST.md — Pre-deployment, first deploy, rollback plan
7. VERSION file and Docker image tagging
```

---

## Acceptance Criteria

- [ ] All Dockerfiles build successfully
- [ ] Production deploy.sh runs without errors
- [ ] Database backup and restore work
- [ ] Health check script reports accurate status
- [ ] Rolling restart achieves zero downtime
- [ ] Documentation covers all deployment steps

## Files Created/Modified

- [ ] `backend/Dockerfile` (optimized)
- [ ] `realtime/Dockerfile` (optimized)
- [ ] `frontend/Dockerfile` (optimized)
- [ ] `scripts/deploy.sh`
- [ ] `scripts/backup.sh`
- [ ] `scripts/restore.sh`
- [ ] `scripts/health-check.sh`
- [ ] `DEPLOYMENT_CHECKLIST.md`
- [ ] `VERSION`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
