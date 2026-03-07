# Security Checklist — PatchGuard Platform

## Infrastructure Security
- [ ] SSH keys used for server access (no passwords)
- [ ] Firewall limits access to 80/443 (HTTP/S) and 22 (SSH) only
- [ ] SSL certs valid and using modern ciphers (TLS 1.2+)
- [ ] Fail2Ban or similar installed on host
- [ ] Log directory protected by root access only

## Application Security
- [ ] Django `SECRET_KEY` is long, random, and stored in .env
- [ ] `DEBUG` is set to False in production
- [ ] All API responses have secure headers (HSTS, CSP, X-Frame-Options)
- [ ] CSRF protection enabled for all POST/PATCH requests
- [ ] JWT tokens have short TTL (15m-1h) and use secure signing
- [ ] CORS allowed origins set to explicit domains only
- [ ] Database credentials not shared with other apps

## Database & Data Security
- [ ] Database accessible only via local Docker network
- [ ] Backups stored in a secure separate location
- [ ] Sensitive data (user hashes) encrypted at rest by DB engine

## Monitoring & Incident Response
- [ ] Audit login enabled for all mutating actions
- [ ] Health endpoints reachable only via internal proxy or VPC
- [ ] Error logs monitored for brute-force patterns
- [ ] Secret rotation procedure documented in runbook
