# Task 4.2 — Patch Catalog API

**Time**: 4 hours  
**Dependencies**: 2.3, 3.2  
**Status**: ✅ Done  
**Files**: `patches/serializers.py`, `patches/views.py`, `patches/filters.py`, `patches/urls.py`, `patches/state_machine.py`

---

## AI Prompt

```
Implement the complete patch catalog REST API for PatchGuard.

1. patches/state_machine.py — PatchStateMachine:
   Define valid status transitions:
   - imported → reviewed, rejected
   - reviewed → approved, rejected
   - approved → superseded
   - rejected → imported (allow re-import)
   - superseded → (terminal, no transitions)
   
   Methods:
   - can_transition(current_status, new_status) → bool
   - transition(patch, new_status, user=None) → updates status, sets approved_by/at if approving
   - get_available_transitions(current_status) → list of valid next states

2. patches/filters.py — PatchFilter:
   - severity: ChoiceFilter
   - status: ChoiceFilter
   - vendor: CharFilter (icontains)
   - cve_id: CharFilter with custom method (search in cve_ids ArrayField)
   - applicable_os: CharFilter with custom method (search in applicable_os ArrayField)
   - requires_reboot: BooleanFilter
   - released_after: DateTimeFilter
   - released_before: DateTimeFilter
   - has_active_exploitation: BooleanFilter (placeholder for future enrichment)

3. patches/serializers.py:

   PatchListSerializer (lightweight):
   - Fields: id, vendor_id, title, severity, status, vendor, cve_ids, applicable_os, requires_reboot, released_at
   - Computed affected_device_count: count of devices with state="missing" for this patch

   PatchDetailSerializer (full):
   - All fields
   - Computed affected_device_count
   - Computed device_status_breakdown: { missing: N, pending: N, installed: N, failed: N }
   - Nested supersedes and superseded_by patch names

   PatchCreateSerializer:
   - For manual patch creation
   - Required: vendor_id, title, severity, vendor, applicable_os

   PatchApprovalSerializer:
   - Just a comment field (optional) for audit trail

   DevicePatchStatusSerializer:
   - All fields with nested device hostname and patch vendor_id

4. patches/views.py:

   PatchViewSet (ModelViewSet):
   - permission_classes: [ReadOnlyForViewers]
   - filterset_class: PatchFilter
   - search_fields: ["vendor_id", "title", "description", "cve_ids", "package_name"]
   - ordering_fields: ["severity", "status", "released_at", "vendor"]
   - get_serializer_class: different for list/detail/create
   
   Custom actions:
   - POST {id}/approve/ → transition to approved (operator+). Uses PatchStateMachine. Creates AuditLog.
   - POST {id}/reject/ → transition to rejected (operator+). Optional reason.
   - POST {id}/review/ → transition to reviewed (operator+)
   - GET {id}/affected-devices/ → list devices missing this patch with device details
   - POST bulk-approve/ → approve multiple patches at once
   - GET stats/ → aggregate: total, by_severity, by_status, awaiting_review_count, critical_pending_count
   - GET compliance-summary/ → overall compliance rate across all devices

   DevicePatchStatusViewSet (ReadOnlyModelViewSet):
   - Filtered by device or patch via query params
   - Used by device detail and patch detail views

5. patches/tasks.py — Celery tasks:

   sync_vendor_patches (periodic, every 6 hours):
   - Placeholder that simulates importing patches from vendor feeds
   - Creates Patch objects with status="imported"
   - Publishes notification to Redis for real-time alert

   generate_compliance_snapshot (periodic, daily):
   - Calculate compliance per device group, per OS, overall
   - Cache results in Redis for dashboard consumption
   - Create a compliance report record (optional: create ComplianceSnapshot model)

6. patches/urls.py:
   - Router with PatchViewSet
   - Router with DevicePatchStatusViewSet at "status"

7. Tests for all endpoints, state transitions, and compliance calculations.
```

---

## Acceptance Criteria

- [x] Patch CRUD works with proper validation
- [x] State machine enforces valid transitions only
- [x] Approval creates audit trail
- [x] Compliance calculations are accurate
- [x] Affected device counts match actual data
- [x] Bulk approve works for multiple patches
- [x] All Swagger annotations are correct
- [x] Tests cover all state transitions

## Files Created/Modified

- [x] `backend/apps/patches/state_machine.py`
- [x] `backend/apps/patches/serializers.py`
- [x] `backend/apps/patches/views.py`
- [x] `backend/apps/patches/filters.py`
- [x] `backend/apps/patches/urls.py`
- [x] `backend/apps/patches/tasks.py`
- [x] `backend/apps/patches/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
