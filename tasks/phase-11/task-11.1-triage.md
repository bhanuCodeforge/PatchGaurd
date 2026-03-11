
# Task 11.1 — Triage Phase 11

**Time**: 1 day  
**Depends on**: Phase 11 plan approval  
**Status**: ✅ Complete  
**Files**: triage spreadsheet, issue tracker, tracker updates

---

## Scope

Break Phase 11 into discrete actionable tickets with owners, estimates, and dependencies. Map dependencies, identify quick wins, update tracker.

---

## Checklist

- [x] Create a ticket (GitHub/Jira/other) for each subtask
- [x] Assign owner and estimate to each ticket
- [x] Map dependencies and identify quick wins
- [x] Update tracker and/or spreadsheet with ticket status

---

## Acceptance Criteria

- [x] All Phase 11 items represented as tickets/issues
- [x] Each ticket has an owner and estimate
- [x] Quick wins identified and scheduled
- [x] Tracker/spreadsheet up to date

---

## Issue Tracker

| ID | Title | Owner | Estimate | Priority | Status | Depends On | Quick Win |
|:---|:------|:------|:---------|:---------|:-------|:-----------|:----------|
| PG-1101 | Triage Phase 11 | TBD | 1d | Critical | ✅ Done | — | ✅ |
| PG-1102 | BFF / API Gateway Prototype | TBD | 3–5d | High | 🔄 In Progress | PG-1101 | — |
| PG-1103 | Redis Streams Migration for WebSocket Fan-out | TBD | 5–10d | High | 🔄 In Progress | PG-1101 | — |
| PG-1104 | Celery Task Hierarchy Refactor | TBD | 3–7d | High | ⬜ Backlog | PG-1101 | — |
| PG-1105 | DeploymentEvent Table & Event Sourcing | TBD | 3–5d | High | ⬜ Backlog | PG-1101 | — |
| PG-1106 | Materialized View for Compliance Stats | TBD | 2–3d | Medium | ⬜ Backlog | PG-1101 | ✅ |
| PG-1107 | Agent API Key Hardening & Rotation | TBD | 2–4d | Medium | ⬜ Backlog | PG-1101 | ✅ |
| PG-1108 | Frontend UX Improvements | TBD | 2–4d | Medium | ⬜ Backlog | PG-1101 | — |

---

## Dependency Map

```
PG-1101 (Triage) ──┬──> PG-1102 (BFF)
                   ├──> PG-1103 (Redis Streams)    ← Largest effort, start ASAP
                   ├──> PG-1104 (Celery Refactor)  ← Can overlap with 1103
                   ├──> PG-1105 (DeploymentEvent)  ← Feeds into 1106
                   ├──> PG-1106 (Materialized View) ← Depends on 1105 for counters
                   ├──> PG-1107 (API Key Hardening) ← Parallel to all
                   └──> PG-1108 (UX Improvements)  ← Parallel to all
```

---

## Quick Wins (Schedule First)

1. **PG-1106** (Materialized View — 2–3d): Low risk, high payoff on dashboard latency.
2. **PG-1107** (API Key Hardening — 2–4d): Security improvement, self-contained.

---

## Running Order Recommendation

| Week | Tasks | Rationale |
|:-----|:------|:----------|
| Week 1 | PG-1102 + PG-1103 (start) | BFF unblocks Angular; Streams is longest effort |
| Week 2 | PG-1103 (cont.) + PG-1107 | Keep Streams going; ship key hardening |
| Week 3 | PG-1104 + PG-1105 | Celery + Event Sourcing together (shared models) |
| Week 4 | PG-1106 + PG-1108 | Materialized view + UX polish |

---

## Completion Log

**Completed**: 2026-04-11  
**Notes**: All Phase 11 items triaged. BFF (PG-1102) and Redis Streams (PG-1103) started in parallel immediately.