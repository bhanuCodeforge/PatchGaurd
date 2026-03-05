# Task 7.6 — Device Inventory Page

**Time**: 3 hours  
**Dependencies**: 7.4, 7.2  
**Status**: ⬜ Not Started  
**Files**: `frontend/src/app/features/devices/`

---

## AI Prompt

```
Implement the PatchGuard device inventory page.

Top: Title + actions. Filter bar: search, status chips, OS chips, environment chips.
Bulk action bar (on selection). Data table: checkbox, hostname, IP, OS, environment, status dot, compliance bar, tags, last seen.
Pagination, sorting, multi-select.

Sub-components: device-list, device-table, device-filters, device-bulk-actions.
Handle: loading, empty, error, no-results states.
```

---

## Acceptance Criteria

- [ ] Device table loads with all columns
- [ ] Search filters in real time (debounced)
- [ ] Filter chips work and update URL
- [ ] Sorting works on all sortable columns
- [ ] Bulk selection with checkbox works
- [ ] Pagination navigates correctly
- [ ] Loading/empty/error states display properly
- [ ] Click navigates to device detail

## Files Created/Modified

- [ ] `frontend/src/app/features/devices/device-list.component.ts`
- [ ] `frontend/src/app/features/devices/device-table.component.ts`
- [ ] `frontend/src/app/features/devices/device-filters.component.ts`
- [ ] `frontend/src/app/features/devices/device-bulk-actions.component.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
