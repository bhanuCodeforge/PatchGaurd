# Task 10.3 — Monitoring & Observability

**Time**: 2 hours  
**Dependencies**: 10.1  
**Status**: ⬜ Not Started  
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

- [ ] All services output structured JSON logs
- [ ] Health endpoints work for all services
- [ ] Management commands execute correctly
- [ ] Log rotation configured
- [ ] Operations runbook is comprehensive
- [ ] Alerting rules documented

## Files Created/Modified

- [ ] `backend/apps/accounts/management/commands/system_health.py`
- [ ] `backend/apps/accounts/management/commands/clear_cache.py`
- [ ] `backend/apps/accounts/management/commands/recount_compliance.py`
- [ ] `backend/apps/accounts/management/commands/export_audit.py`
- [ ] `OPERATIONS_RUNBOOK.md`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
