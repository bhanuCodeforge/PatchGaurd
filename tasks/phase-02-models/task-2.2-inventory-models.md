# Task 2.2 — Inventory App Models

**Time**: 2 hours  
**Dependencies**: 2.1  
**Status**: ✅ Done  
**Files**: `backend/apps/inventory/models.py`, `backend/apps/inventory/admin.py`

---

## AI Prompt

```
Implement the inventory app models for PatchGuard.

1. DeviceGroup model:
   - id: UUIDField primary key
   - name: CharField(200), unique
   - description: TextField, blank
   - dynamic_rules: JSONField, default dict, blank (example: {"os_family": "linux", "tags": ["production"]})
   - is_dynamic: BooleanField, default False
   - parent: ForeignKey to self, nullable, SET_NULL, related_name="children" (for nested groups)
   - created_at: DateTimeField, auto_now_add
   - updated_at: DateTimeField, auto_now
   
   Meta: db_table = "device_group"
   
   Methods:
   - get_devices() → returns queryset of devices. If is_dynamic, filter by dynamic_rules using DeviceManager.filter_by_rules(). Otherwise return self.devices.all()
   - __str__ → name

2. DeviceManager (custom manager):
   - filter_by_rules(rules: dict) → QuerySet
     Supports filtering by: os_family, os_version (startswith), tags (ArrayField contains), environment
     All filters are optional and AND'd together

3. Device model:
   - id: UUIDField primary key
   - hostname: CharField(255), unique, indexed
   - ip_address: GenericIPAddressField, indexed
   - mac_address: CharField(17), blank
   - os_family: CharField(20) with TextChoices (linux, windows, macos)
   - os_version: CharField(100)
   - os_arch: CharField(20), default "x86_64"
   - agent_version: CharField(20), blank
   - environment: CharField(20) with TextChoices (production, staging, development, test), default production
   - status: CharField(20) with TextChoices (online, offline, maintenance, decommissioned), default offline
   - tags: ArrayField of CharField(50), default list, blank
   - groups: ManyToManyField to DeviceGroup, related_name="devices", blank
   - metadata: JSONField, default dict, blank (for CPU, RAM, disk info)
   - agent_api_key: CharField(64), unique, indexed
   - last_seen: DateTimeField, nullable
   - last_checkin_ip: GenericIPAddressField, nullable
   - created_at, updated_at: auto timestamps
   
   objects = DeviceManager()
   
   Indexes:
   - (status, os_family) composite
   - (environment, status) composite
   - last_seen
   
   Meta: db_table = "device"
   Methods: __str__ → hostname

4. Django Admin:
   - DeviceGroupAdmin: list_display, inline for showing member count
   - DeviceAdmin: list_display (hostname, ip_address, os_family, environment, status, last_seen), list_filter (os_family, environment, status), search_fields (hostname, ip_address), filter_horizontal for groups

Generate models, admin, and migration. Include ArrayField import from django.contrib.postgres.fields.
```

---

## Acceptance Criteria

- [x] Migration runs cleanly
- [x] Dynamic groups filter devices correctly by rules
- [x] ArrayField for tags switched to JSONField for cross-DB compatibility
- [x] Admin interface shows all fields with proper filtering
- [x] Device manager filter_by_rules handles all rule types

## Files Created/Modified

- [x] `backend/apps/inventory/models.py`
- [x] `backend/apps/inventory/admin.py`
- [x] `backend/apps/inventory/migrations/0001_initial.py`

## Completion Log

## Completion Log

2026-04-04: Implemented full inventory models. Custom `DeviceManager` handles dynamic rule filtering. Switched `ArrayField` to `JSONField` for `tags` to support SQLite local dev. Verified with 200 device seed data.
