# Task 7.4 — App Shell (Sidebar + Top Bar)

**Time**: 2 hours  
**Dependencies**: 7.1  
**Status**: ✅ Completed
**Files**: `frontend/src/app/layout/`

---

## AI Prompt

```
Implement the PatchGuard app shell with sidebar navigation and top bar.

Sidebar (220px, fixed): Logo, nav sections (Overview, Manage, Reports, System), active state, badge counts, admin-only items.

Top bar: Page title, live indicator, last sync, notification bell, user avatar dropdown.

App routing: /login (no shell), all other routes wrapped in AppShellComponent.
```

---

## Acceptance Criteria

- [x] Sidebar renders with all navigation items
- [x] Active route is highlighted
- [x] Badge counts update from API
- [x] Top bar shows connection status
- [x] User menu with logout works
- [x] Router outlet renders correct component
- [x] Admin-only routes hidden for non-admins

## Files Created/Modified

- [x] `frontend/src/app/layout/app-shell/app-shell.component.ts`
- [x] `frontend/src/app/layout/sidebar/sidebar.component.ts`
- [x] `frontend/src/app/layout/topbar/topbar.component.ts`
- [x] `frontend/src/app/app.routes.ts`

## Completion Log

- **2026-04-05**: Verified full implementation of App Shell components. Navigation, admin route protection, and top-bar status integration are fully functional.
