#!/bin/bash
set -e

DB_HOST="${POSTGRES_HOST:-dhg-registry-db}"
DB_USER="${POSTGRES_USER:-dhg}"

echo "Waiting for database at ${DB_HOST} to be ready..."
until pg_isready -h "${DB_HOST}" -U "${DB_USER}"; do
    echo "Database not ready, waiting..."
    sleep 2
done

echo "Running database migrations..."
alembic upgrade head

echo "Starting Registry API..."
exec "$@"
