
# Task 11.7 — Agent API Key Hardening & Rotation

**Status**: ✅ Complete  
**Files**: `backend/apps/inventory/models.py`, `backend/apps/inventory/migrations/0007_device_key_rotation_fields.py`, `backend/apps/inventory/tasks.py`, `backend/config/celery_app.py`

---

## Implementation

### Model Changes

Two new fields on `Device`:

| Field | Type | Purpose |
|---|---|---|
| `key_created_at` | `DateTimeField(null=True)` | When current key was generated |
| `key_last_rotated_at` | `DateTimeField(null=True)` | Timestamp of most-recent rotation |

### Automated Rotation: `rotate_stale_api_keys` Celery Task

- Runs daily via Beat at **02:30 UTC**
- Finds devices with `key_created_at` (or `key_last_rotated_at`) older than **90 days**  
- Generates new `secrets.token_urlsafe(32)` key, saves to DB
- Pushes `KEY_ROTATED` command to agent via **Redis agent command channel**
  - Agent receives new key pre-emptively and writes it to `config.yaml`
  - Key is **never transmitted over WebSocket query-strings**

### Agent Command Payload

```json
{
  "command": "KEY_ROTATED",
  "payload": {
    "new_api_key": "...",
    "effective_at": "2026-04-11T02:30:00Z",
    "message": "API key rotated automatically. Update config.yaml before next reconnect."
  }
}
```

### Manual Rotation (existing)

`POST /api/v1/devices/{id}/rotate_key/` — returns new key for admin use.

---

## Completion Log

**Completed**: 2026-04-11  
**Migration**: `0007_device_key_rotation_fields` ✅ applied  
**Django check**: 0 issues