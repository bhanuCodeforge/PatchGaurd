#!/bin/bash
set -e

# PatchGuard - Automated Production Deployment Script
# Usage: ./scripts/deploy.sh [tag|branch]

TARGET=${1:-"main"}
ENV_FILE=".env"

echo "--- Starting PatchGuard Deployment ($TARGET) ---"

# 1. Update source code (if in git repo)
if [ -d ".git" ]; then
    echo "[1/5] Updating source code..."
    # git fetch --all
    # git checkout $TARGET
    # git pull origin $TARGET
else
    echo "[1/5] Not a git repository, skipping update."
fi

# 2. Rebuild and restart containers
echo "[2/5] Rebuilding containers..."
docker-compose -f docker-compose.prod.yml build --pull
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 3. Database migrations
echo "[3/5] Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput

# 4. Static files
echo "[4/5] Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput --clear

# 5. Health Check
echo "[5/5] Performing final health check..."
sleep 10
./scripts/health-check.sh

echo "--- Deployment Complete! ---"
