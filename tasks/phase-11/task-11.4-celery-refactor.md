
# Task 11.4 — Celery Task Hierarchy Refactor

**Time**: 3–7 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: `backend/celery_worker.py`, `apps/patches/tasks`, migration notes, test suite

---

## Scope

Implement two-level Celery tasks to orchestrate deployments (`orchestrate_deployment`, `execute_wave`, `report_device_result`) with dedicated queues and timeouts.

---

## Checklist

- [ ] Add new Celery tasks and queue routing
- [ ] Ensure orchestrator idempotency and persist minimal state in DB
- [ ] Add monitoring and alerting for stuck waves
- [ ] Update migration notes and test suite

---

## Acceptance Criteria

- [ ] Worker crash loses at most one wave, not entire deployment
- [ ] Orchestrator can re-schedule waves idempotently
- [ ] All new tasks and queues are covered by tests

---

## Completion Log

**Completed**:  
**Notes**: 