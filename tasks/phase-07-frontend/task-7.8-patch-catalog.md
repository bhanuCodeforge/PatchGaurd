# Task 7.8 — Patch Catalog Page

**Time**: 3 hours  
**Dependencies**: 7.4, 7.2  
**Status**: ⬜ Not Started  
**Files**: `frontend/src/app/features/patches/`

---

## AI Prompt

```
Implement the PatchGuard patch catalog page.

Tabs: Awaiting review, Approved, All patches, Critical. Filters: search, severity, vendor, OS dropdowns.
Table: checkbox, CVE/Patch, severity pill, status pill, OS tags, affected count, released date, approve/reject actions.
Expanded detail panel. Bulk approve.

Sub-components: patch-catalog, patch-table, patch-detail-panel, patch-approval-dialog.
```

---

## Acceptance Criteria

- [ ] Tabs filter patches by status
- [ ] Search and dropdown filters work
- [ ] Severity badges display correct colors
- [ ] Approve/reject actions call API and update UI
- [ ] Detail panel shows full patch information
- [ ] Bulk approve works for multiple patches

## Files Created/Modified

- [ ] `frontend/src/app/features/patches/patch-catalog.component.ts`
- [ ] `frontend/src/app/features/patches/patch-table.component.ts`
- [ ] `frontend/src/app/features/patches/patch-detail-panel.component.ts`
- [ ] `frontend/src/app/features/patches/patch-approval-dialog.component.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
