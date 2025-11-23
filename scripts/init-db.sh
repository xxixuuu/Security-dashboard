#!/bin/bash
# =============================================================================
# Database Initialization Script
# =============================================================================

set -e

echo "🔧 Initializing SecDash database..."

# Enable TimescaleDB extension
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- Create UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create pg_trgm for faster text search
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;

    SELECT 'Database initialized successfully' AS status;
EOSQL

echo "✅ Database initialization completed!"
