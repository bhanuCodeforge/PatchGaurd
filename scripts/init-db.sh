#!/bin/bash
# PatchGuard PostgreSQL initialization script
# Runs as docker-entrypoint-initdb.d during first startup

set -e
echo "Initializing PatchGuard PostgreSQL database..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Core extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    CREATE EXTENSION IF NOT EXISTS "btree_gin";

    -- Performance Parameters (applied on restart)
    ALTER SYSTEM SET max_connections = '200';
    ALTER SYSTEM SET shared_buffers = '512MB';
    ALTER SYSTEM SET effective_cache_size = '1536MB';
    ALTER SYSTEM SET work_mem = '4MB';
    ALTER SYSTEM SET maintenance_work_mem = '128MB';
    ALTER SYSTEM SET wal_level = 'replica';
    ALTER SYSTEM SET max_wal_senders = '3';
    ALTER SYSTEM SET log_min_duration_statement = '200';
EOSQL

echo "Database initialized successfully. System params set (requires restart to apply)."
