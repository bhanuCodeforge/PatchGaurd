#!/bin/bash
set -e

# PatchGuard - Restore Database and Redis from Backup
# Usage: ./scripts/restore.sh [backup_archive]

BACKUP_ARCHIVE=$1

if [ -z "$BACKUP_ARCHIVE" ]; then
    echo "Usage: ./scripts/restore.sh [backup_archive]"
    exit 1
fi

echo "--- Starting PatchGuard Restore ---"

# 1. Unpack
echo "[1/4] Extracting $BACKUP_ARCHIVE..."
TMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_ARCHIVE" -C "$TMP_DIR"

DB_FILE=$(find "$TMP_DIR" -name "patchguard_db_*.sql")
REDIS_FILE=$(find "$TMP_DIR" -name "patchguard_redis_*.rdb")

if [ -z "$DB_FILE" ] || [ -z "$REDIS_FILE" ]; then
    echo "Error: Invalid backup archive."
    rm -rf "$TMP_DIR"
    exit 1
fi

# 2. Restore PostgreSQL
echo "[2/4] Restoring PostgreSQL..."
# Drop and recreate DB (requires superuser or separate connection)
# For simplicity, we just pipe the SQL. This assumes the DB exists and is clean or SQL has DROP statements.
cat "$DB_FILE" | docker-compose -f docker-compose.prod.yml exec -T db psql -U patchguard_user -d patchguard_db
echo "  - Database: RESTORED"

# 3. Restore Redis
echo "[3/4] Restoring Redis..."
docker-compose -f docker-compose.prod.yml stop redis
docker-compose -f docker-compose.prod.yml cp "$REDIS_FILE" redis:/data/dump.rdb
docker-compose -f docker-compose.prod.yml start redis
echo "  - Redis: RESTORED"

# 4. Clean up
echo "[4/4] Cleaning up..."
rm -rf "$TMP_DIR"

echo "--- Restore Complete! ---"
