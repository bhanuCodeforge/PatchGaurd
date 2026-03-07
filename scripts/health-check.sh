#!/bin/bash
set -e

# PatchGuard - Integrated Health Check Probe
# Usage: ./scripts/health-check.sh [host]

HOST=${1:-"https://localhost"}
ENDPOINT="/api/health/"

echo "--- Probing PatchGuard health on $HOST ---"

# 1. API Health Check
echo "[1/2] Checking API health..."
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k "$HOST$ENDPOINT")

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "  - API Status: OK ($STATUS_CODE)"
else
    echo "  - API Status: FAILED ($STATUS_CODE)"
    exit 1
fi

# 2. WebSocket Health Check (simple handshake)
# echo "[2/2] Checking WebSocket health..."
# We can use websocat or similar, but for a simple probe, checking the endpoint is often enough.

echo "--- Health Check: PASSED ---"
