# Task 4.3 — Deployment Orchestration API

**Time**: 4 hours  
**Dependencies**: 2.4, 4.1, 4.2  
**Status**: ✅ Done  
**Files**: `deployments/serializers.py`, `deployments/views.py`, `deployments/urls.py`

---

## AI Prompt

```
Implement the complete deployment orchestration REST API for PatchGuard.

1. deployments/serializers.py:

   DeploymentListSerializer:
   - Fields: id, name, status, strategy, total_devices, completed_devices, failed_devices, current_wave, created_by (username), created_at, started_at, completed_at
   - Computed progress_percentage, failure_rate

   DeploymentDetailSerializer:
   - All fields
   - Nested patches (PatchListSerializer, many=True, read-only)
   - Nested target_groups (DeviceGroupSerializer, many=True, read-only)
   - Computed wave_summary: list of { wave_number, total, completed, failed, in_progress }
   - Computed target_breakdown: { queued, in_progress, completed, failed, skipped }

   DeploymentCreateSerializer:
   - Required: name, patch_ids (list of UUID), target_group_ids (list of UUID), strategy
   - Optional: description, canary_percentage, wave_size, wave_delay_minutes, max_failure_percentage, requires_reboot, maintenance_window_start/end, scheduled_at
   - Validate: at least one patch, at least one group, patches must be in "approved" status
   - On create: set created_by from request.user

   DeploymentTargetSerializer:
   - Fields: id, device (hostname + id), wave_number, status, started_at, completed_at, error_log

2. deployments/views.py:

   DeploymentViewSet (ModelViewSet):
   - get_permissions: create/update/execute/pause/cancel need IsOperatorOrAbove, read needs ReadOnlyForViewers, destroy needs IsAdmin
   - filterset_fields: ["status", "strategy", "created_by"]
   - ordering_fields: ["created_at", "started_at", "status"]
   
   Custom actions:
   
   POST {id}/approve/ → admin approves a deployment (changes draft → scheduled)
   POST {id}/execute/ → start deployment immediately
   POST {id}/pause/ → pause running deployment
   POST {id}/resume/ → resume paused deployment
   POST {id}/cancel/ → cancel deployment
   POST {id}/rollback/ → initiate rollback
   GET {id}/progress/ → real-time progress stats
   GET {id}/targets/ → paginated list of deployment targets
   GET {id}/failed/ → list of failed targets with error logs
   GET {id}/timeline/ → ordered list of status changes with timestamps

3. Reporting endpoints:
   GET /api/v1/reports/dashboard-stats/ → cached dashboard stats
   GET /api/v1/reports/compliance/ → detailed compliance report

4. deployments/urls.py:
   - Router with DeploymentViewSet
   - Report URLs

5. Tests covering complete deployment lifecycle.
```

---

## Acceptance Criteria

- [x] Full deployment lifecycle works end-to-end
- [x] Execute resolves devices from groups correctly
- [x] Pause/resume/cancel change status correctly
- [x] Progress endpoint returns accurate real-time data
- [x] Failed targets are queryable with error logs
- [x] Dashboard stats endpoint returns all required data
- [x] Compliance report is accurate
- [x] All tests pass

## Files Created/Modified

- [x] `backend/apps/deployments/serializers.py`
- [x] `backend/apps/deployments/views.py`
- [x] `backend/apps/deployments/urls.py`
- [x] `backend/apps/deployments/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
