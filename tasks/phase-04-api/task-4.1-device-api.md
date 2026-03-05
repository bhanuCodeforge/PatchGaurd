# Task 4.1 — Device Inventory API

**Time**: 4 hours  
**Dependencies**: 2.2, 3.2  
**Status**: ✅ Done  
**Files**: `inventory/serializers.py`, `inventory/views.py`, `inventory/filters.py`, `inventory/urls.py`

---

## AI Prompt

```
Implement the complete device inventory REST API for PatchGuard.

1. inventory/filters.py — DeviceFilter (django_filters.FilterSet):
   - hostname: CharFilter (icontains)
   - os_family: ChoiceFilter
   - environment: ChoiceFilter
   - status: ChoiceFilter
   - tag: CharFilter with custom method filter_by_tag (ArrayField contains)
   - group: UUIDFilter on groups__id
   - last_seen_after: DateTimeFilter (gte)
   - last_seen_before: DateTimeFilter (lte)
   - agent_version: CharFilter (exact)
   - compliance_below: NumberFilter with custom method (devices below X% compliance)

2. inventory/serializers.py:

   DeviceGroupSerializer:
   - All fields + computed device_count (from get_devices().count())
   - Nested parent group name (read-only)

   DeviceGroupCreateSerializer:
   - Fields for creation: name, description, is_dynamic, dynamic_rules, parent

   DeviceListSerializer (lightweight for list views):
   - Fields: id, hostname, ip_address, os_family, os_version, environment, status, tags, agent_version, last_seen
   - No nested relations for performance

   DeviceDetailSerializer (full for detail views):
   - All fields
   - Nested groups via DeviceGroupSerializer (many=True, read_only)
   - Computed compliance_summary: SerializerMethodField that queries DevicePatchStatus and returns state → count dict
   - Computed patch_stats: { total, installed, missing, pending, failed }

   DeviceCreateSerializer:
   - Required: hostname, ip_address, os_family, os_version
   - Optional: everything else
   - Auto-generate agent_api_key on create using common.utils.generate_api_key()

   DeviceBulkTagSerializer:
   - device_ids: ListField of UUIDField
   - tags: ListField of CharField
   - action: ChoiceField ("add", "remove")

3. inventory/views.py:

   DeviceViewSet (ModelViewSet):
   - permission_classes: [ReadOnlyForViewers]
   - filterset_class: DeviceFilter
   - search_fields: ["hostname", "ip_address", "tags"]
   - ordering_fields: ["hostname", "last_seen", "status", "os_family", "created_at"]
   - get_queryset: select_related + prefetch_related, exclude decommissioned
   - get_serializer_class: DeviceListSerializer for list, DeviceDetailSerializer for retrieve, DeviceCreateSerializer for create
   
   Custom actions:
   - GET {id}/compliance/ → detailed compliance breakdown for a single device
   - GET {id}/patches/ → list all DevicePatchStatus for this device with patch details
   - GET {id}/deployments/ → list recent DeploymentTargets for this device
   - POST {id}/scan/ → trigger a patch scan (enqueue Celery task)
   - POST {id}/reboot/ → send reboot command via Redis pub/sub
   - POST bulk-tag/ → bulk add/remove tags on multiple devices
   - POST bulk-group/ → bulk add devices to a group
   - GET stats/ → aggregate stats: total, by_os, by_environment, by_status, online_count
   - Decorate all with @extend_schema for Swagger

   DeviceGroupViewSet (ModelViewSet):
   - permission_classes: [ReadOnlyForViewers]
   - search_fields: ["name"]
   - Custom action: GET {id}/devices/ → list devices in this group (respects dynamic rules)

4. inventory/urls.py:
   - Router with DeviceViewSet at "" (results in /api/v1/devices/)
   - Router with DeviceGroupViewSet at "groups" (results in /api/v1/devices/groups/)

5. Write comprehensive tests:
   - CRUD operations for devices and groups
   - All filter combinations
   - Bulk tag operations
   - Compliance endpoint accuracy
   - Permission enforcement (viewer can read, operator can write)
   - Pagination behavior
   - Search functionality
```

---

## Acceptance Criteria

- [x] All CRUD operations work for devices and groups
- [x] Filtering by OS, environment, status, tag, group works
- [x] Compliance endpoint returns accurate percentages
- [x] Bulk operations update multiple devices
- [x] Dynamic groups resolve devices correctly
- [x] Swagger shows all endpoints with examples
- [x] All tests pass

## Files Created/Modified

- [x] `backend/apps/inventory/serializers.py`
- [x] `backend/apps/inventory/views.py`
- [x] `backend/apps/inventory/filters.py`
- [x] `backend/apps/inventory/urls.py`
- [x] `backend/apps/inventory/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
