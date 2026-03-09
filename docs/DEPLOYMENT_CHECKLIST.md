# Deployment Checklist — PatchGuard Platform

## Pre-deployment
- [ ] Database backup taken (`backup.sh`)
- [ ] All feature tests passing (`pytest`)
- [ ] No high/critical severity security issues (`bandit` or manual audit)
- [ ] VERSION file updated

## Infrastructure
- [ ] Nginx config verified (`nginx -t`)
- [ ] SSL certs generated and valid (`generate-certs.sh`)
- [ ] Environment variables (.env) updated for production
- [ ] ALLOWED_HOSTS includes production domain

## Deployment Steps
- [ ] Run `scripts/deploy.sh`
- [ ] Verify migrations applied successfully
- [ ] Verify static files collected

## Post-deployment
- [ ] Run `scripts/health-check.sh`
- [ ] Verify WebSocket connectivity in browser
- [ ] Verify audit log entries created for login
- [ ] Monitor error logs for first 15 minutes
- [ ] Check Celery worker processing heartbeat tasks
