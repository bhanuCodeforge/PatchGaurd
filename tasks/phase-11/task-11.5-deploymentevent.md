
# Task 11.5 — DeploymentEvent Table & Event Sourcing

**Time**: 3–5 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: Django model, migration, backfill script, API updates

---

## Scope

Add immutable `DeploymentEvent` model, backfill current deployment state, and refactor APIs to use event aggregates.

---

## Checklist

- [ ] Create Django model and migration for DeploymentEvent
- [ ] Write management command to backfill events from existing deployments
- [ ] Refactor API to return counters from events/materialized summary
- [ ] Add verification checks for event consistency

---

## Acceptance Criteria

- [ ] Counters are correct under high concurrency (verified by load test)
- [ ] Full audit trail of device events is available
- [ ] API remains compatible for consumers

---

## Completion Log

**Completed**:  
**Notes**: 