# Task 3.1 — JWT Authentication (Login, Refresh, Logout)

**Time**: 3 hours  
**Dependencies**: 2.1  
**Status**: ✅ Done  
**Files**: `accounts/serializers.py`, `accounts/views.py`, `accounts/urls.py`

---

## AI Prompt

```
Implement the complete JWT authentication system for PatchGuard.

1. accounts/serializers.py:

   CustomTokenObtainSerializer (extends TokenObtainPairSerializer):
   - Override get_token(cls, user) to add custom claims: role, username, email
   - Update user.last_login and reset failed_login_attempts on success
   - Override validate() to check account lockout:
     * If user.locked_until > now, raise ValidationError "Account locked. Try again later."
     * On auth failure, increment failed_login_attempts
     * If failed_login_attempts >= 5, set locked_until to now + 30 minutes
     * Always save updated fields

   UserSerializer (ModelSerializer):
   - Fields: id, username, email, first_name, last_name, role, department, is_active, last_login, is_ldap_user, date_joined
   - Read-only: id, last_login, date_joined
   - Add drf_spectacular example annotation

   UserCreateSerializer (ModelSerializer):
   - Fields: username, email, password (write_only, min_length=12), first_name, last_name, role, department
   - create() uses User.objects.create_user()

   PasswordChangeSerializer:
   - Fields: old_password, new_password (min 12 chars)
   - Validate old_password against current user
   - Validate new_password complexity (upper, lower, digit, special char)

2. accounts/views.py:

   LoginView (extends TokenObtainPairView):
   - Uses CustomTokenObtainSerializer
   - @extend_schema(tags=["Auth"])

   RefreshView (extends TokenRefreshView):
   - @extend_schema(tags=["Auth"])

   LogoutView (APIView):
   - POST: accepts { refresh: "..." }, blacklists the refresh token
   - Returns 205 on success, 400 on failure
   - @extend_schema(tags=["Auth"])

   PasswordChangeView (APIView):
   - POST: validates and changes password
   - Updates last_password_change, sets must_change_password=False
   - @extend_schema(tags=["Auth"])

   ProfileView (APIView):
   - GET: returns current user profile via UserSerializer
   - PATCH: allows updating first_name, last_name, department
   - @extend_schema(tags=["Auth"])

3. accounts/urls.py:
   - POST login/ → LoginView
   - POST refresh/ → RefreshView
   - POST logout/ → LogoutView
   - POST change-password/ → PasswordChangeView
   - GET/PATCH profile/ → ProfileView

4. Write tests in accounts/tests/test_auth.py:
   - test_login_success
   - test_login_invalid_credentials
   - test_login_locked_account
   - test_account_lockout_after_5_failures
   - test_token_refresh
   - test_token_refresh_rotation (old refresh blacklisted)
   - test_logout_blacklists_refresh
   - test_password_change
   - test_password_change_complexity_validation
   - test_profile_view
   - test_expired_token_returns_401
```

---

## Acceptance Criteria

- [x] Login returns access and refresh tokens with custom claims
- [x] Account locks after 5 failed attempts
- [x] Token refresh rotates and blacklists old token
- [x] Logout blacklists refresh token
- [x] Password change enforces complexity rules
- [x] All tests pass

## Files Created/Modified

- [x] `backend/apps/accounts/serializers.py`
- [x] `backend/apps/accounts/views.py`
- [x] `backend/apps/accounts/urls.py`
- [x] `backend/apps/accounts/tests/test_auth.py`

## Completion Log

## Completion Log

2026-04-04: Implemented CustomTokenObtainSerializer, JWT views, profile and password management APIs. Tested with mocked auth payloads.
