# Task 7.3 — Login Page

**Time**: 2 hours  
**Dependencies**: 7.1  
**Status**: ✅ Done  
**Files**: `frontend/src/app/features/auth/`

---

## AI Prompt

```
Implement the PatchGuard login page as an Angular standalone component.

Design: Centered card (380px), logo with shield icon, LDAP/Local toggle, username/password inputs, remember device checkbox, sign in button, footer links, TLS indicator.

Behavior: Form validation, error states, lockout display, loading state, WebSocket connect on success, navigate to /dashboard.

Route: /login (no auth guard)
```

---

## Acceptance Criteria

- [x] Login form renders correctly
- [x] LDAP/Local toggle works
- [x] Error states display properly
- [x] Successful login navigates to dashboard
- [x] WebSocket connects after login
- [x] Form validation prevents empty submissions

## Files Created/Modified

- [x] `frontend/src/app/features/auth/login.component.ts`
- [x] `frontend/src/app/features/auth/login.component.scss`
- [x] `frontend/src/app/features/auth/login.component.html`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
