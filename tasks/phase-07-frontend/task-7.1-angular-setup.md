# Task 7.1 — Angular Project Setup & Core Module

**Time**: 3 hours  
**Dependencies**: Phase 1  
**Status**: ✅ Done  
**Files**: `frontend/` core structure

---

## AI Prompt

```
Set up the Angular 20+ project for PatchGuard with standalone components and signals.

1. Create Angular project with ng new, standalone, routing, SCSS
2. Core module (src/app/core/):
   - models/ (user, device, patch, deployment interfaces and enums)
   - auth/ (auth.service.ts with signals, auth.interceptor.ts, auth.guard.ts, role.guard.ts)
   - services/ (api.service.ts, websocket.service.ts, notification.service.ts)
3. app.config.ts with interceptors and router
4. environments/ (dev and prod)
5. Proxy configuration for dev
```

---

## Acceptance Criteria

- [x] Angular app compiles and serves
- [x] Auth service manages JWT lifecycle
- [x] HTTP interceptor attaches tokens
- [x] Guards protect routes
- [x] WebSocket service connects with reconnection
- [x] Notification service shows toasts
- [x] Proxy works for dev environment

## Files Created/Modified

- [x] `frontend/` — full Angular project
- [x] `frontend/src/app/core/models/`
- [x] `frontend/src/app/core/auth/`
- [x] `frontend/src/app/core/services/`
- [x] `frontend/proxy.conf.json`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
