# Task 7.5 — Dashboard Page

**Time**: 3 hours  
**Dependencies**: 7.4, 7.2  
**Status**: ⬜ Not Started  
**Files**: `frontend/src/app/features/dashboard/`

---

## AI Prompt

```
Implement the PatchGuard main dashboard page.

Layout: 4 KPI cards, compliance donut chart, devices by OS bar chart, active deployments feed (live via WebSocket), critical patches table.

Sub-components: compliance-gauge, device-os-chart, deployment-feed, critical-patches-table.

Data: reportService.getDashboardStats(), auto-refresh 30s, WebSocket live updates, OnPush change detection.
```

---

## Acceptance Criteria

- [ ] Dashboard loads and displays all 4 KPI cards
- [ ] Donut chart renders with correct proportions
- [ ] OS bar chart shows accurate data
- [ ] Deployment feed updates in real time via WebSocket
- [ ] Critical patches table is sortable
- [ ] Loading skeletons show during data fetch
- [ ] Empty state shows when no data

## Files Created/Modified

- [ ] `frontend/src/app/features/dashboard/dashboard.component.ts`
- [ ] `frontend/src/app/features/dashboard/widgets/compliance-gauge.component.ts`
- [ ] `frontend/src/app/features/dashboard/widgets/device-os-chart.component.ts`
- [ ] `frontend/src/app/features/dashboard/widgets/deployment-feed.component.ts`
- [ ] `frontend/src/app/features/dashboard/widgets/critical-patches-table.component.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
