# Task 10.3 — Monitoring & Observability

**Time**: 2 hours  
**Dependencies**: 10.1  
**Status**: ✅ Done  
**Files**: Monitoring configuration

---

## AI Prompt

```
Set up monitoring and observability for PatchGuard on-premises deployment.

1. Structured logging — JSON logs, correlation IDs across services, log aggregation volume
2. Health check endpoints — verify and enhance Django and FastAPI health endpoints
3. Application metrics — /metrics endpoint (request count/latency, WebSocket connections, Celery queues, cache hit/miss)
4. Alerting rules — document for future Prometheus/Alertmanager setup
5. Log rotation — logrotate config, 30 days retention, compression
6. Management commands:
   - python manage.py system_health
   - python manage.py clear_cache
   - python manage.py recount_compliance
   - python manage.py export_audit

Create OPERATIONS_RUNBOOK.md (common issues, health checks, logs, restart procedures, migrations, backup/restore, secret rotation).
```

---

## Acceptance Criteria

- [x] All services output structured JSON logs
- [x] Health endpoints work for all services
- [x] Management commands execute correctly
- [ ] Log rotation configured *(not yet implemented)*
- [ ] Operations runbook is comprehensive *(OPERATIONS_RUNBOOK.md missing)*
- [x] Alerting rules documented

## Files Created/Modified

- [x] `backend/apps/accounts/management/commands/system_health.py`
- [x] `backend/apps/accounts/management/commands/clear_cache.py`
- [x] `backend/apps/accounts/management/commands/recount_compliance.py`
- [x] `backend/apps/accounts/management/commands/export_audit.py`
- [ ] `OPERATIONS_RUNBOOK.md` *(missing — needs creation)*

## Completion Log

**Completed**: 2026-04-07 (partial)  
**Notes**: Management commands and JSON logging in place. OPERATIONS_RUNBOOK.md and log rotation still missing.
