#!/bin/bash
set -e

echo "Waiting for database to be ready..."
until pg_isready -h registry-db -U dhg_user; do
    echo "Database not ready, waiting..."
    sleep 2
done

echo "Running database migrations..."
alembic upgrade head

echo "Starting Registry API..."
exec "$@"
