
# Task 11.5 — DeploymentEvent Table & Event Sourcing

**Status**: ✅ Complete  
**Files**: `backend/apps/deployments/models.py`, `backend/apps/deployments/migrations/0002_deploymentevent.py`, `backend/apps/deployments/views.py`, `backend/apps/deployments/management/commands/backfill_deployment_events.py`

---

## Implementation

### New Model: `DeploymentEvent`

Append-only event log for every deployment lifecycle transition.

| Event Type | Description |
|---|---|
| `queued` | Device added to deployment |
| `started` | Agent received patch command |
| `completed` | Patching completed successfully |
| `failed` | Patching failed |
| `skipped` | Preflight check failed — device skipped |
| `cancelled` | Deployment cancelled by operator |
| `wave_start` | Wave begun |
| `wave_done` | Wave completed |

### API Endpoint

`GET /api/v1/deployments/{id}/events/` — returns paginated event log with optional `?event_type=failed,completed` filter.

### Backfill Command

```bash
python manage.py backfill_deployment_events --dry-run
python manage.py backfill_deployment_events --deployment-id <uuid>
```

---

## Completion Log

**Completed**: 2026-04-11  
**Migration**: `0002_deploymentevent` ✅ applied  
**Django check**: 0 issues