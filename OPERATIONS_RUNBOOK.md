# operations Runbook — PatchGuard platform

> [!NOTE]
> This runbook is intended for system administrators managing the PatchGuard application and its underlying infrastructure.

## Service components
- **Frontend**: Nginx + Angular (Port 443)
- **API**: Django/Gunicorn (Port 8000)
- **Real-Time**: FastAPI/WebSockets (Port 8001)
- **Task worker**: Celery (Default queue)
- **Scheduler**: Celery Beat
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis

## Health Checks
The primary health endpoint is: `https://[host]/api/health/`.
You can also run a deep diagnostic via:
```bash
docker-compose exec backend python manage.py system_health
```

## Maintenance procedures

### Backups
Backups are automated but can be triggered manually:
```bash
./scripts/backup.sh ./my-backups
```

### Restoring from Backup
```bash
./scripts/restore.sh ./backups/patchguard_full_backup_2026-01-01.tar.gz
```

### Clearing the cache
If dashboard stats appear stale or WebSockets are disconnected:
```bash
docker-compose exec backend python manage.py clear_cache
```

### Database migrations
Always perform a backup before running migrations:
```bash
docker-compose exec backend python manage.py migrate
```

## Troubleshooting

### High latency / API timeout
1. Check CPU/RAM: `top` or `docker stats`
2. Check database connections: `system_health`
3. Restart gunicorn: `docker-compose restart backend`

### WebSockets Disconnect frequently
1. Check NGINX logs: `docker-compose logs nginx`
2. Check Redis connectivity: `system_health`
3. Ensure `X-Forwarded-Proto` is correctly set to `https`.

### Tasks not executing
1. Check Celery logs: `docker-compose logs worker`
2. Restart worker: `docker-compose restart worker`
