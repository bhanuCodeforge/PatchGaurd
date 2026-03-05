# Task 5.1 — Deployment Execution Task

**Time**: 4 hours  
**Dependencies**: 4.3  
**Status**: ✅ Done  
**Files**: `deployments/tasks.py`

---

## AI Prompt

```
Implement the core deployment execution Celery task for PatchGuard.

deployments/tasks.py:

1. execute_deployment(self, deployment_id: str) — Main orchestration task:
   - bind=True, queue="critical", max_retries=3, retry_backoff=True
   - Build waves based on strategy: IMMEDIATE, CANARY, ROLLING, MAINTENANCE
   - For each wave: publish commands to Redis, poll for completion, check failure threshold
   - Publish progress to Redis channel "deployment:progress"
   - Handle SoftTimeLimitExceeded, retry with backoff

2. cancel_deployment_task(deployment_id: str)
3. process_scheduled_deployments() — periodic, every 1 minute
4. Helper: publish_progress(deployment)
5. Helper: update_deployment_counters(deployment)

Write tests for all strategies, failure threshold, pause/resume, and cancel flows.
```

---

## Acceptance Criteria

- [x] All three strategies (immediate, canary, rolling) work correctly
- [x] Failure threshold halts deployment
- [x] Pause/resume works between waves
- [x] Progress published to Redis in real time
- [x] Scheduled deployments trigger automatically
- [x] Task retries on transient failures
- [x] All tests pass

## Files Created/Modified

- [x] `backend/apps/deployments/tasks.py`
- [x] `backend/apps/deployments/tests/test_tasks.py`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
