# Task 9.1 — Backend Integration Tests

**Time**: 4 hours  
**Dependencies**: Phases 2–6  
**Status**: ⬜ Not Started  
**Files**: Test files across all apps

---

## AI Prompt

```
Write comprehensive integration tests for the PatchGuard Django backend.

Use pytest-django with fixtures. Create conftest.py with shared fixtures.

Test suites:
1. test_auth_flow.py — End-to-end authentication (login, refresh, logout, lockout)
2. test_device_lifecycle.py — Full device lifecycle (create, group, tag, scan, compliance, decommission)
3. test_patch_workflow.py — Patch approval workflow (import → review → approve, invalid transitions)
4. test_deployment_lifecycle.py — Complete deployment flow (create → approve → execute → monitor)
5. test_permissions_matrix.py — Exhaustive RBAC testing (admin/operator/viewer/unauthenticated)
6. test_reporting.py — Dashboard stats and compliance reports
7. test_api_documentation.py — Schema generation validation

Target: >85% code coverage on views and serializers.
Run with: pytest --cov=apps --cov-report=html -v
```

---

## Acceptance Criteria

- [ ] All test suites pass
- [ ] Code coverage >85% on views and serializers
- [ ] Every API endpoint tested with all user roles
- [ ] State machine transitions fully tested
- [ ] No flaky tests (all deterministic)

## Files Created/Modified

- [ ] `backend/conftest.py`
- [ ] `backend/apps/accounts/tests/test_auth_flow.py`
- [ ] `backend/apps/inventory/tests/test_device_lifecycle.py`
- [ ] `backend/apps/patches/tests/test_patch_workflow.py`
- [ ] `backend/apps/deployments/tests/test_deployment_lifecycle.py`
- [ ] `backend/apps/accounts/tests/test_permissions_matrix.py`
- [ ] `backend/tests/test_reporting.py`
- [ ] `backend/tests/test_api_documentation.py`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
