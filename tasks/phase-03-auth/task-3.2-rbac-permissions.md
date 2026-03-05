# Task 3.2 — RBAC Permissions System

**Time**: 2 hours  
**Dependencies**: 3.1  
**Status**: ✅ Done  
**Files**: `accounts/permissions.py`, `accounts/views.py` (UserViewSet), `accounts/urls_users.py`

---

## AI Prompt

```
Implement the RBAC permission system and user management endpoints for PatchGuard.

1. accounts/permissions.py:

   IsAdmin(BasePermission):
   - has_permission: user.is_authenticated AND user.role == "admin"

   IsOperatorOrAbove(BasePermission):
   - has_permission: user.is_authenticated AND user.role in ("admin", "operator")

   IsViewerOrAbove(BasePermission):
   - has_permission: user.is_authenticated (any authenticated user)

   ReadOnlyForViewers(BasePermission):
   - has_permission:
     * Not authenticated → False
     * GET, HEAD, OPTIONS → True (any authenticated user can read)
     * POST, PUT, PATCH, DELETE → only if role in ("admin", "operator")

   IsOwnerOrAdmin(BasePermission):
   - has_object_permission: user is admin OR user is the object itself

   IsAgentServiceAccount(BasePermission):
   - has_permission: user.is_authenticated AND user.role == "agent"

2. accounts/views.py — Add UserViewSet:

   UserViewSet (ModelViewSet):
   - queryset: User.objects.all().order_by("-date_joined")
   - permission_classes: [IsAdmin]
   - get_serializer_class: UserCreateSerializer for "create", UserSerializer otherwise
   - filterset_fields: ["role", "is_active", "is_ldap_user"]
   - search_fields: ["username", "email", "first_name", "last_name", "department"]
   - ordering_fields: ["username", "date_joined", "last_login"]
   
   Custom actions:
   - @action(detail=False, methods=["get"]) me/ → returns current user (any authenticated)
   - @action(detail=True, methods=["post"]) lock/ → locks user account (admin only)
   - @action(detail=True, methods=["post"]) unlock/ → unlocks user account (admin only)
   - @action(detail=True, methods=["post"]) reset-password/ → generates temporary password (admin only)
   - @action(detail=True, methods=["post"]) change-role/ → changes user role (admin only)

   All actions should create AuditLog entries.

3. accounts/urls_users.py:
   - Router-based URLs for UserViewSet at /api/v1/users/

4. Write tests in accounts/tests/test_permissions.py:
   - Test complete RBAC matrix:
     * Admin can access everything
     * Operator can read all, write to devices/patches/deployments, cannot manage users
     * Viewer can only read
     * Unauthenticated gets 401
   - Test each permission class individually
   - Test user management CRUD (admin only)
   - Test lock/unlock actions
```

---

## Acceptance Criteria

- [x] RBAC matrix from the architecture doc is enforced
- [x] Admin can CRUD users
- [x] Operator can read users but not create/update/delete
- [x] Viewer gets 403 on write operations
- [x] Lock/unlock works correctly
- [x] All permission tests pass

## Files Created/Modified

- [x] `backend/apps/accounts/permissions.py`
- [x] `backend/apps/accounts/views.py`
- [x] `backend/apps/accounts/urls_users.py`
- [x] `backend/apps/accounts/tests/test_permissions.py`

## Completion Log

## Completion Log

2026-04-04: Implemented RBAC Permissions, IsAdmin, IsOperator, IsViewer. Added UserViewSet with lock/unlock/change_password custom actions.
