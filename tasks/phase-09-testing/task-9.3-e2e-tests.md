# Task 9.3 — E2E Tests

**Time**: 3 hours  
**Dependencies**: All previous phases  
**Status**: ⬜ Not Started  
**Files**: `frontend/e2e/`

---

## AI Prompt

```
Write end-to-end tests for PatchGuard using Playwright.

Test scenarios:
1. e2e/auth.spec.ts — Authentication flow (login, dashboard, logout, protected routes)
2. e2e/dashboard.spec.ts — Dashboard data verification
3. e2e/device-flow.spec.ts — Device management (list, search, filter, detail)
4. e2e/patch-flow.spec.ts — Patch approval workflow
5. e2e/deployment-flow.spec.ts — Full deployment wizard + execution
6. e2e/rbac.spec.ts — Permission enforcement (viewer vs admin)

Configure: screenshots on failure, run against Docker Compose environment.
Run with: npx playwright test
```

---

## Acceptance Criteria

- [ ] All E2E tests pass
- [ ] Tests run against seeded Docker environment
- [ ] Screenshots captured on failure
- [ ] Full deployment flow works end-to-end
- [ ] RBAC enforcement verified visually

## Files Created/Modified

- [ ] `frontend/e2e/auth.spec.ts`
- [ ] `frontend/e2e/dashboard.spec.ts`
- [ ] `frontend/e2e/device-flow.spec.ts`
- [ ] `frontend/e2e/patch-flow.spec.ts`
- [ ] `frontend/e2e/deployment-flow.spec.ts`
- [ ] `frontend/e2e/rbac.spec.ts`
- [ ] `frontend/playwright.config.ts`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
