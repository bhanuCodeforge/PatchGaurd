# Task 7.11 — Remaining Pages (Compliance, Audit, Users, Settings)

**Time**: 5 hours  
**Dependencies**: 7.4, 7.2  
**Status**: ⬜ Not Started  
**Files**: Remaining feature components

---

## AI Prompt

```
Implement the remaining PatchGuard pages:

1. Compliance Report (/compliance): Date range selector, KPIs, trend line chart, least compliant groups, compliance by OS, SLA table.

2. Audit Log (/audit): Summary cards, filter bar, action table with type badges, pagination, export.

3. User Management (/settings/users, admin only): Tabs, filter bar, user table, add user form with role cards, lock/unlock actions.

4. Settings (/settings, admin only): Sidebar sections (LDAP, Notifications, Maintenance, Agent config, Vendor feeds, SLA, Backup, License), form controls for each section.

OnPush change detection and signals throughout.
```

---

## Acceptance Criteria

- [ ] Compliance page renders all charts and tables
- [ ] Audit log loads with all filter options
- [ ] User management CRUD works (admin only)
- [ ] Settings page shows all configuration sections
- [ ] LDAP test connection calls API
- [ ] Loading/empty/error states work on all pages

## Files Created/Modified

- [ ] `frontend/src/app/features/compliance/`
- [ ] `frontend/src/app/features/audit/`
- [ ] `frontend/src/app/features/settings/user-management.component.ts`
- [ ] `frontend/src/app/features/settings/settings.component.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
