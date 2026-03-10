
# Task 11.2 — BFF / API Gateway Prototype

**Time**: 3–5 days  
**Dependencies**: 11.1-triage  
**Status**: ⬜ Not Started  
**Files**: `backend/bff/`, README, integration tests

---

## Scope

Ship a lightweight FastAPI BFF prototype that aggregates critical endpoints and provides a single base URL for the Angular frontend.

---

## Checklist

- [ ] Implement auth passthrough (cookie/header translation)
- [ ] Aggregate `/api/v1/dashboard` endpoint
- [ ] Proxy `/api/v1/devices` list with caching
- [ ] WebSocket pass-through or proxy for `/ws/`
- [ ] Write README with run/re-point instructions
- [ ] Add integration test verifying endpoint parity

---

## Acceptance Criteria

- [ ] Angular can use a single base URL for all API and realtime calls
- [ ] Rate-limiting and caching rules are applied at BFF for heavy endpoints
- [ ] Integration tests pass for all proxied/aggregated endpoints

---

## Completion Log

**Completed**:  
**Notes**: 