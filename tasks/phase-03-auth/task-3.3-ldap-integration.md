# Task 3.3 — LDAP/Active Directory Integration

**Time**: 3 hours  
**Dependencies**: 3.1  
**Status**: ✅ Done  
**Files**: `accounts/ldap_backend.py`, `accounts/tasks.py` (LDAP sync)

---

## AI Prompt

```
Implement LDAP/Active Directory authentication backend for PatchGuard on-premises deployment.

1. accounts/ldap_backend.py — LDAPBackend:

   authenticate(self, request, username=None, password=None):
   - Return None if username or password is empty
   - Get LDAP settings from Django settings: LDAP_URI, LDAP_BIND_DN_TEMPLATE, LDAP_SEARCH_BASE
   - Initialize ldap connection with OPT_REFERRALS=0, NETWORK_TIMEOUT=10
   - Attempt simple_bind_s with formatted bind DN
   - Search for user with sAMAccountName filter
   - Extract attributes: cn, mail, givenName, sn, memberOf, distinguishedName
   - Map AD group memberships to PatchGuard roles using _map_groups_to_role()
   - Use update_or_create to sync user to Django:
     * username, email, first_name, last_name from AD attributes
     * role from group mapping
     * is_ldap_user = True
     * ldap_dn = distinguished name
     * must_change_password = False
   - Handle exceptions: INVALID_CREDENTIALS → return None, LDAPError → log and return None
   - Always unbind in finally block

   _map_groups_to_role(self, member_of: list) → str:
   - Decode bytes, extract CN from DN
   - Check against configurable group names from settings:
     * LDAP_ADMIN_GROUP (default "PatchMgr-Admins") → "admin"
     * LDAP_OPERATOR_GROUP (default "PatchMgr-Operators") → "operator"
     * Default → "viewer"

   get_user(self, user_id):
   - Standard get by pk

2. Add to settings/base.py:
   - AUTHENTICATION_BACKENDS = ["apps.accounts.ldap_backend.LDAPBackend", "django.contrib.auth.backends.ModelBackend"]
   - LDAP_URI, LDAP_BIND_DN_TEMPLATE, LDAP_SEARCH_BASE from env vars
   - LDAP_ADMIN_GROUP, LDAP_OPERATOR_GROUP from env vars with defaults
   - LDAP_SYNC_ENABLED from env (default False)

3. accounts/tasks.py — Celery tasks:

   sync_ldap_users (periodic task, runs every 15 minutes if LDAP_SYNC_ENABLED):
   - Connect to LDAP server using service account (LDAP_SERVICE_DN, LDAP_SERVICE_PASSWORD)
   - Search all users in LDAP_SEARCH_BASE
   - For each AD user, update_or_create in Django
   - Mark Django LDAP users not found in AD as inactive
   - Log sync stats: created, updated, deactivated
   - Create AuditLog entry for the sync

   test_ldap_connection:
   - Simple task that attempts LDAP bind and returns success/failure
   - Used by settings page "Test connection" button

4. Write tests in accounts/tests/test_ldap.py:
   - Mock python-ldap for all tests (don't require actual AD server)
   - test_ldap_authenticate_success
   - test_ldap_authenticate_invalid_credentials
   - test_ldap_group_to_role_mapping
   - test_ldap_creates_new_user
   - test_ldap_updates_existing_user
   - test_ldap_sync_task
   - test_ldap_connection_timeout
```

---

## Acceptance Criteria

- [x] LDAP authentication works (verified with mocked tests)
- [x] Group-to-role mapping is correct
- [x] New users are created on first LDAP login
- [x] Existing users are updated on subsequent logins
- [x] LDAP sync task runs periodically
- [x] Fallback to local auth works when LDAP is down
- [x] All tests pass with mocked LDAP

## Files Created/Modified

- [x] `backend/apps/accounts/ldap_backend.py`
- [x] `backend/apps/accounts/tasks.py`
- [x] `backend/config/settings/base.py` (LDAP settings)
- [x] `backend/apps/accounts/tests/test_ldap.py`

## Completion Log

## Completion Log

2026-04-04: Implemented LDAP backend with AD group mapping to RBAC roles. Added settings, celery sync task, Docker dependencies.
