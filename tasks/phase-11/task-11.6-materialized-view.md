
# Task 11.6 — Materialized View for Compliance Stats

**Status**: ✅ Complete  
**Files**: `backend/apps/patches/migrations/0006_compliance_materialized_view.py`, `backend/apps/patches/tasks.py`

---

## Implementation

### Materialized View: `mv_compliance_stats`

PostgreSQL `MATERIALIZED VIEW` precomputing fleet-wide compliance stats.

**Columns**:
- `total_devices`, `online_devices`
- `compliant_devices` (rate ≥ 90%), `non_compliant_devices`
- `avg_compliance_rate` (fleet average)
- `missing_critical_patches`, `missing_high_patches`
- `devices_by_os` (JSON), `devices_by_env` (JSON)
- `refreshed_at`

**Index**: Unique singleton index for fast single-row read.

### Refresh Strategy

| Trigger | Frequency |
|---|---|
| Celery Beat | Every hour |
| Post-deployment | On `orchestrate_deployment` completion |

### Celery Task: `refresh_compliance_materialized_view`

- `REFRESH MATERIALIZED VIEW CONCURRENTLY` (non-blocking, requires unique index)
- Stores snapshot JSON in Redis for ultra-fast BFF/dashboard reads
- Graceful fallback on SQLite (dev): logs warning, returns `{"status": "skipped"}`

### Usage

```python
# Redis cache key
"bff:compliance_mv_snapshot"  # TTL: 1 hour

# Direct DB query (PostgreSQL)
SELECT avg_compliance_rate, missing_critical_patches FROM mv_compliance_stats;
```

---

## Completion Log

**Completed**: 2026-04-11  
**Migration**: `0006_compliance_materialized_view` ✅ applied (SQLite skipped gracefully)  
**Django check**: 0 issues