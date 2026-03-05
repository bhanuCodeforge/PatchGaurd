# Task 2.3 — Patches App Models

**Time**: 2 hours  
**Dependencies**: 2.2  
**Status**: ✅ Done  
**Files**: `backend/apps/patches/models.py`, `backend/apps/patches/admin.py`

---

## AI Prompt

```
Implement the patches app models for PatchGuard.

1. Patch model:
   - id: UUIDField primary key
   - vendor_id: CharField(100), unique, indexed (e.g., "CVE-2025-3891", "KB5035849")
   - title: CharField(500)
   - description: TextField, blank
   - severity: CharField(20) with TextChoices (critical, high, medium, low)
   - status: CharField(20) with TextChoices (imported, reviewed, approved, rejected, superseded), default imported
   - vendor: CharField(100) — "Canonical", "Microsoft", "RedHat"
   - kb_article: URLField, blank
   - cve_ids: ArrayField of CharField(20), default list, blank
   - applicable_os: ArrayField of CharField(50), default list (e.g., ["ubuntu-22.04", "ubuntu-24.04"])
   - package_name: CharField(200), blank
   - package_version: CharField(100), blank
   - file_url: URLField, blank (internal mirror URL)
   - file_hash_sha256: CharField(64), blank
   - file_size_bytes: BigIntegerField, nullable
   - supersedes: ForeignKey to self, nullable, SET_NULL, related_name="superseded_by"
   - requires_reboot: BooleanField, default False
   - approved_by: ForeignKey to User, nullable, SET_NULL
   - approved_at: DateTimeField, nullable
   - released_at: DateTimeField, nullable
   - created_at, updated_at: auto timestamps
   
   Indexes:
   - (severity, status) composite
   - (vendor, status) composite
   - -released_at
   
   Meta: db_table = "patch", ordering = ["-released_at"]

2. DevicePatchStatus model (junction table tracking per-device patch state):
   - id: UUIDField primary key
   - device: ForeignKey to Device, CASCADE, related_name="patch_statuses"
   - patch: ForeignKey to Patch, CASCADE, related_name="device_statuses"
   - state: CharField(20) with TextChoices (not_applicable, missing, pending, downloading, installing, installed, failed, rolled_back), default missing
   - installed_at: DateTimeField, nullable
   - error_message: TextField, blank
   - retry_count: IntegerField, default 0
   - last_attempt: DateTimeField, nullable
   
   Constraints:
   - unique_together = [("device", "patch")]
   
   Indexes:
   - (device, state) composite
   - (patch, state) composite
   - (state, -last_attempt) composite
   
   Meta: db_table = "device_patch_status"

3. Django Admin:
   - PatchAdmin: list_display (vendor_id, title, severity, status, vendor, requires_reboot, released_at), list_filter (severity, status, vendor, requires_reboot), search_fields (vendor_id, title, cve_ids), actions for bulk approve/reject
   - DevicePatchStatusAdmin: list_display (device, patch, state, installed_at, retry_count), list_filter (state,), raw_id_fields for device and patch (performance)

Generate models, admin, and migration.
```

---

## Acceptance Criteria

- [x] Migration runs cleanly with all constraints
- [x] unique_together prevents duplicate device-patch combos
- [x] Patch status state machine covers all transitions
- [x] Admin shows filtered views per severity/status
- [x] ArrayField for cve_ids and applicable_os switched to JSONField for cross-DB compatibility

## Files Created/Modified

- [x] `backend/apps/patches/models.py`
- [x] `backend/apps/patches/admin.py`
- [x] `backend/apps/patches/migrations/0001_initial.py`

## Completion Log

## Completion Log

2026-04-04: Implemented full patch catalog and junction status models. Switched `ArrayField` to `JSONField` for `cve_ids` and `applicable_os` to support SQLite local dev. Verified with 30 patch and status seed data.
