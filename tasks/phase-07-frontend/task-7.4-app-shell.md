# Task 7.4 — App Shell (Sidebar + Top Bar)

**Time**: 2 hours  
**Dependencies**: 7.1  
**Status**: ⬜ Not Started  
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

- [ ] Sidebar renders with all navigation items
- [ ] Active route is highlighted
- [ ] Badge counts update from API
- [ ] Top bar shows connection status
- [ ] User menu with logout works
- [ ] Router outlet renders correct component
- [ ] Admin-only routes hidden for non-admins

## Files Created/Modified

- [ ] `frontend/src/app/layout/app-shell.component.ts`
- [ ] `frontend/src/app/layout/sidebar.component.ts`
- [ ] `frontend/src/app/layout/topbar.component.ts`
- [ ] `frontend/src/app/app.routes.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
