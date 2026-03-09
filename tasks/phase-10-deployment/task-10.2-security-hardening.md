# Task 10.2 — Security Hardening

**Time**: 3 hours  
**Dependencies**: 10.1  
**Status**: ✅ Done  
**Files**: Various config files

---

## AI Prompt

```
Implement all security hardening measures for PatchGuard on-premises deployment.

1. Django security settings (SSL redirect, HSTS, secure cookies, X-Frame-Options)
2. Password policy (12+ chars, complexity, history, expiry, first-login force change)
3. API rate limiting (auth 5/min, general 200/min, deploy 10/min, 429 + Retry-After)
4. Input validation (SQL injection, XSS, path traversal, SSRF protection)
5. Redis security (requirepass, bind internal, disable dangerous commands)
6. PostgreSQL security (strong password, internal-only, pg_hba.conf, query logging)
7. Docker security (non-root, read-only fs, no privileged, resource limits, trivy scan)
8. Agent authentication (unique API keys, TLS-only, revocable)
9. Audit logging completeness (all mutations, immutable, 12-month retention)
10. Secret management (.env permissions, git hooks, rotation procedure)

Create SECURITY_CHECKLIST.md.
```

---

## Acceptance Criteria

- [x] All Django security settings configured
- [x] Password policy enforced
- [x] Rate limiting works correctly
- [x] No SQL injection vulnerabilities
- [x] Redis and PostgreSQL secured
- [x] Docker containers run as non-root
- [x] Audit log captures all mutations
- [x] Security checklist is complete

## Files Created/Modified

- [x] `backend/config/settings/prod.py` (security settings)
- [x] `backend/apps/accounts/models.py` (password complexity validator)
- [x] `nginx/nginx.conf` (security headers, TLS 1.2/1.3, HSTS)
- [x] `docker-compose.prod.yml` (non-root, memory limits, health checks)
- [x] `docs/SECURITY_CHECKLIST.md`

## Completion Log

**Completed**: 2026-04-07  
**Notes**: prod.py has full Django security settings (HSTS, SSL redirect, secure cookies). nginx.conf has CSP, X-Frame-Options DENY. docker-compose.prod.yml runs all services as user 1000:1000 with memory limits.
