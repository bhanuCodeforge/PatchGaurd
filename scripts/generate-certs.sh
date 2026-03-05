#!/usr/bin/env bash
# Generate self-signed certificates for dev/testing.
# To be replaced with real CA-signed certificates in true production.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/../nginx/ssl"

echo "Creating SSL directory at ${SSL_DIR}..."
mkdir -p "${SSL_DIR}"

echo "Generating generic self-signed certificate..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${SSL_DIR}/key.pem" \
    -out "${SSL_DIR}/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=PatchGuard/OU=IT/CN=patchmgr.internal.corp"

# Set permissions so docker/nginx process can read
chmod 644 "${SSL_DIR}/cert.pem"
chmod 640 "${SSL_DIR}/key.pem"

echo "Certificate generated successfully."
ls -l "${SSL_DIR}"
