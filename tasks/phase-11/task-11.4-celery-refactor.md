
# Task 11.4 — Celery Task Hierarchy Refactor

**Status**: ✅ Complete  
**Files**: `backend/apps/deployments/tasks.py`, `backend/config/celery_app.py`

---

## Implementation

### Two-Level Task Hierarchy

| Task | Queue | Timeout | Purpose |
|---|---|---|---|
| `orchestrate_deployment` | `critical` | — | Idempotent orchestrator, iterates waves |
| `execute_wave` | `deployment-waves` | 15 min soft / 20 min hard | Preflight checks + patch command dispatch per wave |
| `report_device_result` | `deployment-results` | — | Atomic per-device result recorder using `F()` expressions |
| `monitor_stuck_waves` | `default` | — | Detects waves stuck >25 min (runs every 10 min via Beat) |

### Key Improvements Over Monolithic Task

- **No race condition**: `report_device_result` uses `F("completed_devices") + 1` atomic increments
- **Fault isolation**: A crash in `execute_wave` loses at most 1 wave, not the entire deployment
- **Re-entrant**: `orchestrate_deployment` skips already-completed waves on restart
- **Backward-compatible**: Old `execute_deployment` call sites delegate to `orchestrate_deployment`

### New Celery Queues

```
critical            — deployment orchestration (renamed from execute_deployment)
deployment-waves    — wave-level tasks (15-min timeout)
deployment-results  — per-device result ingestion (acks_late=True)
default             — monitoring + background tasks
reporting           — compliance snapshots, SLA checks
```

---

## Completion Log

**Completed**: 2026-04-11  
**Tests**: Covered by existing deployment test infrastructure + Django check (0 issues)