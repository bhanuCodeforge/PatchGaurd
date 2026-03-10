
# Task 11.6 — Materialized View for Compliance Stats

**Time**: 2–3 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: SQL migration, Celery task, API, tests

---

## Scope

Implement a Postgres materialized view to precompute compliance statistics and a refresh pipeline (Celery task + Redis cache snapshot).

---

## Checklist

- [ ] Create materialized view SQL and migration notes
- [ ] Implement Celery task to refresh on deployment completion
- [ ] Add API to read cached snapshot
- [ ] Write tests for view refresh and API

---

## Acceptance Criteria

- [ ] Dashboard and compliance endpoints respond within target latency under load
- [ ] Materialized view is refreshed on deployment completion
- [ ] API returns up-to-date compliance stats

---

## Completion Log

**Completed**:  
**Notes**: 