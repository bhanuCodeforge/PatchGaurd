
# Task 11.7 — Agent API Key Hardening & Rotation

**Time**: 2–4 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: agent client, server, DB migration, rotation task

---

## Scope

Move API keys out of WebSocket query string to headers, add key metadata and rotation, and implement automatic rotation via Celery Beat.

---

## Checklist

- [ ] Update agent to send `X-Agent-Key` header instead of `?api_key=`
- [ ] Update Nginx config to avoid logging sensitive headers
- [ ] Add `created_at` and `last_rotated_at` to API key model
- [ ] Implement Celery Beat job to rotate keys every 90 days and notify agents
- [ ] Add DB migration and rotation task

---

## Acceptance Criteria

- [ ] API key is never exposed in query string or logs
- [ ] Key rotation occurs automatically and is tracked in DB
- [ ] Agents update config on rotation without manual intervention

---

## Completion Log

**Completed**:  
**Notes**: 