# Phase 7 — Angular Frontend

**Phase Total**: 24–30 hours (4–5 days)  
**Status**: ⬜ Not Started

## Tasks

| Task | Title | Hours | Dependencies | Status |
|------|-------|-------|--------------|--------|
| [7.1](task-7.1-angular-setup.md) | Angular Project Setup & Core Module | 3 | Phase 1 | ⬜ |
| [7.2](task-7.2-feature-services.md) | Feature Services (Device, Patch, Deployment) | 2 | 7.1 | ⬜ |
| [7.3](task-7.3-login-page.md) | Login Page | 2 | 7.1 | ⬜ |
| [7.4](task-7.4-app-shell.md) | App Shell (Sidebar + Top Bar) | 2 | 7.1 | ⬜ |
| [7.5](task-7.5-dashboard.md) | Dashboard Page | 3 | 7.4, 7.2 | ⬜ |
| [7.6](task-7.6-device-inventory.md) | Device Inventory Page | 3 | 7.4, 7.2 | ⬜ |
| [7.7](task-7.7-device-detail.md) | Device Detail Flyout | 2 | 7.6 | ⬜ |
| [7.8](task-7.8-patch-catalog.md) | Patch Catalog Page | 3 | 7.4, 7.2 | ⬜ |
| [7.9](task-7.9-deployment-wizard.md) | Deployment Wizard (Multi-Step) | 4 | 7.4, 7.2 | ⬜ |
| [7.10](task-7.10-deployment-live.md) | Live Deployment Monitor | 3 | 7.9, 7.2 | ⬜ |
| [7.11](task-7.11-remaining-pages.md) | Remaining Pages (Compliance, Audit, Users, Settings) | 5 | 7.4, 7.2 | ⬜ |
| [7.12](task-7.12-shared-components.md) | Shared Components (Toasts, Dialogs, etc.) | 3 | 7.1 | ⬜ |

## Dependency Graph

```
Phase 1 → 7.1 ──┬──→ 7.2 ──┬──→ 7.5 (Dashboard)
                 │           ├──→ 7.6 → 7.7 (Devices)
                 │           ├──→ 7.8 (Patches)
                 │           ├──→ 7.9 → 7.10 (Deployments)
                 │           └──→ 7.11 (Remaining)
                 ├──→ 7.3 (Login)
                 ├──→ 7.4 (App Shell) ──→ 7.5, 7.6, 7.8, 7.9, 7.11
                 └──→ 7.12 (Shared Components)
```

## Notes

- This is the largest phase — plan for 4-5 days
- Tasks 7.3, 7.4, 7.12 can run in parallel after 7.1
- Feature pages (7.5-7.11) can be partially parallelized
- All feature pages depend on 7.2 (services) and 7.4 (shell)
