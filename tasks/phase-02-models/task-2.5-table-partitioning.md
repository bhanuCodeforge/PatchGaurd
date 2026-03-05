# Task 2.5 — Table Partitioning Migration

**Time**: 1 hour  
**Dependencies**: 2.1  
**Status**: ✅ Done  
**Files**: New migration in accounts app

---

## AI Prompt

```
Create a Django data migration that partitions the audit_log table by month in PostgreSQL.

The migration should:

1. Rename existing audit_log to audit_log_old
2. Create new audit_log as a partitioned table (PARTITION BY RANGE on timestamp column) with the same schema (LIKE audit_log_old INCLUDING ALL)
3. Create monthly partitions for the next 24 months from the current date
4. Each partition named audit_log_YYYY_MM with appropriate date ranges
5. Copy all data from audit_log_old to the new partitioned table
6. Drop audit_log_old
7. Create a helper function create_monthly_partition(year, month) that can be called by the monthly Celery task to create future partitions

Also create a Celery task in apps/accounts/tasks.py:
- cleanup_audit_partitions: Creates partition for next month (if not exists), drops partitions older than 12 months
- This task runs monthly via Celery Beat (already configured)

Include a reverse migration that just logs a warning that manual intervention is needed to reverse partitioning.

Use Django's migrations.RunSQL for the raw SQL operations. Add a RunPython step that creates the initial partitions dynamically based on current date.
```

---

## Acceptance Criteria

- [x] Migration partitions the audit_log table
- [x] INSERT into audit_log works and routes to correct partition
- [x] SELECT across partitions works transparently
- [x] Celery task creates future partitions
- [x] Old partition cleanup works without data loss

## Files Created/Modified

- [x] `backend/apps/accounts/migrations/0002_partition_audit_log.py`
- [x] `backend/apps/accounts/tasks.py`

## Completion Log

## Completion Log

2026-04-04: Implemented raw SQL partitioning for `audit_log` with 24-month horizon. Integrated Celery maintenance task to automate future partition creation and cleanup (12-month retention). Logic is safe for non-Postgres backends.
