# Task 2.1 — Accounts App Models

**Time**: 2 hours  
**Dependencies**: 1.4  
**Status**: ✅ Done  
**Files**: `backend/apps/accounts/models.py`, `backend/apps/accounts/admin.py`

---

## AI Prompt

```
Implement the accounts app models for PatchGuard.

1. User model (extends AbstractUser):
   - id: UUIDField primary key (uuid4)
   - role: CharField with TextChoices (admin, operator, viewer, agent)
   - department: CharField(100), blank
   - must_change_password: BooleanField, default True
   - last_password_change: DateTimeField, nullable
   - failed_login_attempts: IntegerField, default 0
   - locked_until: DateTimeField, nullable
   - ldap_dn: CharField(500), blank, indexed
   - is_ldap_user: BooleanField, default False
   
   Indexes:
   - role
   - (is_active, role) composite
   
   Meta: db_table = "accounts_user"

2. AuditLog model:
   - id: UUIDField primary key (uuid4)
   - user: ForeignKey to User, SET_NULL, nullable
   - action: CharField(50), indexed
   - resource_type: CharField(50)
   - resource_id: UUIDField, nullable
   - details: JSONField, default dict
   - ip_address: GenericIPAddressField, nullable
   - timestamp: DateTimeField, auto_now_add, indexed
   
   Indexes:
   - (resource_type, resource_id) composite
   - (user, -timestamp) composite
   
   Meta: db_table = "audit_log", ordering = ["-timestamp"]
   
   Note: Add a comment about partitioning by month (applied via raw SQL migration later)

3. Django Admin:
   - UserAdmin: list_display (username, email, role, department, is_active, last_login), list_filter (role, is_active, is_ldap_user), search_fields (username, email, department), readonly_fields for computed fields
   - AuditLogAdmin: list_display (timestamp, user, action, resource_type, ip_address), list_filter (action, resource_type), search_fields (user__username, action), readonly for all fields (immutable), date_hierarchy on timestamp

Generate the model, admin registration, and initial migration.
```

---

## Acceptance Criteria

- [x] Migration creates tables with correct columns and indexes
- [x] User model works as AUTH_USER_MODEL
- [x] Admin interface shows both models with filtering
- [x] UUID primary keys generate correctly
- [x] Can create users with all roles

## Files Created/Modified

- [x] `backend/apps/accounts/models.py`
- [x] `backend/apps/accounts/admin.py`
- [x] `backend/apps/accounts/migrations/0001_initial.py`

## Completion Log

## Completion Log

2026-04-04: Implemented model and admin files. Verified with successful migration and account creation during seeding. Fixed table naming to match specs exactly.
