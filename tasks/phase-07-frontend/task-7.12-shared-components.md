# Task 7.12 — Shared Components (Toasts, Dialogs, Empty States, Errors)

**Time**: 3 hours  
**Dependencies**: 7.1  
**Status**: ✅ Completed
**Files**: `frontend/src/app/shared/`

---

## AI Prompt

```
Implement all shared UI components for PatchGuard:

1. toast-container.component.ts — Notification stack (top-right, auto-dismiss, variants)
2. confirm-dialog.component.ts — Modal with severity, checkbox/text confirmation
3. empty-state.component.ts — No data / no results / error variants
4. loading-skeleton.component.ts — Shimmer skeletons (kpi-row, table, card, chart)
5. status-badge.component.ts — Colored pills for device/patch/deployment/severity
6. data-table.component.ts — Generic reusable table with sort, select, pagination
7. Pipes: relative-time, severity-color, file-size, compliance-color
8. Error pages: 404, 403, 500, 503
9. connection-banner.component.ts — WebSocket reconnection banner
10. session-expired.component.ts — Re-authentication overlay
```

---

## Acceptance Criteria

- [x] Toast notifications appear and auto-dismiss
- [x] Confirm dialog blocks with various configurations
- [x] Empty states render for each variant
- [x] Loading skeletons match the mockup designs
- [x] Status badges display correct colors
- [x] Data table is reusable across pages
- [x] All pipes transform data correctly
- [x] Error pages render for each code

## Files Created/Modified

- [x] `frontend/src/app/shared/components/` (all components)
- [x] `frontend/src/app/shared/pipes/` (all pipes)

## Completion Log

- **2026-04-05**: All shared UI components and utility pipes have been implemented and verified. This provides a consistent design system across the entire application, including accessible status badges, shimmer loading states, and a centralized toast notification system.
