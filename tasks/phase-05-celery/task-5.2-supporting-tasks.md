# Task 5.2 — Supporting Celery Tasks

**Time**: 2 hours  
**Dependencies**: 5.1  
**Status**: ✅ Done  
**Files**: `inventory/tasks.py`, `patches/tasks.py`

---

## AI Prompt

```
Implement all supporting Celery tasks for PatchGuard.

1. inventory/tasks.py:
   - mark_stale_devices (periodic, every 5 minutes)
   - flush_heartbeat_batch (periodic, every 30 seconds)
   - scan_device_patches(device_id: str)

2. patches/tasks.py:
   - sync_vendor_patches (periodic, every 6 hours)
   - generate_compliance_snapshot (periodic, daily at 01:00)
   - check_superseded_patches

3. accounts/tasks.py:
   - cleanup_audit_partitions (periodic, monthly)

Write tests for each task using mock Redis and time freezing (freezegun).
```

---

## Acceptance Criteria

- [x] Stale device detection works within 5-minute cycles
- [x] Heartbeat batching reduces DB writes
- [x] Vendor sync creates realistic patch data
- [x] Compliance snapshot calculates accurately
- [x] Superseded patch detection works
- [x] Audit partition maintenance runs without errors
- [x] All tests pass

## Files Created/Modified

- [x] `backend/apps/inventory/tasks.py`
- [x] `backend/apps/patches/tasks.py`
- [x] `backend/apps/accounts/tasks.py`
- [x] Test files for each

## Completion Log

<!-- Record completion date, notes, and any deviations -->
