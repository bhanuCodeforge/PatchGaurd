# Task 7.12 — Shared Components (Toasts, Dialogs, Empty States, Errors)

**Time**: 3 hours  
**Dependencies**: 7.1  
**Status**: ⬜ Not Started  
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

- [ ] Toast notifications appear and auto-dismiss
- [ ] Confirm dialog blocks with various configurations
- [ ] Empty states render for each variant
- [ ] Loading skeletons match the mockup designs
- [ ] Status badges display correct colors
- [ ] Data table is reusable across pages
- [ ] All pipes transform data correctly
- [ ] Error pages render for each code

## Files Created/Modified

- [ ] `frontend/src/app/shared/components/` (all components)
- [ ] `frontend/src/app/shared/pipes/` (all pipes)

## Completion Log

<!-- Record completion date, notes, and any deviations -->
