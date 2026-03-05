# Task 10.2 — Security Hardening

**Time**: 3 hours  
**Dependencies**: 10.1  
**Status**: ⬜ Not Started  
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

- [ ] All Django security settings configured
- [ ] Password policy enforced
- [ ] Rate limiting works correctly
- [ ] No SQL injection vulnerabilities
- [ ] Redis and PostgreSQL secured
- [ ] Docker containers run as non-root
- [ ] Audit log captures all mutations
- [ ] Security checklist is complete

## Files Created/Modified

- [ ] `backend/config/settings/prod.py` (security settings)
- [ ] `backend/apps/accounts/validators.py` (password policy)
- [ ] `nginx/nginx.conf` (security headers)
- [ ] `docker-compose.prod.yml` (container security)
- [ ] `SECURITY_CHECKLIST.md`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
