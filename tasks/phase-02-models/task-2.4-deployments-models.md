# Task 2.4 — Deployments App Models

**Time**: 2 hours  
**Dependencies**: 2.3  
**Status**: ✅ Done  
**Files**: `backend/apps/deployments/models.py`, `backend/apps/deployments/admin.py`

---

## AI Prompt

```
Implement the deployments app models for PatchGuard.

1. Deployment model:
   - id: UUIDField primary key
   - name: CharField(200)
   - description: TextField, blank
   - patches: ManyToManyField to Patch, related_name="deployments"
   - target_groups: ManyToManyField to DeviceGroup, related_name="deployments"
   - status: CharField(20) with TextChoices (draft, scheduled, in_progress, paused, completed, failed, cancelled, rolling_back), default draft
   - strategy: CharField(20) with TextChoices (immediate, canary, rolling, maintenance), default rolling
   - canary_percentage: IntegerField, default 5
   - wave_size: IntegerField, default 50
   - wave_delay_minutes: IntegerField, default 15
   - max_failure_percentage: FloatField, default 5.0
   - requires_reboot: BooleanField, default False
   - maintenance_window_start: TimeField, nullable
   - maintenance_window_end: TimeField, nullable
   - total_devices: IntegerField, default 0
   - completed_devices: IntegerField, default 0
   - failed_devices: IntegerField, default 0
   - current_wave: IntegerField, default 0
   - scheduled_at: DateTimeField, nullable
   - started_at: DateTimeField, nullable
   - completed_at: DateTimeField, nullable
   - created_by: ForeignKey to User, SET_NULL, nullable, related_name="created_deployments"
   - approved_by: ForeignKey to User, SET_NULL, nullable, related_name="approved_deployments"
   - created_at, updated_at: auto timestamps
   
   Indexes:
   - (status, -created_at) composite
   - scheduled_at
   
   Meta: db_table = "deployment", ordering = ["-created_at"]
   
   Properties:
   - progress_percentage → computed from completed_devices / total_devices
   - failure_rate → computed from failed_devices / total_devices
   - is_active → status in (in_progress, paused)

2. DeploymentTarget model (per-device tracking within a deployment):
   - id: UUIDField primary key
   - deployment: ForeignKey to Deployment, CASCADE, related_name="targets"
   - device: ForeignKey to Device, CASCADE, related_name="deployment_targets"
   - wave_number: IntegerField, default 0
   - status: CharField(20) with TextChoices (queued, in_progress, completed, failed, skipped, rolled_back), default queued
   - started_at: DateTimeField, nullable
   - completed_at: DateTimeField, nullable
   - error_log: TextField, blank
   
   Constraints:
   - unique_together = [("deployment", "device")]
   
   Indexes:
   - (deployment, wave_number, status) composite
   - (device, -started_at) composite
   
   Meta: db_table = "deployment_target"

3. Django Admin:
   - DeploymentAdmin: list_display (name, status, strategy, total_devices, completed_devices, failed_devices, created_by, created_at), list_filter (status, strategy), readonly_fields for progress fields, inlines for DeploymentTarget (tabular, show first 20)
   - DeploymentTargetAdmin: list_display (deployment, device, wave_number, status, started_at, completed_at), list_filter (status, wave_number), raw_id_fields for deployment and device

Generate models, admin, and migration.
```

---

## Acceptance Criteria

- [x] All migrations run cleanly
- [x] `python manage.py migrate` creates all 8 tables across 4 apps
- [x] Deployment status transitions are valid
- [x] Progress properties calculate correctly
- [x] Admin shows inline deployment targets

## Files Created/Modified

- [x] `backend/apps/deployments/models.py`
- [x] `backend/apps/deployments/admin.py`
- [x] `backend/apps/deployments/migrations/0001_initial.py`

## Completion Log

## Completion Log

2026-04-04: Implemented full deployment orchestration models. Includes wave/canary strategy fields and progress calculation properties. Verified with 5 deployment seed data.
