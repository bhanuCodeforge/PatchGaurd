#!/bin/bash
set -e

# Generate self-signed SSL certificates for PatchGuard on-premises deployment

CERT_DIR="./nginx/ssl"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/patchguard.key" ]; then
    echo "Certificates already exist. Skipping generation."
    exit 0
fi

echo "Generating self-signed SSL certificates..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/patchguard.key" \
    -out "$CERT_DIR/patchguard.crt" \
    -subj "/C=US/ST=State/L=City/O=PatchGuard/OU=IT/CN=patchguard.local"

echo "Certificates generated in $CERT_DIR"
chmod 600 "$CERT_DIR/patchguard.key"
chmod 644 "$CERT_DIR/patchguard.crt"
