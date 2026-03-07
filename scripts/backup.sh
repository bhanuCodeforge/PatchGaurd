#!/bin/bash
set -e

# PatchGuard - Database and Redis Backup Script
# Usage: ./scripts/backup.sh [output_directory]

BACKUP_DIR=${1:-"./backups"}
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DB_BACKUP="$BACKUP_DIR/patchguard_db_$TIMESTAMP.sql"
REDIS_BACKUP="$BACKUP_DIR/patchguard_redis_$TIMESTAMP.rdb"

echo "--- Starting PatchGuard Backup ($TIMESTAMP) ---"

# 1. PostgreSQL Backup
echo "[1/2] Backing up PostgreSQL..."
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U patchguard_user patchguard_db > "$DB_BACKUP"
echo "  - Database: $DB_BACKUP (OK)"

# 2. Redis Backup (snapshot)
echo "[2/2] Backing up Redis..."
# Force a save
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli SAVE
# Copy the RDB
docker-compose -f docker-compose.prod.yml cp redis:/data/dump.rdb "$REDIS_BACKUP"
echo "  - Redis: $REDIS_BACKUP (OK)"

# 3. Compress
echo "Compressing backups..."
tar -czf "$BACKUP_DIR/patchguard_full_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "patchguard_db_$TIMESTAMP.sql" "patchguard_redis_$TIMESTAMP.rdb"
rm "$DB_BACKUP" "$REDIS_BACKUP"

echo "--- Backup Complete: $BACKUP_DIR/patchguard_full_backup_$TIMESTAMP.tar.gz ---"
